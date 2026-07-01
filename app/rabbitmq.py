import json
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import BasicProperties

from app.config import get_settings
from app.service import (
    cambiar_estado_reserva,
    checkin_reserva,
    crear_cliente,
    crear_reserva,
    disponibilidad,
    eliminar_cliente,
    listar_clientes,
    listar_reservas,
    obtener_reserva,
    registrar_anticipo,
    reporte_reservas,
    actualizar_cliente,
    actualizar_reserva,
    ServiceError,
)

settings = get_settings()

ACTION_HANDLERS = {
    "cliente.list": lambda payload: listar_clientes(),
    "cliente.create": lambda payload: crear_cliente(payload),
    "cliente.update": lambda payload: actualizar_cliente(payload),
    "cliente.delete": lambda payload: eliminar_cliente(payload),
    "reserva.list": lambda payload: listar_reservas(payload),
    "reserva.create": lambda payload: crear_reserva(payload),
    "reserva.get": lambda payload: obtener_reserva(payload),
    "reserva.update": lambda payload: actualizar_reserva(payload),
    "reserva.anticipo": lambda payload: registrar_anticipo(payload),
    "reserva.change_status": lambda payload: cambiar_estado_reserva(payload),
    "reserva.checkin": lambda payload: checkin_reserva(payload),
    "reserva.availability": lambda payload: disponibilidad(payload),
    "report.reservas": lambda payload: reporte_reservas(payload),
}


def send_response(channel: BlockingChannel, properties: BasicProperties, response: Any) -> None:
    if not properties.reply_to:
        return
    channel.basic_publish(
        exchange="",
        routing_key=properties.reply_to,
        properties=pika.BasicProperties(correlation_id=properties.correlation_id),
        body=json.dumps(response, default=str).encode("utf-8"),
    )


def on_request(channel: BlockingChannel, method, properties: BasicProperties, body: bytes) -> None:
    try:
        message = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        result = {"success": False, "error": "Mensaje no es JSON válido"}
        send_response(channel, properties, result)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    action = message.get("action")
    payload = message.get("payload", {})
    if not action:
        result = {"success": False, "error": "Falta el campo action"}
        send_response(channel, properties, result)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    handler = ACTION_HANDLERS.get(action)
    if not handler:
        result = {"success": False, "error": f"Acción desconocida: {action}"}
        send_response(channel, properties, result)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        result = handler(payload)
        response = {"success": True, "result": result}
    except ServiceError as exc:
        response = {"success": False, "error": str(exc)}
    except Exception as exc:
        response = {"success": False, "error": str(exc)}

    send_response(channel, properties, response)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer() -> None:
    parameters = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=settings.rabbitmq_queue, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=settings.rabbitmq_queue, on_message_callback=on_request)
    print(f"[x] Esperando mensajes en cola '{settings.rabbitmq_queue}'. Presiona CTRL+C para detener.")
    try:
        channel.start_consuming()
    finally:
        if not connection.is_closed:
            connection.close()
