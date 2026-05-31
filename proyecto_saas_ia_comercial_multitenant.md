# Proyecto: SaaS Multi-Tenant de Asistente Comercial IA para WhatsApp

## 1. Visión del producto

Construir una plataforma SaaS multi-tenant que permita a empresas configurar un asistente comercial con IA para atender clientes por WhatsApp, gestionar conversaciones, detectar intención de compra, consultar catálogo e inventario, generar links de pago, confirmar pagos mediante webhooks, registrar ventas y permitir agendamiento de citas cuando el cliente no compra de inmediato.

El producto NO debe iniciar como un clon completo de Talos Flow, Kommo, HubSpot, Shopify, Calendly o un ERP. El enfoque inicial debe ser resolver muy bien el proceso comercial conversacional.

### Propuesta de valor inicial

> Asistente comercial IA para WhatsApp que responde clientes, califica leads, vende productos, genera links de pago, registra ventas y agenda citas cuando el cliente aún no está listo para comprar.

---

## 2. Alcance del MVP

### Incluido en el MVP

1. Multi-tenant básico.
2. Conexión con WhatsApp Cloud API.
3. Inbox de conversaciones.
4. Motor de conversación con IA.
5. Clasificación de intención del cliente.
6. Catálogo de productos.
7. Inventario básico.
8. Creación de órdenes.
9. Generación de links de pago.
10. Confirmación de pago por webhook.
11. Registro de venta.
12. Agendamiento de citas.
13. Notificaciones a humanos.
14. Integración auxiliar con n8n para automatizaciones no críticas.
15. Webhooks salientes configurables por empresa.

### Fuera del MVP

1. Constructor visual avanzado tipo Talos Flow.
2. Omnicanal completo desde el inicio.
3. Telegram, Instagram y Messenger en primera versión.
4. ERP completo.
5. CRM avanzado.
6. Facturación electrónica.
7. RAG con documentos PDF.
8. Multiagentes complejos.
9. Voz.
10. Automatizaciones críticas manejadas por n8n.

---

## 3. Principios de arquitectura

### Regla principal

Si afecta dinero, inventario, pagos, pedidos o estados críticos, debe vivir en el backend.

Si notifica, sincroniza o ejecuta tareas periféricas, puede ir por n8n.

### Distribución de responsabilidades

```text
FastAPI Backend = núcleo transaccional y multi-tenant
PostgreSQL = fuente de verdad
OpenAI Tools = capa controlada para acciones de IA
n8n = automatizaciones auxiliares
WhatsApp Cloud API = canal principal
Pasarela de pagos = generación y confirmación de pagos
Frontend React = panel administrativo e inbox
```

---

## 4. Stack recomendado

### Backend

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic
- PostgreSQL
- Redis
- Celery o RQ para jobs asíncronos
- JWT para autenticación
- bcrypt/passlib para contraseñas

### Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- TanStack Query
- Zustand o Redux Toolkit
- React Hook Form
- Zod
- React Flow en fase posterior

### IA

- OpenAI API
- Structured Outputs
- Function Calling / Tools
- Prompts por tenant
- Prompts por etapa comercial

### Infraestructura

- Docker
- Docker Compose para desarrollo local
- Railway, Render, VPS o AWS para despliegue inicial
- PostgreSQL administrado o contenedor dedicado
- Redis administrado o contenedor dedicado

---

## 5. Arquitectura general

```text
Cliente WhatsApp
    ↓
WhatsApp Cloud API Webhook
    ↓
FastAPI /webhooks/whatsapp
    ↓
Guardar mensaje en PostgreSQL
    ↓
Motor conversacional
    ↓
Clasificador de intención
    ↓
Tools del backend
    ↓
Respuesta generada por IA
    ↓
WhatsApp Cloud API
```

### Flujo de compra

```text
Cliente pregunta por producto
    ↓
IA detecta intención de compra
    ↓
Backend consulta producto e inventario
    ↓
Backend crea orden pending/waiting_payment
    ↓
Backend genera link de pago
    ↓
IA envía link al cliente
    ↓
Pasarela confirma pago por webhook
    ↓
Backend marca orden como paid
    ↓
Backend registra venta
    ↓
Backend dispara evento order.paid
    ↓
n8n/humano recibe notificación
```

### Flujo de cita

