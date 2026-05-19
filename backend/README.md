# Swatek Flow AI Backend

Backend MVP para una plataforma SaaS multi-tenant de asistente comercial IA para WhatsApp.

La configuración actual usa MySQL por defecto mediante `mysql+pymysql`.

## Desarrollo local

```bash
cp .env.example .env
docker compose up -d
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

La API queda disponible en `http://localhost:8000`.

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

Si usas StackCP por SSH como en TablePlus, abre el tunel en otra terminal:

```bash
chmod +x scripts/stackcp_tunnel.sh
./scripts/stackcp_tunnel.sh
```

Y configura `DATABASE_URL` usando `127.0.0.1:3307`.
