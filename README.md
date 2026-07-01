# Microservicio de Reservas por Mensajería

Este proyecto ahora es un microservicio de reservas sin API HTTP directa.
La comunicación se realiza a través de mensajes en RabbitMQ.

## Qué incluye

- Servicio de reservas independiente
- Base de datos PostgreSQL
- Consumo de comandos desde RabbitMQ
- Scheduler de no-show
- Lógica de clientes, reservas, anticipos y estados

## Archivos clave

- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- `.env`
- `app/main.py`
- `app/rabbitmq.py`
- `app/service.py`

## Protocolo de mensajes

El microservicio escucha en la cola configurada por `RABBITMQ_QUEUE`.
Cada mensaje debe ser JSON con estos campos:

- `action`: string que indica la operación
- `payload`: objeto con los datos de la operación

### Acciones soportadas

- `cliente.list`
- `cliente.create`
- `cliente.update`
- `cliente.delete`
- `reserva.list`
- `reserva.create`
- `reserva.get`
- `reserva.update`
- `reserva.anticipo`
- `reserva.change_status`
- `reserva.checkin`
- `reserva.availability`
- `report.reservas`

### Ejemplo de mensaje

```json
{
  "action": "reserva.create",
  "payload": {
    "cliente_id": 1,
    "restaurante_id": 1,
    "sucursal_id": 1,
    "fecha": "2026-07-01T19:00:00Z",
    "hora_inicio": "2026-07-01T19:00:00Z",
    "hora_fin": "2026-07-01T21:00:00Z",
    "numero_personas": 4,
    "mesa_id": null
  }
}
```

## Dependencias

Python 3.12 y estas versiones exactas:

- `sqlalchemy==2.0.35`
- `psycopg[binary]==3.1.20`
- `pydantic==2.8.0`
- `pydantic-settings==2.8.0`
- `httpx==0.27.0`
- `pika==1.7.2`
- `alembic==1.12.0`
- `apscheduler==3.11.0`

## Configuración

Crea un archivo `.env` con estas variables:

```env
DATABASE_URL=postgresql+psycopg://reservas_user:reservas_pass@reservas_db:5432/reservasdb
ADMINISTRACION_URL=http://administracion:8001
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
RABBITMQ_QUEUE=reservas_queue
```

> `DATABASE_URL` debe usar el host del contenedor de Postgres dentro de Docker.

## Cómo ejecutar

```powershell
docker compose up -d --build
```

## Cómo verificar

- `docker compose ps`
- `docker compose logs --no-color --tail=80`
- RabbitMQ management: `http://localhost:15672`

## Notas

- El servicio crea tablas en la base de datos y semillas de estados al iniciar.
- El scheduler de no-show se ejecuta en segundo plano.
- Si RabbitMQ no está disponible, el servicio no podrá procesar mensajes.