```text
Cliente no compra o quiere asesoría
    ↓
IA detecta intención de agendar
    ↓
Backend consulta disponibilidad
    ↓
Backend crea appointment
    ↓
n8n puede crear evento en Google Calendar
    ↓
Backend confirma al cliente
    ↓
Humano recibe notificación
```

---

## 6. Multi-tenancy

### Estrategia inicial recomendada

Usar una sola base de datos compartida con columna `company_id` en todas las tablas principales.

Esto permite avanzar rápido y mantener bajo control el costo operativo.

### Regla obligatoria

Toda consulta de datos de negocio debe filtrar por `company_id`.

Ejemplo:

```sql
SELECT *
FROM orders
WHERE company_id = :company_id;
```

Nunca consultar datos de negocio sin `company_id`.

### Tablas que deben tener company_id

- users
- whatsapp_accounts
- contacts
- conversations
- messages
- products
- inventory
- orders
- order_items
- appointments
- ai_agents
- funnel_steps
- company_integrations
- outbound_webhooks
- events

---

## 7. Modelo de datos inicial

### companies

```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(150) NOT NULL,
    email VARCHAR(200) NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'agent',
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(company_id, email)
);
```

Roles iniciales:

```text
owner
admin
agent
viewer
```

### whatsapp_accounts

```sql
CREATE TABLE whatsapp_accounts (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    phone_number_id VARCHAR(100) NOT NULL,
    business_account_id VARCHAR(100),
    access_token_encrypted TEXT NOT NULL,
    verify_token VARCHAR(255) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### contacts

```sql
CREATE TABLE contacts (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(150),
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(200),
    source VARCHAR(50) DEFAULT 'whatsapp',
    status VARCHAR(30) DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(company_id, phone)
);
```

### conversations

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    contact_id UUID NOT NULL REFERENCES contacts(id),
    channel VARCHAR(50) NOT NULL DEFAULT 'whatsapp',
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    assigned_user_id UUID REFERENCES users(id),
    current_step VARCHAR(100),
    last_message_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Estados sugeridos:

```text
open
waiting_customer
waiting_human
closed
```

### messages

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    external_message_id VARCHAR(150),
    sender_type VARCHAR(50) NOT NULL,
    content TEXT,
    message_type VARCHAR(50) DEFAULT 'text',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

sender_type:

```text
customer
ai
agent
system
```

### products

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    sku VARCHAR(100),
    price NUMERIC(14,2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'COP',
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(company_id, sku)
);
```

### inventory

```sql
CREATE TABLE inventory (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity_available INTEGER NOT NULL DEFAULT 0,
    quantity_reserved INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(company_id, product_id)
);
```

### orders

