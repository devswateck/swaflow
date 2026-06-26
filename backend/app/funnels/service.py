from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.companies.models import Company
from app.funnels.models import SalesFunnel, SalesFunnelStep
from app.funnels.schemas import FunnelCreate, FunnelStepWrite, FunnelUpdate

WELCOME_FUNNEL_SYSTEM_KEY = "welcome"
WELCOME_FUNNEL_NAME = "Funnel de bienvenida"
WELCOME_FUNNEL_DESCRIPTION = "Punto de entrada comercial para conversaciones nuevas."
WELCOME_FUNNEL_MESSAGE = (
    "Hola, gracias por escribir. Soy el asistente de Swaflow. "
    "Para ayudarte mejor, cuentame tu nombre, correo y ciudad."
)
WELCOME_CAPTURE_FIELDS = ["Nombre", "Correo", "Ciudad"]
WELCOME_ASSIGNMENT_CRITERIA = "Conversaciones nuevas o sin clasificacion comercial previa"
WELCOME_STEPS: list[FunnelStepWrite] = [
    FunnelStepWrite(
        position=1,
        name="Bienvenida",
        code="bienvenida",
        prompt=(
            "Saluda al cliente, agradece su contacto y presenta las opciones "
            "comerciales principales del tenant."
        ),
        objectives=["Saludar", "Detectar interes principal"],
        transition_criteria="El cliente responde con una necesidad o interes concreto.",
        config={"entry_point": True, "capture_fields": ["Nombre", "Correo", "Ciudad"]},
    ),
    FunnelStepWrite(
        position=2,
        name="Captura inicial",
        code="captura_inicial",
        prompt=(
            "Solicita solamente los datos que faltan: nombre, correo y ciudad. "
            "No repitas el telefono si ya viene desde WhatsApp."
        ),
        objectives=["Capturar datos iniciales", "Evitar pedir el telefono"],
        transition_criteria="Los datos iniciales estan completos o el cliente pide avanzar.",
        config={"required_fields": ["Nombre", "Correo", "Ciudad"]},
    ),
    FunnelStepWrite(
        position=3,
        name="Clasificacion comercial",
        code="clasificacion_comercial",
        prompt=(
            "Clasifica la intencion del cliente y decide el siguiente paso: "
            "comprar, consultar, agendar o pasar a humano."
        ),
        objectives=["Clasificar la intencion", "Elegir el siguiente flujo"],
        transition_criteria="La intencion comercial queda identificada.",
        config={"allowed_outcomes": ["comprar", "consultar", "agendar", "humano"]},
    ),
]


def _with_steps_stmt(company_id: UUID):
    return (
        select(SalesFunnel)
        .where(SalesFunnel.company_id == company_id)
        .options(selectinload(SalesFunnel.steps))
        .order_by(SalesFunnel.created_at.desc())
    )


def _default_welcome_funnel_stmt(company_id: UUID):
    return (
        select(SalesFunnel)
        .where(SalesFunnel.company_id == company_id, SalesFunnel.system_key == WELCOME_FUNNEL_SYSTEM_KEY)
        .options(selectinload(SalesFunnel.steps))
        .order_by(SalesFunnel.created_at.asc())
    )


def _lock_company_row(db: Session, *, company_id: UUID) -> None:
    db.execute(select(Company.id).where(Company.id == company_id).with_for_update())


def _seed_default_welcome_funnel_fields(funnel: SalesFunnel) -> bool:
    dirty = False
    if not funnel.welcome_message:
        funnel.welcome_message = WELCOME_FUNNEL_MESSAGE
        dirty = True
    if not funnel.capture_fields:
        funnel.capture_fields = list(WELCOME_CAPTURE_FIELDS)
        dirty = True
    if not funnel.assignment_criteria:
        funnel.assignment_criteria = WELCOME_ASSIGNMENT_CRITERIA
        dirty = True
    return dirty


def _normalize_capture_fields(value: object) -> list[str]:
    return list(value) if isinstance(value, list) else []


