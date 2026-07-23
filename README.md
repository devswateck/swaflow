# SwaFlow

Proyecto SaaS multi-tenant para asistente comercial IA por WhatsApp.

## Estructura

- `backend/`: API FastAPI, SQLAlchemy, Alembic, MySQL, auth JWT y servicios del MVP.
- `frontend/`: consola React/Vite para el panel administrativo e inbox comercial.
- `docs/`: politica operativa y referencias para agentes, incluyendo el uso de subagentes.
- `docs/adr/`: decisiones arquitectonicas formales del proyecto.
- `proyecto_saas_ia_comercial_multitenant.md`: documento base del desarrollo.

## Arranque rapido

Backend:

```bash
cd backend
docker compose up -d
export SWAFLOW_ENV_FILE=.env.development
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Configura `backend/.env.development` para desarrollo local. El backend carga ese archivo por defecto si existe; si quieres usar otro, define `SWAFLOW_ENV_FILE`.

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Producción:

- En producción el frontend y el backend corren en Docker en el VPS de la app.
- La base de datos vive fuera del VPS, en StackCP.
- El backend lee `DATABASE_URL` desde `/docker/swaflow/backend.env`.
- El frontend debe reconstruirse y publicar el bundle nuevo cuando cambie el código.
- `PUBLIC_BASE_URL` debe ser la URL pública real, por ejemplo `https://app.tudominio.com`.
- `CORS_ALLOW_ORIGINS` debe incluir el origen público del frontend si no comparten dominio.
- El frontend usa `/api/v1` como base y el nginx del contenedor proxya hacia `swaflow-backend:8000`.

Ejemplo de `backend.env` en el VPS:

```env
APP_NAME=Swatek Flow AI
APP_ENV=production
DATABASE_URL=mysql+pymysql://Admin-1585:TU_PASSWORD@sdb-j.hosting.stackcp.net:3306/SwaFlow-3139306da1?charset=utf8mb4
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=TU_SECRETO_LARGO
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
OPENAI_API_KEY=TU_OPENAI_API_KEY
WHATSAPP_VERIFY_TOKEN=TU_VERIFY_TOKEN
ENCRYPTION_KEY=TU_ENCRYPTION_KEY
N8N_WEBHOOK_URL=
PUBLIC_BASE_URL=https://app.tudominio.com
CORS_ALLOW_ORIGINS=https://app.tudominio.com
```

## Flujo De Trabajo

- Cada historia de usuario debe desarrollarse en una rama independiente.
- El nombre de la rama debe incluir el id de la historia, por ejemplo `1-8/...`, `1-9/...`, y no debe reutilizarse para otra historia.
