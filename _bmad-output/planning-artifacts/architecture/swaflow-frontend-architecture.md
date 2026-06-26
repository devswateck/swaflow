---
title: "SWAFLOW Frontend Architecture"
type: "architecture"
status: "draft"
updated: "2026-06-11"
stepsCompleted: [1, 2, 3]
lastStep: 3
inputDocuments:
  - "_bmad-output/project-context.md"
  - "_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md"
  - "_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/addendum.md"
  - "_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/review-technical-product.md"
  - "_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/open-questions.md"
  - "_bmad-output/planning-artifacts/epics.md"
  - "_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md"
  - "_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md"
  - "_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md"
  - "_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/frontend-implementation-brief.md"
sources:
  - "../project-context.md"
  - "../ux-designs/ux-Swaflow-2026-06-09/DESIGN.md"
  - "../ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md"
  - "../ux-designs/ux-Swaflow-2026-06-09/frontend-implementation-brief.md"
  - "../../implementation-artifacts/spec-swaflow-visual-shell.md"
---

# SWAFLOW Frontend Architecture

Este documento define la estructura de frontend que debe seguirse antes de ampliar o refactorizar la aplicacion. Su objetivo es evitar que UX, arquitectura e implementacion se mezclen de forma prematura.

## Decision Summary

SWAFLOW seguira siendo una app React/Vite en una sola superficie principal, con `App.tsx` como shell de transicion mientras el sistema se ordena. La arquitectura no introduce un router nuevo ni un rediseño funcional general en esta fase.

La primera version arquitectonica se apoya en cuatro capas:

1. Sistema visual y tokens.
2. Shell global y navegacion.
3. Modulos de producto.
4. Datos, estado y persistencia.

El objetivo es que Dashboard, Inbox y los modulos operativos hereden una base consistente antes de cambiar su comportamiento profundo.

## Architecture Goals

- Separar identidad visual de comportamiento funcional.
- Mantener dark mode como default cuando no exista preferencia guardada.
- Preservar `Zustand`, `api<T>()`, `swaflow_theme` y `swaflow_active_page`.
- Evitar datos falsos o mocks para contenido operativo.
- Permitir que Dashboard use Recharts sin obligar a reescribir todo el frontend.
- Dejar Inbox listo para un rail contextual posterior, pero no implementarlo aqui.

## Non-Goals

- No redisenar backend.
- No cambiar el modelo de multi-tenant.
- No introducir un router nuevo solo por orden visual.
- No rehacer Dashboard ni Inbox por completo en esta etapa.
- No agregar dependencias nuevas fuera de lo ya aprobado para la historia correspondiente.

## Frontend Layers

### 1. Design Tokens

Los tokens de color y superficie son la fuente de verdad visual.

- `tailwind.config.ts` debe exponer tokens semanticos, no colores sueltos dispersos.
- `styles.css` debe resolver dark/light mode y fallback visual.
- El verde/teal deja de ser el color de marca.
- Los acentos de marca son magenta y violeta, con neutros profesionales para el trabajo diario.

Regla: una clase de componente no debe definir por su cuenta la identidad de marca salvo excepcion puntual.

### 2. App Shell

El shell es responsable de:

- Branding visible `SWAFLOW`.
- Header global.
- Sidebar agrupado por dominio.
- Estado de tema.
- Estado de pagina activa.
- Overlay movil y transiciones basicas.

Este shell puede seguir viviendo en `App.tsx` mientras no exista una extraccion clara que reduzca complejidad real.

### 3. Page Modules

Los modulos de pagina se comportan como superficies independientes que consumen el shell:

- Dashboard.
- Inbox.
- Productos.
- Inventario.
- Ordenes.
- Citas.
- IA.
- Funnels.
- WhatsApp.
- Integraciones.
- Ajustes.

Cada modulo debe usar patrones comunes de pagina, encabezado, tabla, estado vacio, error y carga para que la app no se sienta fragmentada.

### 4. Shared UI Primitives