def _is_likely_welcome_funnel(funnel: SalesFunnel) -> bool:
    step_codes = [step.code for step in sorted(funnel.steps, key=lambda step: step.position)]
    return step_codes == [step.code for step in WELCOME_STEPS]


def _has_exact_welcome_signature(funnel: SalesFunnel) -> bool:
    if not _is_likely_welcome_funnel(funnel):
        return False
    return (
        funnel.welcome_message == WELCOME_FUNNEL_MESSAGE
        and _normalize_capture_fields(funnel.capture_fields) == list(WELCOME_CAPTURE_FIELDS)
        and funnel.assignment_criteria == WELCOME_ASSIGNMENT_CRITERIA
    )


def _find_legacy_welcome_candidate(db: Session, *, company_id: UUID) -> SalesFunnel | None:
    candidates = list(db.scalars(_with_steps_stmt(company_id)))
    if not candidates:
        return None
    exact_candidates = [funnel for funnel in candidates if _has_exact_welcome_signature(funnel)]
    if not exact_candidates:
        return None
    return sorted(exact_candidates, key=lambda funnel: funnel.created_at)[0]


def _default_welcome_funnel_payload() -> FunnelCreate:
    return FunnelCreate(
        name=WELCOME_FUNNEL_NAME,
        description=WELCOME_FUNNEL_DESCRIPTION,
        status="active",
        is_default=True,
        welcome_message=WELCOME_FUNNEL_MESSAGE,
        capture_fields=list(WELCOME_CAPTURE_FIELDS),
        assignment_criteria=WELCOME_ASSIGNMENT_CRITERIA,
        steps=[step.model_copy(deep=True) for step in WELCOME_STEPS],
    )


def ensure_welcome_funnel(
    db: Session,
    *,
    company_id: UUID,
    commit: bool = True,
) -> SalesFunnel:
    _lock_company_row(db, company_id=company_id)
    existing_default = db.scalar(_default_welcome_funnel_stmt(company_id))
    if existing_default is None:
        existing_default = _find_legacy_welcome_candidate(db, company_id=company_id)
    if existing_default is not None:
        if existing_default.system_key != WELCOME_FUNNEL_SYSTEM_KEY:
            existing_default.system_key = WELCOME_FUNNEL_SYSTEM_KEY
            dirty = True
        else:
            dirty = False
        if existing_default.status != "active":
            existing_default.status = "active"
            dirty = True
        dirty = _seed_default_welcome_funnel_fields(existing_default) or dirty
        if not existing_default.is_default:
            _set_default_if_requested(db, company_id=company_id, is_default=True)
            existing_default.is_default = True
            dirty = True
        if not existing_default.steps:
            _sync_steps(
                db,
                company_id=company_id,
                funnel=existing_default,
                steps=[step.model_copy(deep=True) for step in WELCOME_STEPS],
            )
            dirty = True
        elif not _is_likely_welcome_funnel(existing_default):
            _sync_steps(
                db,
                company_id=company_id,
                funnel=existing_default,
                steps=[step.model_copy(deep=True) for step in WELCOME_STEPS],
            )
            dirty = True
        if dirty and commit:
            db.commit()
        return get_funnel(db, company_id=company_id, funnel_id=existing_default.id)

    _set_default_if_requested(db, company_id=company_id, is_default=True)
    funnel = SalesFunnel(
        company_id=company_id,
        name=WELCOME_FUNNEL_NAME,
        system_key=WELCOME_FUNNEL_SYSTEM_KEY,
        description=WELCOME_FUNNEL_DESCRIPTION,
        status="active",
        is_default=True,
        welcome_message=WELCOME_FUNNEL_MESSAGE,
        capture_fields=list(WELCOME_CAPTURE_FIELDS),
        assignment_criteria=WELCOME_ASSIGNMENT_CRITERIA,
    )
    db.add(funnel)
    db.flush()
    _sync_steps(
        db,
        company_id=company_id,
        funnel=funnel,
        steps=[step.model_copy(deep=True) for step in WELCOME_STEPS],
    )
    if commit:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un funnel con ese nombre",
            ) from exc
    return get_funnel(db, company_id=company_id, funnel_id=funnel.id)