```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    contact_id UUID NOT NULL REFERENCES contacts(id),
    conversation_id UUID REFERENCES conversations(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total NUMERIC(14,2) NOT NULL DEFAULT 0,
    currency VARCHAR(10) NOT NULL DEFAULT 'COP',
    payment_provider VARCHAR(50),
    payment_reference VARCHAR(150),
    payment_link TEXT,
    payment_status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Estados de orden:

```text
pending
waiting_payment
paid
processing
cancelled
expired
```

### order_items

```sql
CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(14,2) NOT NULL,
    total NUMERIC(14,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### appointments

```sql
CREATE TABLE appointments (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    contact_id UUID NOT NULL REFERENCES contacts(id),
    conversation_id UUID REFERENCES conversations(id),
    assigned_user_id UUID REFERENCES users(id),
    scheduled_at TIMESTAMP NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 30,
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled',
    notes TEXT,
    external_calendar_event_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Estados de cita:

```text
scheduled
confirmed
cancelled
completed
no_show
```

### ai_agents

```sql
CREATE TABLE ai_agents (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    name VARCHAR(150) NOT NULL,
    system_prompt TEXT NOT NULL,
    tone VARCHAR(100),
    rules JSONB DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### company_integrations

```sql
CREATE TABLE company_integrations (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    type VARCHAR(100) NOT NULL,
    credentials_encrypted TEXT,
    config JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Tipos iniciales:

```text
wompi
mercado_pago
google_calendar
smtp
sendgrid
n8n
kommo
hubspot
```

### outbound_webhooks

```sql
CREATE TABLE outbound_webhooks (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    event_type VARCHAR(100) NOT NULL,
    target_url TEXT NOT NULL,
    secret_token TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### events

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP
);
```

---

## 8. Eventos internos del sistema

Eventos mínimos:

```text
message.received
conversation.created
lead.qualified
order.created
order.waiting_payment
order.paid
order.cancelled
appointment.created
appointment.cancelled
human.handoff_requested
payment.failed
```

Estos eventos pueden disparar:

1. Webhooks salientes.
2. Notificaciones por correo.
3. Mensajes internos.
4. Workflows de n8n.
5. Logs de auditoría.

---

## 9. n8n dentro del producto

### Decisión técnica

n8n NO debe ser el núcleo multi-tenant.

No crear un proyecto de n8n por cliente en el MVP. Eso convierte el SaaS en una agencia de automatización difícil de escalar.

### Uso correcto de n8n

n8n debe funcionar como ejecutor auxiliar para automatizaciones no críticas.

Ejemplos:

```text
Enviar correo al asesor cuando se pague una orden.
Crear evento en Google Calendar cuando se agenda una cita.
Enviar resumen diario de ventas.
Sincronizar contacto con una hoja de cálculo.
Enviar lead a un CRM externo.
```

### Uso incorrecto de n8n

No usar n8n para:

```text
Validar stock.
Crear órdenes como fuente de verdad.
Confirmar pagos como fuente principal.
Cambiar estados críticos sin pasar por backend.
Manejar permisos multi-tenant.
Guardar clientes como base principal.
```

### Patrón recomendado

```text
FastAPI genera evento
    ↓
FastAPI guarda evento en DB
    ↓
FastAPI llama webhook genérico de n8n
    ↓
n8n ejecuta acción auxiliar
    ↓
n8n puede devolver resultado al backend
```

Payload sugerido para n8n:

```json
{
  "company_id": "uuid",
  "event_type": "order.paid",
  "timestamp": "2026-05-18T10:30:00Z",
  "data": {
    "order_id": "uuid",
    "customer_name": "Cliente Demo",
    "customer_phone": "573000000000",
    "total": 250000,
    "currency": "COP"
  }
}
```

---

## 10. IA y tools

### Regla central

La IA conversa, pero el backend decide.

La IA no debe:

```text
Calcular precios definitivos.
Modificar inventario directamente.
Confirmar pagos.
Crear citas sin validar disponibilidad.
Inventar políticas comerciales.
Inventar disponibilidad.
```

### Tools iniciales

#### search_products

Busca productos activos de la empresa.

Input:

```json
{
  "query": "camiseta negra talla m"
}
```

Output:

```json
{
  "products": [
    {
      "id": "uuid",
      "name": "Camiseta negra",
      "price": 80000,
      "currency": "COP",
      "available": true
    }
  ]
}
```

#### check_stock

Valida stock real.

Input:

```json
{
  "product_id": "uuid",
  "quantity": 1
}
```

Output:

```json
{
  "available": true,
  "quantity_available": 5
}
```

#### create_order

Crea orden pendiente.

Input:

```json
{
  "contact_id": "uuid",
  "conversation_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 1
    }
  ]
}
```

Output:

```json
{
  "order_id": "uuid",
  "status": "waiting_payment",
  "total": 80000,
  "currency": "COP"
}
```

#### generate_payment_link

Genera link de pago.

Input:

```json
{
  "order_id": "uuid"
}
```

Output:

```json
{
  "payment_link": "https://...",
  "payment_reference": "ref_123"
}
```

#### schedule_appointment

Crea cita.

Input:

```json
{
  "contact_id": "uuid",
  "conversation_id": "uuid",
  "scheduled_at": "2026-05-20T14:00:00-05:00",
  "notes": "Cliente interesado en asesoría"
}
```

Output:

```json
{
  "appointment_id": "uuid",
  "status": "scheduled"
}
```

#### transfer_to_human

Solicita atención humana.

Input:

```json
{
  "conversation_id": "uuid",
  "reason": "Cliente solicita asesor humano"
}
```

Output:

```json
{
  "status": "waiting_human"
}
```

---

## 11. Clasificación de intención

Intenciones iniciales:

```text
buy_product
ask_product_info
schedule_appointment
request_human
support
complaint
unknown
```

Respuesta esperada del clasificador:

```json
{
  "intent": "buy_product",
  "confidence": 0.91,
  "entities": {
    "product_name": "camiseta negra",
    "quantity": 1
  }
}
```

Regla:

Si `confidence < 0.70`, la IA debe hacer una pregunta aclaratoria en vez de ejecutar una acción crítica.

---

## 12. Prompts base

### System prompt general por tenant

```text
Eres un asistente comercial de {{company_name}}.
Tu objetivo es atender al cliente, responder dudas comerciales, ayudarlo a comprar productos disponibles o agendar una cita si aún no desea comprar.