Los primitivos compartidos deben emerger cuando reduzcan duplicacion real.

Objetivo de extraccion:

- `Button`
- `Card`
- `Badge`
- `PageHeader`
- `Sidebar`
- `Input`
- `EmptyState`
- `Skeleton`
- `Notice`

No extraer por moda ni por anticipacion; extraer cuando un patron aparezca varias veces y ya tenga forma estable.

### 5. Data and State

La app usa dos tipos de estado:

- Estado de UI local: tema, pagina activa, filtros, estados de modal, seleccion de chat.
- Estado de dominio: datos traidos por API, cacheados por el cliente, sin inventar valores.

Reglas:

- `Zustand` sigue siendo la capa de auth y preferencias persistidas.
- `TanStack Query` sigue siendo la capa natural para lectura de datos del servidor.
- `localStorage` debe tener fallback seguro para navegadores restringidos.
- Ninguna vista debe depender de una respuesta inventada si el backend no provee el dato.

### 6. Charts

Dashboard usara Recharts como libreria de graficas.

Motivo:

- Permite ejes, tooltips, leyendas y responsividad sin construir SVG manualmente.
- Reduce el costo de mantener paneles profesionales.
- Encaja con la necesidad de graficas serias en un dashboard SaaS operacional.

Limite:

- Solo se usa donde el dato justifique la grafica.
- Si no hay serie real, se muestra estado vacio o resumen textual honesto.

### 7. Inbox Structure

Inbox se modela como un workspace de tres zonas en desktop:

- Lista de conversaciones.
- Hilo de mensajes.
- Rail de contexto y acciones.

En mobile, la composicion se simplifica sin perder jerarquia funcional.

Decisiones:

- La lista debe priorizar actividad reciente, no solo orden alfabetico.
- El rail contextual concentra acciones que hoy estan dispersas.
- El composer conserva borrador si el envio falla.

## Sequence of Implementation

La secuencia correcta es:

1. Cerrar UX y arquitectura.
2. Consolidar shell y tokens.
3. Construir Dashboard con datos reales y Recharts.
4. Construir Inbox con rail contextual.
5. Extraer primitivos comunes cuando el shell se estabilice.

No debe invertirse ese orden salvo una decision explicita del producto.

## Acceptance Gate

Antes de permitir implementacion nueva, deben cumplirse estas condiciones:

- UX de shell, dashboard e inbox documentado.
- Arquitectura de frontend definida en este documento.
- Reglas de marca y tema claras.
- Recharts aprobado para Dashboard.
- No quedan dudas abiertas sobre que parte es documentación y que parte es codigo.

## Open Decisions

- Nombre y entrega final del logo de aplicacion.
- Momento exacto de extraccion de primitivos compartidos.
- Si el Dashboard inicial deriva series de datos existentes o espera nuevos endpoints.
- Si Inbox requiere estructura de datos adicional antes del rail contextual.

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

Swaflow debe operar como una plataforma SaaS multi-tenant para ventas conversacionales por WhatsApp, con IA como capa de orquestacion y backend como fuente de verdad. Las capacidades arquitectonicamente relevantes incluyen dashboard operativo, inbox en tiempo real, configuracion del tenant, usuarios y permisos, WhatsApp Cloud API, catalogo Meta, inventario, ordenes, links de pago, citas, funnels, integraciones auxiliares, webhooks salientes y exportacion del retiro del tenant.

El sistema necesita soportar reglas de negocio criticas: aislamiento por `company_id`, asignacion y reasignacion de chats, activacion y desactivacion de IA por conversacion, reservas de inventario, confirmacion de pagos por webhook, sincronizacion opcional de calendario, y auditoria de cambios operativos.

**Non-Functional Requirements:**