def get_default_funnel(db: Session, *, company_id: UUID) -> SalesFunnel:
    return ensure_welcome_funnel(db, company_id=company_id, commit=False)


def list_funnels(db: Session, *, company_id: UUID) -> list[SalesFunnel]:
    return list(db.scalars(_with_steps_stmt(company_id)))


def get_funnel(db: Session, *, company_id: UUID, funnel_id: UUID) -> SalesFunnel:
    funnel = db.scalar(
        _with_steps_stmt(company_id).where(SalesFunnel.id == funnel_id)
    )
    if funnel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funnel no encontrado")
    return funnel


def _set_default_if_requested(
    db: Session, *, company_id: UUID, is_default: bool
) -> None:
    if not is_default:
        return
    existing_defaults = list(
        db.scalars(
            select(SalesFunnel).where(
                SalesFunnel.company_id == company_id, SalesFunnel.is_default.is_(True)
            )
        )
    )
    for item in existing_defaults:
        item.is_default = False


def _sync_steps(
    db: Session, *, company_id: UUID, funnel: SalesFunnel, steps: list[FunnelStepWrite]
) -> None:
    funnel.steps.clear()
    sorted_steps = sorted(steps, key=lambda step: step.position)
    for step in sorted_steps:
        funnel.steps.append(
            SalesFunnelStep(
                company_id=company_id,
                funnel_id=funnel.id,
                position=step.position,
                name=step.name,
                code=step.code,
                prompt=step.prompt,
                objectives=step.objectives,
                transition_criteria=step.transition_criteria,
                status=step.status,
                config=step.config,
            )
        )
    db.flush()


def create_funnel(db: Session, *, company_id: UUID, payload: FunnelCreate) -> SalesFunnel:
    if payload.is_default:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo el funnel de bienvenida puede ser predeterminado",
        )
    funnel = SalesFunnel(
        company_id=company_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        is_default=payload.is_default,
        welcome_message=payload.welcome_message,
        capture_fields=payload.capture_fields,
        assignment_criteria=payload.assignment_criteria,
    )
    db.add(funnel)
    db.flush()
    _sync_steps(db, company_id=company_id, funnel=funnel, steps=payload.steps)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un funnel con ese nombre",
        ) from exc
    return get_funnel(db, company_id=company_id, funnel_id=funnel.id)


def update_funnel(
    db: Session, *, company_id: UUID, funnel_id: UUID, payload: FunnelUpdate
) -> SalesFunnel:
    funnel = get_funnel(db, company_id=company_id, funnel_id=funnel_id)
    data = payload.model_dump(exclude_unset=True)
    if "is_default" in data and data["is_default"] is False and funnel.system_key == WELCOME_FUNNEL_SYSTEM_KEY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El funnel de bienvenida debe permanecer como predeterminado",
        )
    if "is_default" in data and data["is_default"] is True and funnel.system_key != WELCOME_FUNNEL_SYSTEM_KEY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo el funnel de bienvenida puede ser predeterminado",
        )
    if "status" in data and funnel.system_key == WELCOME_FUNNEL_SYSTEM_KEY and data["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El funnel de bienvenida debe permanecer activo",
        )
    if "is_default" in data:
        _set_default_if_requested(db, company_id=company_id, is_default=bool(data["is_default"]))
        if data["is_default"] is True and funnel.system_key == WELCOME_FUNNEL_SYSTEM_KEY:
            funnel.is_default = True
    steps = data.pop("steps", None)
    for field, value in data.items():
        setattr(funnel, field, value)
    if steps is not None:
        _sync_steps(db, company_id=company_id, funnel=funnel, steps=steps)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un funnel con ese nombre",
        ) from exc
    return get_funnel(db, company_id=company_id, funnel_id=funnel.id)


def delete_funnel(db: Session, *, company_id: UUID, funnel_id: UUID) -> None:
    funnel = get_funnel(db, company_id=company_id, funnel_id=funnel_id)
    if funnel.system_key == WELCOME_FUNNEL_SYSTEM_KEY or funnel.is_default:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se puede eliminar el funnel de bienvenida",
        )
    db.delete(funnel)
    db.commit()