Reglas obligatorias:
1. No inventes precios.
2. No inventes disponibilidad.
3. No confirmes pagos manualmente.
4. No prometas entregas que no estén configuradas.
5. Si el cliente quiere comprar, consulta productos y stock usando las herramientas disponibles.
6. Si el cliente desea pagar, crea una orden y genera un link de pago usando las herramientas disponibles.
7. Si el cliente no quiere comprar todavía, ofrece agendar una cita o pasar con un asesor.
8. Si el cliente está molesto o pide humano, transfiere a un asesor.
9. Responde de forma clara, breve y comercial.
```

### Prompt de clasificación

```text
Clasifica el mensaje del cliente en una de estas intenciones:
- buy_product
- ask_product_info
- schedule_appointment
- request_human
- support
- complaint
- unknown

Devuelve únicamente JSON válido con:
intent, confidence y entities.
```

---

## 13. Backend: módulos sugeridos

```text
app/
  main.py
  core/
    config.py
    security.py
    database.py
    tenant.py
  auth/
    routes.py
    service.py
    schemas.py
  companies/
    models.py
    routes.py
    service.py
  users/
    models.py
    routes.py
    service.py
  whatsapp/
    routes.py
    service.py
    schemas.py
  conversations/
    models.py
    routes.py
    service.py
  messages/
    models.py
    service.py
  contacts/
    models.py
    routes.py
    service.py
  products/
    models.py
    routes.py
    service.py
  inventory/
    models.py
    routes.py
    service.py
  orders/
    models.py
    routes.py
    service.py
  payments/
    routes.py
    service.py
    providers/
      wompi.py
      mercado_pago.py
  appointments/
    models.py
    routes.py
    service.py
  ai/
    service.py
    prompts.py
    tools.py
    intent_classifier.py
  integrations/
    models.py
    routes.py
    service.py
  events/
    models.py
    service.py
    dispatcher.py
  webhooks/
    routes.py
    service.py
```

---

## 14. API endpoints iniciales

### Auth

```text
POST /auth/login
POST /auth/refresh
GET  /auth/me
```

### Companies

```text
POST /companies
GET  /companies/{id}
PUT  /companies/{id}
```

### Users

```text
GET    /users
POST   /users
GET    /users/{id}
PUT    /users/{id}
DELETE /users/{id}
```

### WhatsApp

```text
GET  /webhooks/whatsapp
POST /webhooks/whatsapp
POST /whatsapp/accounts
GET  /whatsapp/accounts
```

### Conversations

```text
GET  /conversations
GET  /conversations/{id}
POST /conversations/{id}/assign
POST /conversations/{id}/close
POST /conversations/{id}/send-message
```

### Products

```text
GET    /products
POST   /products
GET    /products/{id}
PUT    /products/{id}
DELETE /products/{id}
```

### Inventory

```text
GET  /inventory
PUT  /inventory/{product_id}
POST /inventory/{product_id}/adjust
```

### Orders

```text
GET  /orders
POST /orders
GET  /orders/{id}
POST /orders/{id}/payment-link
POST /orders/{id}/cancel
```

### Payments

```text
POST /webhooks/payments/wompi
POST /webhooks/payments/mercado-pago
```

### Appointments

```text
GET  /appointments
POST /appointments
GET  /appointments/{id}
PUT  /appointments/{id}
POST /appointments/{id}/cancel
```

### Integrations

```text
GET  /integrations
POST /integrations
PUT  /integrations/{id}
```

### Outbound webhooks

```text
GET    /outbound-webhooks
POST   /outbound-webhooks
PUT    /outbound-webhooks/{id}
DELETE /outbound-webhooks/{id}
```

---

## 15. Frontend: módulos iniciales

```text
src/
  app/
  components/
  features/
    auth/
    dashboard/
    inbox/
    products/
    inventory/
    orders/
    appointments/
    ai-agent/
    integrations/
    settings/
  lib/
    api.ts
    auth.ts
    queryClient.ts
  routes/
