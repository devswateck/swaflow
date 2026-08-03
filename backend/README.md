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
Por defecto, el backend ya no carga `backend/.env` de forma automática; el arranque normal usa solo el perfil local.

## Primer tenant

1. Crear empresa y owner con `POST /companies`.
2. Autenticarse con `POST /auth/login`.
3. Usar el token Bearer para operar usuarios, productos, inventario, conversaciones, órdenes y citas.

Todas las consultas de datos de negocio se filtran por `company_id` desde el usuario autenticado.

## MySQL local

Si cambias el perfil local, define el `DATABASE_URL` correspondiente en `backend/.env.development` y vuelve a ejecutar:

```bash
alembic upgrade head
```

Si quieres usar otro archivo de entorno, exporta `SWAFLOW_ENV_FILE` antes de arrancar Alembic o Uvicorn.