- Aislamiento multi-tenant estricto en toda consulta y mutacion de datos de negocio.
- Seguridad fuerte para secretos, tokens y credenciales cifradas.
- Idempotencia en webhooks y eventos externos.
- Consistencia transaccional para ordenes, pagos, inventario y citas.
- Resiliencia operativa: fallos de IA, WhatsApp, calendario o n8n no deben bloquear la gestion humana ni corromper estados confirmados.
- Rendimiento perceptible en listas, dashboard e inbox con actualizacion cercana a tiempo real.

**Scale & Complexity:**

El proyecto tiene complejidad alta y exige una arquitectura full-stack orientada a dominios. Los componentes arquitectonicos principales ya visibles son:

- Backend core y dominios por modulo.
- Autenticacion y autorizacion por rol y por modulo.
- Multi-tenancy y provisioning operativo de tenants.
- Mensajeria/inbox y sincronizacion de estado.
- IA comercial y reglas de seguridad.
- Catalogo, inventario y ordenes.
- Pagos y adaptadores de pasarela.
- Citas y calendario.
- Eventos, auditoria y exportacion.
- Integraciones auxiliares y webhooks.
- Frontend shell y modulos operativos.

- Primary domain: full-stack web application with transactional backend
- Complexity level: high
- Estimated architectural components: 11+

### Technical Constraints & Dependencies

- Backend actual: Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings, Uvicorn.
- Base de datos vigente: MySQL con `mysql+pymysql`; PostgreSQL queda fuera de la decision activa.
- Frontend actual: React 18, Vite 8, TypeScript 5.6, Tailwind 3.4, TanStack Query, Zustand, Lucide.
- El backend es la fuente de verdad para ordenes, inventario, pagos, permisos y estados criticos.
- n8n solo puede resolver automatizaciones perifericas.
- WhatsApp Cloud API es el canal principal del MVP.
- El PRD ya fija un contrato tecnico minimo para adaptadores de pasarela de pago.
- Ya existe una arquitectura frontend; el siguiente frente real es backend y dominios.

### Cross-Cutting Concerns Identified

- Aislamiento multi-tenant por `company_id`.
- Autorizacion por rol y por modulo.
- Manejo seguro de secretos y credenciales.
- Idempotencia y deduplicacion de webhooks.
- Reservas y liberacion de inventario.
- Consistencia entre ordenes, pagos y citas.
- Realtime y estado honesto en inbox y dashboard.
- Auditoria y trazabilidad de eventos relevantes.
- Integraciones externas tolerantes a fallos.
- UI sin datos inventados y con estados vacios honestos.

## Starter Template Evaluation

### Primary Technology Domain

Full-stack web application, but Swaflow is already a brownfield repo. The only starter-style choice that still matters is the existing Vite + React frontend foundation, not a fresh re-scaffold.

### Starter Options Considered

- `Vite + React + TypeScript` via `npm create vite@latest -- --template react-ts`.
- Manual FastAPI backend foundation using `fastapi dev` and a package-oriented project layout.
- The existing Swaflow repository scaffold already present in the workspace.

### Selected Starter: Existing Swaflow Brownfield Scaffold

**Rationale for Selection:**

The repository already contains working frontend and backend foundations, installed dependencies, domain modules, and architecture constraints. Reinitializing with a new starter would discard those decisions and create avoidable migration churn. The correct foundation is the current codebase, with Vite retained for frontend development and FastAPI retained for backend development.

**Initialization Command:**

