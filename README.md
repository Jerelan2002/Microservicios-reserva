# Microservicio de Reservas por Mensajería

Este proyecto ya no expone una API HTTP.
Es un microservicio de mensajería que recibe mensajes desde RabbitMQ y procesa reservas, clientes, anticipos y estados.

## Qué es ahora

- Servicio independiente orientado a mensajes
- No hay endpoints REST
- No hay Swagger ni `/docs`
- Comunicación por cola RabbitMQ
- Base de datos PostgreSQL
- Scheduler de no-show en segundo plano

## Cómo funciona

El servicio escucha en la cola configurada por `RABBITMQ_QUEUE`.
Cada mensaje debe ser JSON con los campos:

- `action`: nombre de la operación
- `payload`: datos de entrada

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

### Ejemplo de mensaje sencillo

```json
{
  "action": "cliente.list",
  "payload": {}
}
```

### Ejemplo de crear cliente

```json
{
  "action": "cliente.create",
  "payload": {
    "nombre": "Juan",
    "apellido": "Pérez",
    "identificacion": "12345678",
    "telefono": "123456789",
    "email": "juan@example.com"
  }
}
```

### Ejemplo de crear reserva

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

Python 3.12 o superior y estas versiones:

- `sqlalchemy==2.0.35`
- `psycopg[binary]==3.3.4`
- `pydantic==2.13.4`
- `pydantic-settings==2.13.0`
- `email-validator==2.3.0`
- `httpx==0.27.0`
- `pika==1.4.1`
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

## Cómo probarlo desde Docker Desktop

1. Abre Docker Desktop.
2. Asegúrate de que los contenedores `reservas_service`, `reservas_rabbitmq` y `reservas_db` están en marcha.
3. Abre RabbitMQ management en `http://localhost:15672`.
4. Inicia sesión con `guest` / `guest`.
5. Ve a `Queues` y selecciona `reservas_queue`.
6. En `Publish message`, pega uno de los mensajes JSON de ejemplo.
7. Pulsa `Publish message`.

## Verificar que funciona

- La cola `reservas_queue` debe procesar el mensaje y quedar en `0 messages`.
- Revisa los logs del contenedor `reservas_service` en Docker Desktop.
- Si el servicio muestra `Esperando mensajes en cola 'reservas_queue'`, está listo.

## Notas

- El servicio crea tablas y estados iniciales al iniciar.
- Si RabbitMQ no está disponible, el servicio no procesará mensajes.
- No esperes rutas HTTP ni documentación Swagger.
