# Swatek Flow AI Backend

Backend MVP para una plataforma SaaS multi-tenant de asistente comercial IA para WhatsApp.

La configuración actual usa MySQL por defecto mediante `mysql+pymysql`.

## Desarrollo local

```bash
docker compose up -d
export SWAFLOW_ENV_FILE=.env.development
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

La API queda disponible en `http://localhost:8000`.
Usa `backend/.env.development` para desarrollo local. El archivo `backend/.env` queda reservado para otro perfil si lo necesitas.

## Primer tenant

1. Crear empresa y owner con `POST /companies`.
2. Autenticarse con `POST /auth/login`.
3. Usar el token Bearer para operar usuarios, productos, inventario, conversaciones, órdenes y citas.

Todas las consultas de datos de negocio se filtran por `company_id` desde el usuario autenticado.

## MySQL remoto

Cuando la base esté creada en el servidor, define:

```env
DATABASE_URL=mysql+pymysql://usuario:password@host:3306/nombre_db?charset=utf8mb4
```

Luego ejecuta `alembic upgrade head` desde `backend/`.

Si quieres apuntar a otro archivo de entorno, exporta `SWAFLOW_ENV_FILE` antes de arrancar Alembic o Uvicorn.

En producción real, el backend corre en Docker en el VPS de la app y usa la
base MySQL externa de StackCP directamente.

Usa esta base de `backend.env`:

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

Arranque recomendado:

1. Construye la imagen del frontend y del backend.
2. Arranca el stack Docker del VPS de la app.
3. Ejecuta `alembic upgrade head`.
4. Verifica `https://swaflow.swateck.com`.
