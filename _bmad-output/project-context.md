---
project_name: "Swaflow"
user_name: "Camilosanchez"
date: "2026-06-08"
status: "complete"
workflow_state: "context_consolidated"
sections_completed:
  - "context_discovery"
  - "technology_stack"
  - "language_rules"
  - "framework_rules"
  - "testing_rules"
  - "quality_rules"
  - "workflow_rules"
  - "anti_patterns"
rule_count: 44
optimized_for_llm: true
primary_input:
  - "proyecto_saas_ia_comercial_multitenant.md"
project_knowledge: "docs"
database_decision: "MySQL vigente via mysql+pymysql; no PostgreSQL salvo decision explicita posterior"
---

# Project Context for AI Agents

Este archivo contiene reglas criticas para agentes de IA que implementen codigo en Swaflow. Mantenerlo conciso: debe cubrir detalles no obvios que evitan errores reales de implementacion.

---

## Technology Stack & Versions

- Producto: SaaS multi-tenant para asistente comercial IA por WhatsApp; backend decide acciones transaccionales y la IA solo orquesta conversaciones.
- Backend: Python `>=3.12`, FastAPI `>=0.115.0`, Uvicorn `>=0.30.6`, SQLAlchemy `>=2.0.32`, Alembic `>=1.13.2`, Pydantic Settings `>=2.4.0`.
- Base de datos vigente: MySQL con `mysql+pymysql`, charset `utf8mb4`; Docker local usa `mysql:8.4`. No migrar a PostgreSQL aunque el documento base historico lo mencione.
- Auth/seguridad backend: JWT con `python-jose[cryptography]`, `passlib[bcrypt]`, `bcrypt>=4.0,<4.1`, `cryptography>=43.0.0`.
- Integraciones backend: `httpx` para llamadas HTTP, WhatsApp Graph API configurable, Wompi como proveedor de pagos cuando exista integracion activa.
- Redis esta en entorno y Docker Compose, pero no hay cola activa implementada; no introducir Celery/RQ/jobs sin decision explicita.
- Frontend: React `^18.3.1`, Vite `^8.0.13`, TypeScript `~5.6.3`, Tailwind CSS `^3.4.14`, TanStack Query `^5.59.16`, Zustand `^5.0.1`, Lucide React `^0.468.0`.
- Frontend local: API por defecto `http://localhost:8000`; dev server esperado por CORS en `http://localhost:5173` y `http://127.0.0.1:5173`.

## Critical Implementation Rules

### Language-Specific Rules

- TypeScript debe seguir `strict: true`, `allowJs: false`, `isolatedModules: true` y `noEmit: true`; evitar `any` salvo justificacion local y pequena.
- El frontend usa `moduleResolution` `Node` en app y `Bundler` en config Vite; no introducir aliases o resolucion nueva sin configurar TS/Vite juntos.
- Los mensajes de error visibles para usuario deben mantenerse en espanol; `frontend/src/lib/api.ts` ya centraliza formato de errores FastAPI.
- Python usa SQLAlchemy 2 con `Mapped`, `mapped_column`, `Session` sincronica y funciones de servicio explicitas; mantener ese estilo antes de introducir patrones async.
- Los servicios backend reciben `Session` y `company_id` explicitamente para operaciones tenant-scoped; no leer tenant desde estado global dentro de servicios.
- UUIDs usan `sqlalchemy.types.Uuid(as_uuid=True)` en mixins/modelos; validar compatibilidad MySQL antes de agregar tipos SQL especificos.
- No escribir secretos, tokens ni credenciales en codigo, tests o documentacion generada; usar settings/env e integraciones cifradas.

### Framework-Specific Rules

- Backend organizado por dominio en `backend/app/<dominio>/` con `models.py`, `routes.py`, `schemas.py` y `service.py`; mantener esta frontera para modulos nuevos.
- Registrar routers nuevos en `backend/app/main.py` y modelos nuevos en `backend/app/models.py`; Alembic depende de que SQLAlchemy descubra todos los modelos.
- Toda tabla de negocio tenant-scoped debe incluir `TenantMixin` salvo excepcion global justificada; los indices/restricciones unicas deben incluir `company_id`.
- El patron de aislamiento tenant es `404`, no `403`, cuando un recurso existe en otra empresa; usar `ensure_same_company` o queries con `company_id`.
- Rutas autenticadas toman `current_user.company_id` desde `get_current_user`; solo superadmin puede cruzar tenant donde el codigo ya lo permite explicitamente.
- Cambios transaccionales deben vivir en servicios FastAPI y base de datos, no en n8n ni en la IA: ordenes, pagos, inventario, permisos y estados criticos.
- `create_event` es el patron para eventos internos relevantes; webhooks salientes se filtran por tenant y pueden firmarse con HMAC si hay `secret_token`.
- Frontend actual concentra UI en `frontend/src/App.tsx` y utilidades en `frontend/src/lib`; extraer componentes gradualmente solo cuando reduzca complejidad real.
- Usar `api<T>()` para llamadas HTTP del frontend; no duplicar manejo de Bearer token, expiracion de sesion ni parsing de errores.
- Usar Zustand existente para auth y token `swaflow_token`; no crear otro almacenamiento paralelo.
- Usar iconos de `lucide-react` para acciones visuales y respetar tokens Tailwind existentes: `ink`, `line`, `panel`, `brand`, `warn`, `danger`.

### Testing Rules

