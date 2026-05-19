from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.routes import router as ai_router
from app.appointments.routes import router as appointments_router
from app.auth.routes import router as auth_router
from app.companies.routes import router as companies_router
from app.contacts.routes import router as contacts_router
from app.conversations.routes import router as conversations_router
from app.core.config import get_settings
from app.events.routes import router as events_router
from app.integrations.routes import router as integrations_router
from app.inventory.routes import router as inventory_router
from app.orders.routes import router as orders_router
from app.payments.routes import router as payments_router
from app.products.routes import router as products_router
from app.users.routes import router as users_router
from app.whatsapp.routes import router as whatsapp_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(users_router)
app.include_router(contacts_router)
app.include_router(whatsapp_router)
app.include_router(conversations_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(appointments_router)
app.include_router(ai_router)
app.include_router(integrations_router)
app.include_router(events_router)