```

### Pantallas del MVP

1. Login.
2. Dashboard general.
3. Inbox de conversaciones.
4. Detalle de conversación.
5. Productos.
6. Inventario.
7. Órdenes.
8. Citas.
9. Configuración de IA.
10. Configuración de WhatsApp.
11. Integraciones.
12. Webhooks salientes.

---

## 16. Seguridad

### Reglas obligatorias

1. Cifrar tokens de WhatsApp, pasarelas y calendarios.
2. Nunca guardar credenciales en texto plano.
3. Validar firma de webhooks de pagos.
4. Validar origen y token de webhooks de WhatsApp.
5. Aplicar rate limiting en endpoints públicos.
6. Auditar cambios críticos.
7. Filtrar siempre por `company_id`.
8. Separar roles por permisos.
9. No exponer IDs internos innecesarios al cliente final.
10. No permitir que la IA ejecute SQL directo.

---

## 17. Estados críticos

### Orden

```text
pending → waiting_payment → paid → processing
pending → cancelled
waiting_payment → expired
waiting_payment → cancelled
```

### Conversación

```text
open → waiting_customer
open → waiting_human
waiting_human → open
open → closed
```

### Cita

```text
scheduled → confirmed
scheduled → cancelled
confirmed → completed
confirmed → no_show
```

---

## 18. Roadmap

### Fase 1: Base SaaS

- Auth
- Companies
- Users
- Multi-tenant con company_id
- Dashboard básico

### Fase 2: WhatsApp e inbox

- Webhook WhatsApp
- Enviar mensajes
- Guardar conversaciones
- Inbox
- Asignar humano

### Fase 3: IA comercial

- Clasificación de intención
- Prompts por empresa
- Tools controladas
- Handoff humano

### Fase 4: Catálogo, inventario y ventas

- Productos
- Inventario
- Órdenes
- Links de pago
- Webhook de pago
- Registro de venta

### Fase 5: Agenda

- Crear citas
- Consultar disponibilidad básica
- Notificar asesor
- Integración con Google Calendar vía n8n o nativa

### Fase 6: Integraciones

- Eventos internos
- Webhooks salientes
- n8n auxiliar
- Correos
- Resúmenes

### Fase 7: Escalamiento

- Telegram
- Instagram
- RAG
- Constructor visual
- Analytics avanzado
- CRM más robusto

---

## 19. Criterios de éxito del MVP

El MVP será exitoso si permite:

1. Crear una empresa tenant.
2. Conectar un número de WhatsApp.
3. Recibir mensajes reales.
4. Responder con IA.
5. Detectar intención de compra.
6. Consultar productos disponibles.
7. Crear orden.
8. Generar link de pago.
9. Confirmar pago por webhook.
10. Registrar venta.
11. Notificar a humano.
12. Agendar cita si no hay compra inmediata.
13. Ver todo en un panel.

---

## 20. Instrucciones para Codex

### Objetivo inicial

Crear la primera versión funcional del backend usando FastAPI, PostgreSQL, SQLAlchemy y Alembic.

### Prioridad de implementación

1. Estructura base del proyecto.
2. Configuración de entorno.
3. Conexión a PostgreSQL.
4. Modelos iniciales.
5. Migraciones Alembic.
6. Auth JWT.
7. Multi-tenancy con `company_id`.
8. CRUD de companies, users, products, inventory.
9. Módulo de conversations/messages.
10. Webhook base de WhatsApp.
11. Módulo de orders.
12. Módulo de appointments.
13. Módulo de events.
14. Servicio AI con tools simuladas.

### No implementar todavía

1. Builder visual.
2. Telegram.
3. Instagram.
4. RAG.
5. MCP.
6. CRM avanzado.
7. ERP.

### Convenciones

- Usar UUID como primary key.
- Usar timestamps `created_at` y `updated_at`.
- Usar `company_id` en todas las tablas de negocio.
- Usar servicios separados de rutas.
- Usar schemas Pydantic para request/response.
- No poner lógica de negocio dentro de los routers.
- No permitir consultas sin filtro tenant.
- Crear tests básicos para servicios críticos.

---

## 21. Variables de entorno sugeridas

```env
APP_NAME=AI_SALES_ASSISTANT
APP_ENV=development
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/ai_sales
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
OPENAI_API_KEY=
WHATSAPP_VERIFY_TOKEN=
ENCRYPTION_KEY=
N8N_WEBHOOK_URL=
```

---

## 22. Docker Compose inicial

```yaml
services:
  postgres:
    image: postgres:16
    container_name: ai_sales_postgres
    environment:
      POSTGRES_USER: ai_sales
      POSTGRES_PASSWORD: ai_sales_password
      POSTGRES_DB: ai_sales
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    container_name: ai_sales_redis
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