- Backend usa pytest en `backend/tests`; la suite actual cubre bootstrap de empresa/owner, auth, aislamiento tenant, ordenes, inventario, IA/catalogo y WhatsApp.
- Tests usan SQLite en memoria para velocidad, pero la base vigente de la app es MySQL; no introducir SQL o migraciones que solo funcionen en SQLite.
- Cambios en servicios transaccionales deben agregar/actualizar pruebas de servicio para estados, eventos, commits y errores.
- Cambios en multi-tenancy deben probar acceso positivo del tenant correcto y `404` para tenant ajeno.
- Cambios en ordenes/pagos/inventario deben probar reserva, liberacion, descuento, moneda unica, stock insuficiente e idempotencia cuando aplique.
- Cambios en WhatsApp o pagos externos deben cubrir payloads validos, payloads incompletos, firma/credenciales cuando aplique y fallbacks sin integracion activa.
- Si se agrega un modelo SQLAlchemy, debe estar cubierto por migracion Alembic y cargado por `app.models` para que tests y metadata no diverjan.

### Code Quality & Style Rules

- No modificar el motor de base de datos a PostgreSQL por arrastre del documento historico; MySQL es la decision activa en README, `.env.example`, Alembic y Docker Compose.
- Mantener migraciones Alembic compatibles con MySQL: revisar longitudes, indices, defaults, JSON, UUID y operaciones que MySQL no soporte igual que PostgreSQL.
- `backend/.env`, `frontend/.env`, `.venv`, `node_modules`, `dist`, `__pycache__` y caches no son fuente; no copiar patrones desde artefactos generados.
- No introducir abstracciones amplias si el patron local es servicio + schema + route; preferir cambios pequenos, domain-scoped y faciles de probar.
- Mantener nombres de eventos estables y expresivos: por ejemplo `order.created`, `order.waiting_payment`, `order.paid`, `order.cancelled`, `order.payment_status`.
- Errores HTTP de negocio usan `HTTPException` con status preciso: `404` para no encontrado/otro tenant, `409` para conflicto de stock, `422` para estado o payload invalido.
- Comentarios solo cuando aclaren reglas de negocio o integraciones no obvias; evitar comentarios narrativos sobre codigo evidente.

### Development Workflow Rules

- Backend local: `cd backend`, preparar `.env`, `docker compose up -d`, instalar `.[dev]`, ejecutar `alembic upgrade head`, correr `uvicorn app.main:app --reload`.
- Frontend local: `cd frontend`, preparar `.env`, `npm install`, `npm run dev`; build esperado con `npm run build` y lint con `npm run lint`.
- Antes de cambios de schema, revisar modelos actuales y migraciones existentes bajo `backend/migrations/versions`; no editar migraciones antiguas aplicadas salvo instruccion explicita.
- Para MySQL remoto por tunel, usar `DATABASE_URL` con `127.0.0.1:3307` segun README; no documentar credenciales reales.
- n8n queda como automatizacion auxiliar para notificaciones, sincronizaciones, calendarios, resumenes y webhooks perifericos; no convertirlo en fuente de verdad.
- Mantener este archivo actualizado cuando cambien stack, DB, patrones transaccionales o modulos principales; eliminar reglas que se vuelvan obvias o obsoletas.

### Critical Don't-Miss Rules

- Multi-tenancy: toda query de datos de negocio debe filtrar por `company_id`; nunca confiar solo en IDs recibidos desde frontend, IA, WhatsApp o webhooks.
- La IA no debe inventar precios, stock, disponibilidad, links de pago, politicas comerciales ni agenda; debe consultar tools/servicios backend tenant-scoped.
- Si una intencion de IA tiene baja confianza o falta informacion para una accion critica, pedir aclaracion antes de crear ordenes, pagos, citas o cambios de estado.
- Catalogo para IA/WhatsApp debe usar stock real disponible: `quantity_available - quantity_reserved`; productos sin stock o sin mapping Meta requerido no deben ofrecerse como comprables.
- `create_order` valida contacto, conversacion opcional, producto activo, stock suficiente y moneda unica; tambien reserva inventario con `quantity_reserved`.
- Al marcar pago como `paid`, backend descuenta `quantity_available`, libera reserva y emite evento; no confirmar pagos desde frontend/IA sin pasar por servicio de pagos/backend.
- Cancelar orden debe liberar reservas y registrar evento; no dejar inventario reservado despues de estados terminales.
- WhatsApp Cloud API debe usar credenciales cifradas desde `CompanyIntegration` o `WhatsAppAccount`; tokens nunca van hardcodeados.
- Mensajes salientes de WhatsApp deben registrarse como mensajes internos y publicar realtime/eventos cuando aplique.
- Webhooks salientes deben respetar tenant, tipo de evento y firma HMAC si hay secreto; fallos de entrega no deben romper transacciones criticas ya confirmadas.
- Superadmin es excepcion explicita, no regla general; no ampliar acceso cross-tenant sin pruebas dedicadas.
- Redis y n8n presentes en configuracion no implican que exista procesamiento asincrono critico; no asumir colas, workers o retries transaccionales.
- El documento historico `proyecto_saas_ia_comercial_multitenant.md` es fuente de producto, pero las decisiones implementadas vigentes prevalecen cuando haya conflicto tecnico.

---

## Usage Guidelines

**For AI Agents:**

- Leer este archivo antes de implementar codigo en Swaflow.
- Seguir todas las reglas; si hay duda, preferir la opcion mas restrictiva para tenant, pagos, inventario y secretos.
- Verificar el codigo actual antes de introducir patrones nuevos.
- Actualizar este archivo cuando emerjan decisiones o reglas nuevas relevantes.

**For Humans:**

- Mantener este archivo corto y enfocado en necesidades de agentes.
- Actualizarlo cuando cambien tecnologia, base de datos, modulos principales o reglas de negocio.
- Revisarlo periodicamente para quitar reglas obsoletas.

Last Updated: 2026-06-08