```bash
# No re-scaffold command. Continue from the existing Swaflow repository.
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
React 18 with TypeScript on the frontend, Python 3.12 on the backend.

**Styling Solution:**
Tailwind CSS with the existing semantic token system and dark-mode-first shell.

**Build Tooling:**
Vite for frontend dev/build, `tsc -b` for TypeScript validation, `eslint` for linting, and FastAPI's development server workflow for the backend.

**Testing Framework:**
The repo already uses pytest on the backend; the frontend currently verifies behavior with build and lint gates rather than a new starter-level UI test harness.

**Code Organization:**
Brownfield monorepo split into `frontend/` and `backend/`, with backend domains organized by business area and frontend held in a single shell-oriented app structure.

**Development Experience:**
Fast refresh in Vite, FastAPI dev server iteration, local environment files per app, and the existing `api<T>()`/Zustand data flow rather than a fresh generated starter.

**Note:** There is no project initialization step to perform here. The implementation work should continue from the current repository state.

## Authentication & Security

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- JWT remains the authentication mechanism for logged-in sessions.
- Authorization is enforced with RBAC plus module-level permissions.
- Every business-data query and mutation must be tenant-scoped via `company_id`.
- Cross-tenant access to a real resource must return `404`, not `403`.
- Secrets, API keys, tokens, and webhook credentials must be stored encrypted and never exposed in UI, logs, or API responses.
- Webhooks that can change state must be signature-validated or secret-validated before any business mutation.
- Payment and external-event processing must be idempotent to prevent duplicate state changes.

**Important Decisions (Shape Architecture):**

- Same-tenant permission denial should use `403` when the user exists in the tenant but lacks the required module access.
- Tenant guards and permission checks must exist in backend service logic, not only in the frontend shell.
- Webhook and integration payloads should preserve raw metadata only where needed for auditing and replay-safe processing.
- Security helpers should be reusable across domains so auth rules do not drift between modules.

**Deferred Decisions (Post-MVP):**

- Refresh-token rotation and longer-lived session hardening can be refined after the core JWT flow is stable.
- Centralized secret rotation tooling can be added later if operations require it.

### Authentication & Security

Swaflow will use JWT for authenticated user sessions and will keep authorization separate from authentication. The security model is layered:

- Authenticated identity comes from JWT.
- Module access comes from role plus explicit permissions.
- Tenant access comes from `company_id` in the backend context, not from UI state.
- Secrets stay encrypted at rest and redacted everywhere else.
- Public webhooks must be validated before any write path runs.

This model is necessary because Swaflow is not a simple CRUD app. It handles orders, inventory, payments, conversations, and tenant-scoped integrations where a single bad guard can create cross-tenant leakage or duplicate financial state.

### Decision Impact Analysis

**Implementation Sequence:**

1. Build shared auth and tenant-guard helpers in backend.
2. Apply the guards to `companies`, `users`, and other business domains.
3. Add encrypted secret handling for integrations and webhook credentials.
4. Add idempotent payment and event processing.
5. Expose only redacted, tenant-safe data to the frontend.

**Cross-Component Dependencies:**

- Every business domain depends on the tenant guard.
- Payments depend on secure secret storage and webhook validation.
- Inventory and order state depend on idempotent event handling.
- The frontend depends on backend-enforced permissions, not hidden nav alone.

### Integration Architecture

Swaflow will use a normalized integration layer with explicit adapters per provider. The backend remains the source of truth, while integrations are thin translators around canonic domain contracts.

**Core decisions:**

- `PaymentGatewayAdapter` for links, webhooks, status mapping, and idempotency.
- `WhatsAppAdapter` for inbound/outbound messaging and provider-specific payload normalization.
- `CalendarAdapter` for availability, booking, and synchronization with external calendars.
- `OutboundWebhookDispatcher` for tenant-scoped event delivery to external systems.

**Rules:**

- Integrations are tenant-scoped and credentialed per `company_id`.
- Secrets must stay encrypted at rest and redacted everywhere else.
- Provider payloads may be preserved as JSON metadata, but domain truth is always normalized first.
- Webhook/event dispatch should use a durable outbox or equivalent idempotent mechanism.
- n8n remains peripheral automation only, never the owner of critical state.

**Implementation impact:**

- Integration contracts must be stable enough to survive provider swaps.
- Each adapter must normalize errors into backend-owned categories.
- The backend should expose a single canonical flow for payment, WhatsApp, calendar, and webhook operations.

### Data Architecture

Swaflow will use a normalized relational core in MySQL, with JSON reserved for metadata, provider payloads, and flexible configuration fields.

**Core decisions:**

- Every tenant-owned table must include `company_id`.
- Business entities remain queryable and reportable through relational columns.
- JSON is allowed only where flexibility beats queryability, such as provider metadata or configurable rules.
- Alembic migrations must be backward-compatible first, with destructive cleanup deferred.

**Modeling rules:**

- Prefer domain tables for companies, users, contacts, conversations, messages, products, inventory, orders, payments, appointments, integrations, events, and audit.
- Use unique constraints scoped by `company_id` where natural keys exist.
- Index the columns used by tenant filters, status filters, timestamps, and idempotency checks.
- Keep audit/event tables durable enough to explain external state transitions and replay-safe behavior.

**Implementation impact:**

- The repository already has `TenantMixin` and `ensure_same_company` as building blocks.
- Persistence helpers should enforce tenant scoping consistently in repos and services.
- Webhook and payment idempotency will likely require explicit processed-event records.
- Large-table migrations should be additive and rolled out carefully to avoid MySQL locking surprises.

### Events, Audit & Outbox

Swaflow should treat events and audit as first-class persistence concerns, not as incidental logging.

**Core decisions:**

- Use durable event records for meaningful state transitions across orders, payments, conversations, appointments, integrations, and permissions.
- Use audit records for who changed what, when, and under which tenant context.
- Use an outbox or equivalent durable dispatch pattern for external webhooks and asynchronous delivery.
- Keep event and audit data tenant-scoped and queryable.
- Use processed-event tracking to prevent duplicate downstream side effects.

**Rules:**

- Any action that changes business truth should leave a durable trace.
- External retries must be safe to replay.
- Outbound notifications and webhooks should publish only after the backend commits the source-of-truth change.
- Audit entries must not contain plaintext secrets.

**Implementation impact:**

- Event tables should support idempotency keys, status, timestamps, and tenant ownership.
- Audit tables should support operational review and offboarding/export use cases.
- The outbox should be the bridge between committed domain changes and peripheral integrations like n8n or outbound webhooks.

### API & Communication Patterns

Swaflow will use a stable versioned REST API under `/api/v1`, with thin routers and business logic in domain services.

**Core decisions:**

- Backend requests authenticate first, resolve tenant next, then enforce tenant guard, then check RBAC/module permissions, then run business validation.
- Frontend should consume backend data through `api<T>()` wrappers and TanStack Query.
- Responses should stay stable: `data` for single resources, `items + meta` for paginated lists, and a shared error envelope for failures.
- Same-tenant permission denial should use `403`.
- Cross-tenant resources should use `404`.
- Invalid payloads or invalid business state should use `422`.
- Conflicts such as stock, duplicate events, or idempotency collisions should use `409`.

**Communication rules:**

- Routes should be noun-first and plural where appropriate.
- Non-CRUD operations should use explicit action subpaths, such as payment confirmation or status transitions.
- Error messages visible to users should remain in Spanish.
- Controllers should not own business rules; domain services should.

**Implementation impact:**

- A shared API contract should be documented so the frontend and backend stay aligned.
- Error parsing should be centralized in the frontend rather than repeated per screen.
- Tenant and permission helpers should be reusable across every business module.

### Infrastructure & Deployment

Swaflow should keep deployment simple and predictable: FastAPI + MySQL + Vite frontend, with `.env`-based configuration, Docker for local development, and separate dev/staging/prod environments.

**Core decisions:**

- Keep the backend stateless.
- Persist state in MySQL and minimize external file/state dependencies.
- Standardize local startup around the existing Docker Compose and README flow.
- Make lint, tests, migration checks, and container build validation mandatory in CI/CD.
- Expose health checks for the app and critical dependencies.

**Operational assumptions:**

- Scale vertically first, then horizontally only if the stateless backend needs it.
- Use structured logs and baseline operational tracing rather than heavy platform complexity too early.
- Treat migrations as a first-class operational risk and validate them in CI.

**Implementation impact:**

- Required environment variables should be documented per environment.
- Deployment should remain compatible with the current brownfield repo structure.
- Kubernetes or other platform overhead should stay out unless growth forces it.