---

## 23. Decisión sobre MCP

No implementar MCP en el MVP.

Primero usar OpenAI tools/function calling conectadas directamente al backend.

MCP puede evaluarse después cuando el producto necesite conectarse a múltiples sistemas externos de manera más estándar.

---

## 24. Riesgos principales

### Riesgo 1: Alcance excesivo

Mitigación: WhatsApp primero. Omnicanal después.

### Riesgo 2: IA inventando información

Mitigación: tools controladas, prompts estrictos y backend como fuente de verdad.

### Riesgo 3: n8n como núcleo del SaaS

Mitigación: n8n solo para automatizaciones auxiliares.

### Riesgo 4: fuga de datos entre tenants

Mitigación: `company_id` obligatorio, tests de aislamiento y middleware tenant-aware.

### Riesgo 5: pagos mal confirmados

Mitigación: validar firma de webhooks, idempotencia y estados explícitos.

### Riesgo 6: stock inconsistente

Mitigación: transacciones SQL, reservas de inventario e idempotencia.

---

## 25. Nombre tentativo del producto

Opciones:

```text
VendeIA
FlowSeller AI
Swatek Flow
ComerciIA
VentaBot Pro
LeadFlow AI
```

Nombre recomendado provisional:

```text
Swatek Flow AI
```

---

## 26. Resumen ejecutivo

El producto será una plataforma SaaS multi-tenant para automatizar ventas conversacionales por WhatsApp mediante IA. La IA atenderá clientes, identificará intención de compra, consultará catálogo e inventario mediante tools controladas, generará links de pago, registrará ventas confirmadas por pasarela y permitirá agendar citas cuando el cliente no compre inmediatamente.

El backend en FastAPI será el núcleo del sistema y la fuente de verdad. n8n se usará únicamente para automatizaciones periféricas como correos, notificaciones, calendarios y sincronizaciones. Las operaciones críticas como pagos, inventario, órdenes, clientes y estados de conversación estarán controladas directamente por el backend.

---

## 27. Bitácora de implementación real (actualizado 2026-05-29)

Esta sección resume lo que ya quedó construido y operativo en el proyecto, incluyendo backend, frontend, despliegue, WhatsApp, IA y catálogo.

### 27.1 Estado general

- Proyecto operativo en producción bajo dominio:
  - `https://swaflow.swateck.com`
- Arquitectura separada en carpetas:
  - `backend/`
  - `frontend/`
- Plataforma multi-tenant activa (aislamiento por `company_id`).
- Base de datos MySQL conectada por túnel SSH (StackCP) en VPS.

### 27.2 Infraestructura y despliegue

- VPS con Docker Compose en:
  - `/docker/swaflow`
- Servicios principales:
  - `swaflow-backend`
  - `swaflow-frontend`
  - `stackcp-tunnel`
- Enrutamiento por Traefik con rutas API habilitadas para módulos críticos:
  - `/auth`, `/companies`, `/users`, `/contacts`, `/conversations`, `/products`, `/inventory`, `/orders`, `/payments`, `/appointments`, `/ai`, `/funnels`, `/integrations`, `/outbound-webhooks`, `/events`, `/realtime`, `/whatsapp`, `/webhooks`.
- Ajuste aplicado en producción para corregir error de enrutamiento de `/funnels`.

### 27.3 Seguridad y acceso

