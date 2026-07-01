# Microservicio de Reservas

Servicio responsable de gestionar clientes, reservas, anticipos y estados de reserva.

## Qué incluye

- Backend con FastAPI
- Base de datos PostgreSQL
- Endpoints para clientes, reservas, anticipos y reportes
- Scheduler para no-show
- Documentación automática en Swagger

## Archivos importantes

- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `.env`
- `.dockerignore`
- `app/`

## Endpoints

- `GET /` → estado del servicio
- `GET /docs` → documentación Swagger UI
- `GET /clientes/`
- `POST /clientes/`
- `PUT /clientes/{id}`
- `DELETE /clientes/{id}`
- `GET /reservas/`
- `GET /reservas/{id}`
- `POST /reservas/`
- `PATCH /reservas/{id}`
- `POST /reservas/{id}/anticipo`
- `PATCH /reservas/{id}/estado`
- `PATCH /reservas/{id}/checkin`
- `GET /reservas/disponibilidad`
- `GET /reportes/reservas`

## Dependencias

Python 3.12 y estas versiones exactas:

- `fastapi==0.115.0`
- `uvicorn[standard]==0.24.0`
- `sqlalchemy==2.0.35`
- `psycopg[binary]==3.1.20`
- `pydantic==2.8.0`
- `pydantic-settings==2.8.0`
- `email-validator==2.0.0`
- `httpx==0.27.0`
- `python-jose==3.3.0`
- `alembic==1.12.0`
- `apscheduler==3.11.0`

## Configuración

Crea un archivo `.env` con estas variables:

```env
DATABASE_URL=postgresql+psycopg://reservas_user:reservas_pass@reservas_db:5432/reservasdb
ADMINISTRACION_URL=http://administracion:8001
JWT_PUBLIC_KEY=
JWT_ALGORITHM=RS256
JWT_AUDIENCE=reservas-service
JWT_ISSUER=security-service
```

> `DATABASE_URL` debe usar el host del contenedor de Postgres dentro de Docker.

## Cómo ejecutar (simple)

```powershell
docker --context desktop-linux compose up -d --build
```

## Cómo verificar

- `docker --context desktop-linux compose ps`
- `docker --context desktop-linux compose logs --no-color --tail=80`
- `http://localhost:8002/`
- `http://localhost:8002/docs`

## Qué verás

- `GET /` devuelve el estado del servicio.
- `GET /docs` muestra Swagger.
- `GET /clientes/` y `GET /reservas/` pueden devolver `[]` si no hay datos.
- `GET /reportes/reservas` devuelve `total_reservas:0` si no hay reservas.

## Información extra

- No necesitas un script de arranque adicional.
- Usa solo los comandos de Docker Compose arriba.
- Este repositorio es backend; no incluye frontend.
- Si `JWT_PUBLIC_KEY` no está configurado, el servicio no validará JWT.
- Si `ADMINISTRACION_URL` no está disponible, las llamadas de disponibilidad pueden fallar.

## Limpieza del proyecto

- Eliminé `.venv` del repositorio.
- Añadí `.dockerignore` para no copiar archivos locales en la imagen.
