# SwaFlow

Proyecto SaaS multi-tenant para asistente comercial IA por WhatsApp.

## Estructura

- `backend/`: API FastAPI, SQLAlchemy, Alembic, MySQL, auth JWT y servicios del MVP.
- `frontend/`: consola React/Vite para el panel administrativo e inbox comercial.
- `proyecto_saas_ia_comercial_multitenant.md`: documento base del desarrollo.

## Arranque rapido

Backend:

```bash
cd backend
cp .env.example .env
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```