- Login con usuario/contraseña implementado.
- Contraseñas almacenadas con hash seguro (`bcrypt` vía `passlib`).
- Soporte de superusuario y gestión de usuarios por tenant.
- Gestión de sesión con JWT.
- Recomendación activa: usar siempre tokens permanentes para producción (Meta y OpenAI), nunca tokens temporales.

### 27.4 WhatsApp Cloud API

- Configuración de cuenta WhatsApp por tenant implementada.
- Webhook activo:
  - `https://swaflow.swateck.com/webhooks/whatsapp`
- Verificación de webhook con `verify_token` almacenado en la app.
- Recepción de mensajes entrantes y envío de salientes operativos.
- Correcciones aplicadas:
  - Manejo de duplicados de mensajes por `external_message_id`.
  - Persistencia de eventos/mensajes de interacción.
  - Corrección de errores de respuesta no JSON en rutas (`/outbound-webhooks`, `/funnels`).

### 27.5 Inbox y operación conversacional

- Inbox funcional con:
  - listado de conversaciones,
  - lectura de mensajes entrantes/salientes,
  - envío manual de mensajes.
- Mejoras aplicadas:
  - actualización en tiempo real,
  - pantalla de chat con área fija y scroll interno,
  - permanencia de contexto de navegación al refrescar (evitar salto a dashboard),
  - registro de acciones interactivas dentro del historial de mensajes.
- Ajuste de sesión:
  - se discutió ampliar inactividad a 30-60 min; quedó parametrizable.

### 27.6 Módulo IA (agentes por tenant)

- Configuración de agentes IA por tenant implementada.
- Flujo activo:
  1. Se toma `system_prompt` + reglas en base de datos.
  2. Se agrega contexto reciente de conversación.
  3. Se agrega contexto de catálogo/productos del tenant.
  4. Se genera respuesta con OpenAI.
- Integración de API key OpenAI por entorno productivo aplicada.
- Correcciones implementadas:
  - evitar eco/replicación de mensajes,
  - aplicar correctamente prompt del agente activo,
  - control de saludo inicial y reglas de conversación,
  - soporte para reinicio de contexto conversacional cuando aplique.

### 27.7 Plantillas interactivas para IA (botones/listas)

- Biblioteca de plantillas interactivas implementada en backend:
  - `GET /ai/interactive-templates`
  - `POST /ai/interactive-templates`
  - `PUT /ai/interactive-templates/{template_id}`
  - `DELETE /ai/interactive-templates/{template_id}`
- Runtime IA actualizado para devolver:
  - `reply_text`
  - `action` (clave de plantilla a disparar)
- Cuando hay `action`, el backend envía mensaje interactivo de WhatsApp (botones o lista) y guarda la acción en metadata del mensaje.
- Si no encuentra plantilla activa para la acción, hace fallback a texto normal.

### 27.8 Productos y catálogo Meta

- Sincronización de catálogo Meta implementada:
  - `POST /whatsapp/catalog/sync`
- Mapeo guardado en `products`:
  - nombre,
  - descripción,
  - precio,
  - moneda,
  - disponibilidad/estado,
  - `whatsapp_catalog_id`,
  - `whatsapp_product_retailer_id`.
- Se añadió validación para error común de Meta:
  - si se ingresa ID de conjunto (“All Products”) en vez de ID de catálogo, la API devuelve mensaje claro.
- Sincronización exitosa confirmada:
  - 11 leídos, 11 creados.

### 27.9 Corrección de parseo de precios Meta

- Problema detectado:
  - productos guardados en BD con `price = 1.00` pese a tener precio en catálogo.
- Causa:
  - parser anterior no interpretaba todos los formatos de precio de Meta y caía en fallback.
- Solución aplicada en `backend/app/whatsapp/service.py`:
  - parseo robusto para cadenas (`"250000 COP"`, `"COP 250000"`, `"250.000 COP"`),
  - soporte de precio tipo objeto con `amount` y `offset`,
  - reinicio/redeploy del backend en VPS completado.
- Acción operativa posterior:
  - ejecutar nuevamente `Sync catálogo` para actualizar precios reales en BD.

### 27.10 Módulo Funnels

- Módulo de embudos implementado (backend + frontend).
- Permite crear funnel y pasos por tenant.
- Integración con conversación para asignar funnel/paso.
- Error de carga por ruteo API corregido en Traefik.

### 27.11 Integraciones

