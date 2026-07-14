from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.routes import router as ai_router
from app.audit.routes import router as audit_router
from app.appointments.routes import router as appointments_router
from app.auth.routes import router as auth_router
from app.companies.routes import router as companies_router
from app.contacts.routes import router as contacts_router
from app.conversations.routes import router as conversations_router
from app.core.config import get_settings
from app.dashboard.routes import router as dashboard_router
from app.events.routes import router as events_router
from app.funnels.routes import router as funnels_router
from app.integrations.routes import router as integrations_router
from app.inventory.routes import router as inventory_router
from app.offboarding.routes import router as offboarding_router
from app.orders.routes import router as orders_router
from app.payments.routes import router as payments_router
from app.products.routes import router as products_router
from app.realtime import realtime_manager, router as realtime_router
from app.users.routes import router as users_router
from app.whatsapp.routes import router as whatsapp_router

settings = get_settings()
cors_allow_origins = [
    origin.strip()
    for origin in settings.cors_allow_origins.split(",")
    if origin.strip()
]

api_router = APIRouter(prefix="/api/v1")

@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    realtime_manager.set_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


api_router.include_router(auth_router)
api_router.include_router(companies_router)
api_router.include_router(users_router)
api_router.include_router(contacts_router)
api_router.include_router(dashboard_router)
api_router.include_router(whatsapp_router)
api_router.include_router(conversations_router)
api_router.include_router(products_router)
api_router.include_router(inventory_router)
api_router.include_router(orders_router)
api_router.include_router(payments_router)
api_router.include_router(appointments_router)
api_router.include_router(ai_router)
api_router.include_router(audit_router)
api_router.include_router(funnels_router)
api_router.include_router(integrations_router)
api_router.include_router(offboarding_router)
api_router.include_router(events_router)
api_router.include_router(realtime_router)

app.include_router(api_router)