- Módulo de integraciones habilitado para conectar:
  - calendario,
  - correo/notificaciones,
  - pasarelas,
  - webhooks salientes.
- Se mantiene la regla arquitectónica:
  - backend para lógica crítica,
  - n8n para automatización auxiliar.

### 27.12 Archivos y activos creados recientemente

- Importador local de productos desde Excel/fotos:
  - `backend/scripts/import_products_from_excel.py`
- Archivo CSV preparado para carga manual en Meta:
  - `productos/Carga_Meta_Productos.csv`
- Carpeta de contenidos de producto:
  - `productos/` (Excel + imágenes por nombre)

### 27.13 Estado actual de producción

- Backend reiniciado y saludable:
  - `GET /health` responde OK en producción.
- WhatsApp operativo en recepción y envío.
- IA responde automáticamente con agente activo.
- Sincronización de catálogo funcionando (con token y permisos correctos).

### 27.14 Pendientes inmediatos recomendados

1. Re-sincronizar catálogo para refrescar precios corregidos en BD.
2. Verificar en SQL que los 11 productos queden con precios correctos.
3. Consolidar UX final de IA interactiva (solo Sync catálogo + biblioteca de plantillas).
4. Afinar prompt operativo por tenant y reglas de transición en funnels.
5. Documentar runbook de producción (deploy, rollback, tokens, verificaciones post-restart).

### 27.15 FAQ externo + reglas de seguridad en BD (local, listo para desplegar)

- Se implementó en backend:
  - nuevo campo `ai_agents.security_rules` (texto independiente del `system_prompt`),
  - nueva tabla `ai_faq_entries` por tenant (`question`, `answer`, `active`),
  - límite de **máximo 10 FAQs por tenant**.
- Endpoints nuevos:
  - `GET /ai/faqs`
  - `POST /ai/faqs`
  - `PUT /ai/faqs/{faq_id}`
  - `DELETE /ai/faqs/{faq_id}`
  - `POST /ai/faqs/upload` (archivo externo).
- Carga de archivo FAQ soporta:
  - `.csv`, `.txt`, `.json`, `.xlsx`
  - columnas esperadas: `question/answer` o `pregunta/respuesta`.
- Runtime IA actualizado:
  - usa FAQs desde `ai_faq_entries` como contexto principal,
  - aplica `security_rules` desde `ai_agents`,
  - mantiene fallback legado para compatibilidad si faltan datos.
- Frontend IA actualizado:
  - bloque **Reglas de seguridad** (guardado en `ai_agents.security_rules`),
  - gestor de FAQ (crear, editar, eliminar, cargar archivo),
  - contador visible `N/10`.
- Validación local completada:
  - `backend`: compile OK + tests `5 passed`,
  - `frontend`: build OK.

> Nota operativa: cambios hechos localmente; no se desplegó al VPS en esta iteración.

### 27.16 Integración Wompi y persistencia de links de pago

- Se implementó el proveedor Wompi para generar links de pago desde órdenes:
  - `POST /v1/payment_links`
  - valor fijo en COP,
  - `single_use = true`,
  - vencimiento configurable con valor inicial de **120 minutos**,
  - URL de retorno configurable.
- Credenciales cifradas por tenant:
  - llave privada Wompi,
  - secreto de eventos Wompi,
  - soporte independiente para Sandbox y Producción.
- Webhook receptor:
  - `POST /webhooks/payments/wompi`
- Seguridad del webhook:
  - validación SHA256 con el secreto de eventos,
  - correlación de la orden por referencia o `payment_link_id`,
  - persistencia del ID de transacción recibido.
- Estados de orden:
  - link generado: `waiting_payment`,
  - pago confirmado: `paid`,
  - rechazo o error: `failed`,
  - vencimiento: `expired`.
- Notificación por correo tras aprobación:
  - cliente, si el contacto tiene correo,
  - usuarios activos con rol `owner` o `admin`,
  - usando la integración SMTP configurada para el tenant.
- Frontend:
  - el módulo **Órdenes** ahora consulta datos reales del backend,
  - muestra referencia, estado, vencimiento y link persistido,
  - permite generar, abrir y copiar el link de pago.
- Validación local completada:
  - `backend`: compile OK + tests `5 passed`,
  - `frontend`: build OK,
  - `git diff --check`: OK.
