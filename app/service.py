from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models.anticipo import Anticipo, EstadoAnticipo
from app.models.cliente import Cliente
from app.models.estado_reserva import EstadoReserva
from app.models.historial_estado_reserva import HistorialEstadoReserva
from app.models.reserva import Reserva
from app.schemas.anticipo import AnticipoCreate, AnticipoOut
from app.schemas.cliente import ClienteCreate, ClienteOut, ClienteUpdate
from app.schemas.reporte import ReporteReservaItem, ReporteReservas
from app.schemas.reserva import ReservaCreate, ReservaOut, ReservaUpdate

settings = get_settings()


class ServiceError(Exception):
    pass


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


def to_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: to_json(item) for key, item in value.items()}
    return value


def obtener_estado(db: Session, nombre: str) -> EstadoReserva:
    estado = db.query(EstadoReserva).filter(EstadoReserva.nombre == nombre).first()
    if not estado:
        raise ServiceError(f"Estado '{nombre}' no está configurado")
    return estado


def validar_disponibilidad_administracion(sucursal_id: int, fecha: datetime, hora: datetime, personas: int) -> Any:
    url = f"{settings.administracion_url}/mesas-disponibles"
    params = {
        "sucursal_id": sucursal_id,
        "fecha": fecha.date().isoformat(),
        "hora": hora.time().isoformat(),
        "personas": personas,
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            respuesta = client.get(url, params=params)
            respuesta.raise_for_status()
            return respuesta.json()
    except httpx.RequestError as exc:
        raise ServiceError("Administración no disponible") from exc
    except httpx.HTTPStatusError as exc:
        raise ServiceError("Error al consultar Administración") from exc


def extraer_mesa_disponible(respuesta: Any, mesa_id: int | None = None) -> int | None:
    if isinstance(respuesta, bool):
        return mesa_id if respuesta else None

    if isinstance(respuesta, dict):
        if mesa_id is not None:
            if respuesta.get("mesa_id") == mesa_id:
                return mesa_id
            mesas = respuesta.get("mesas")
            if isinstance(mesas, list) and any(isinstance(m, dict) and m.get("id") == mesa_id for m in mesas):
                return mesa_id
            return None

        if "mesa_id" in respuesta and isinstance(respuesta["mesa_id"], int):
            return respuesta["mesa_id"]
        mesas = respuesta.get("mesas")
        if isinstance(mesas, list) and mesas:
            for mesa in mesas:
                if isinstance(mesa, dict) and "id" in mesa:
                    return mesa["id"]

    if isinstance(respuesta, list) and respuesta:
        if mesa_id is not None:
            for mesa in respuesta:
                if isinstance(mesa, dict) and mesa.get("id") == mesa_id:
                    return mesa_id
        first = respuesta[0]
        if isinstance(first, dict) and "id" in first:
            return first["id"]

    return mesa_id


def validar_solapamiento(db: Session, mesa_id: int, inicio: datetime, fin: datetime, reserva_id: int | None = None) -> bool:
    query = db.query(Reserva).filter(
        Reserva.mesa_id == mesa_id,
        Reserva.hora_inicio < fin,
        Reserva.hora_fin > inicio,
        Reserva.estado_id.in_(
            db.query(EstadoReserva.id).filter(EstadoReserva.nombre.in_(["Pendiente", "Confirmada", "Check-In"]))
        ),
    )
    if reserva_id is not None:
        query = query.filter(Reserva.id != reserva_id)
    return query.first() is not None


def validar_cliente_existe(db: Session, cliente_id: int) -> None:
    if not db.get(Cliente, cliente_id):
        raise ServiceError("Cliente no encontrado")


def validar_rango_horario(hora_inicio: datetime, hora_fin: datetime) -> None:
    if hora_fin <= hora_inicio:
        raise ServiceError("La hora de fin debe ser posterior a la hora de inicio")


def listar_clientes() -> List[Dict[str, Any]]:
    with db_session() as db:
        clientes = db.query(Cliente).all()
        return [ClienteOut.model_validate(cliente).model_dump(mode="json") for cliente in clientes]


def crear_cliente(payload: Dict[str, Any]) -> Dict[str, Any]:
    cliente_in = ClienteCreate.model_validate(payload)
    with db_session() as db:
        existente = db.query(Cliente).filter(Cliente.identificacion == cliente_in.identificacion).first()
        if existente:
            raise ServiceError("Cliente ya existe")
        nuevo = Cliente(**cliente_in.model_dump())
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return ClienteOut.model_validate(nuevo).model_dump(mode="json")


def actualizar_cliente(payload: Dict[str, Any]) -> Dict[str, Any]:
    cliente_id = int(payload.get("cliente_id"))
    datos = payload.get("data", {})
    cliente_update = ClienteUpdate.model_validate(datos)
    with db_session() as db:
        registro = db.get(Cliente, cliente_id)
        if not registro:
            raise ServiceError("Cliente no encontrado")
        cambios = cliente_update.model_dump(exclude_none=True)
        for field, value in cambios.items():
            setattr(registro, field, value)
        db.commit()
        db.refresh(registro)
        return ClienteOut.model_validate(registro).model_dump(mode="json")


def eliminar_cliente(payload: Dict[str, Any]) -> Dict[str, Any]:
    cliente_id = int(payload.get("cliente_id"))
    with db_session() as db:
        registro = db.get(Cliente, cliente_id)
        if not registro:
            raise ServiceError("Cliente no encontrado")
        db.delete(registro)
        db.commit()
        return {"cliente_id": cliente_id, "deleted": True}


def listar_reservas(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    with db_session() as db:
        query = db.query(Reserva)
        if payload.get("cliente_id") is not None:
            query = query.filter(Reserva.cliente_id == int(payload["cliente_id"]))
        if payload.get("sucursal_id") is not None:
            query = query.filter(Reserva.sucursal_id == int(payload["sucursal_id"]))
        if payload.get("estado_id") is not None:
            query = query.filter(Reserva.estado_id == int(payload["estado_id"]))
        reservas = query.order_by(Reserva.fecha, Reserva.hora_inicio).all()
        return [ReservaOut.model_validate(reserva).model_dump(mode="json") for reserva in reservas]


def crear_reserva(payload: Dict[str, Any]) -> Dict[str, Any]:
    reserva_in = ReservaCreate.model_validate(payload)
    with db_session() as db:
        validar_cliente_existe(db, reserva_in.cliente_id)
        validar_rango_horario(reserva_in.hora_inicio, reserva_in.hora_fin)
        disponibilidad = validar_disponibilidad_administracion(
            reserva_in.sucursal_id,
            reserva_in.fecha,
            reserva_in.hora_inicio,
            reserva_in.numero_personas,
        )
        mesa_id = extraer_mesa_disponible(disponibilidad, reserva_in.mesa_id)
        if mesa_id is None:
            raise ServiceError("No hay mesas disponibles")
        if validar_solapamiento(db, mesa_id, reserva_in.hora_inicio, reserva_in.hora_fin):
            raise ServiceError("La mesa ya tiene una reserva en ese horario")
        estado = obtener_estado(db, "Pendiente")
        nueva = Reserva(**reserva_in.model_dump(exclude_none=True), mesa_id=mesa_id, estado_id=estado.id)
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        return ReservaOut.model_validate(nueva).model_dump(mode="json")


def obtener_reserva(payload: Dict[str, Any]) -> Dict[str, Any]:
    reserva_id = int(payload.get("reserva_id"))
    with db_session() as db:
        reserva = db.get(Reserva, reserva_id)
        if not reserva:
            raise ServiceError("Reserva no encontrada")
        return ReservaOut.model_validate(reserva).model_dump(mode="json")


def actualizar_reserva(payload: Dict[str, Any]) -> Dict[str, Any]:
    reserva_id = int(payload.get("reserva_id"))
    update_data = payload.get("data", {})
    reserva_update = ReservaUpdate.model_validate(update_data)
    with db_session() as db:
        registro = db.get(Reserva, reserva_id)
        if not registro:
            raise ServiceError("Reserva no encontrada")
        estado_actual = db.get(EstadoReserva, registro.estado_id)
        if estado_actual.nombre not in ["Pendiente", "Confirmada"]:
            raise ServiceError("Solo reservas Pendiente o Confirmada pueden modificarse")
        datos = reserva_update.model_dump(exclude_none=True)
        if "estado_id" in datos:
            raise ServiceError("Use reserva.change_status para cambiar el estado")
        if "cliente_id" in datos:
            validar_cliente_existe(db, datos["cliente_id"])
        nuevo_fecha = datos.get("fecha", registro.fecha)
        nuevo_inicio = datos.get("hora_inicio", registro.hora_inicio)
        nuevo_fin = datos.get("hora_fin", registro.hora_fin)
        nuevo_numero_personas = datos.get("numero_personas", registro.numero_personas)
        nuevo_mesa_id = datos.get("mesa_id", registro.mesa_id)
        if any(field in datos for field in ["fecha", "hora_inicio", "hora_fin"]):
            validar_rango_horario(nuevo_inicio, nuevo_fin)
        disponibilidad = validar_disponibilidad_administracion(
            registro.sucursal_id,
            nuevo_fecha,
            nuevo_inicio,
            nuevo_numero_personas,
        )
        mesa_id_valida = extraer_mesa_disponible(disponibilidad, nuevo_mesa_id)
        if mesa_id_valida is None or ("mesa_id" in datos and mesa_id_valida != nuevo_mesa_id):
            raise ServiceError("La mesa solicitada no está disponible para el horario indicado")
        if validar_solapamiento(db, mesa_id_valida, nuevo_inicio, nuevo_fin, reserva_id=registro.id):
            raise ServiceError("La mesa ya tiene una reserva en ese horario")
        for campo, valor in datos.items():
            if campo == "mesa_id":
                setattr(registro, campo, mesa_id_valida)
            else:
                setattr(registro, campo, valor)
        db.commit()
        db.refresh(registro)
        return ReservaOut.model_validate(registro).model_dump(mode="json")


def registrar_anticipo(payload: Dict[str, Any]) -> Dict[str, Any]:
    reserva_id = int(payload.get("reserva_id"))
    anticipo_in = AnticipoCreate.model_validate(payload.get("anticipo", {}))
    with db_session() as db:
        reserva = db.get(Reserva, reserva_id)
        if not reserva:
            raise ServiceError("Reserva no encontrada")
        if reserva.estado_id != obtener_estado(db, "Pendiente").id:
            raise ServiceError("Anticipo solo para reservas pendientes")
        pago = Anticipo(
            reserva_id=reserva_id,
            monto=anticipo_in.monto,
            metodo_pago=anticipo_in.metodo_pago,
            estado=EstadoAnticipo.PAGADO,
        )
        db.add(pago)
        reserva.estado_id = obtener_estado(db, "Confirmada").id
        reserva.fecha_confirmacion = datetime.utcnow()
        db.commit()
        db.refresh(pago)
        return AnticipoOut.model_validate(pago).model_dump(mode="json")


def cambiar_estado_reserva(payload: Dict[str, Any]) -> Dict[str, Any]:
    reserva_id = int(payload.get("reserva_id"))
    estado_id = int(payload.get("estado_id"))
    usuario_id = payload.get("usuario_id")
    with db_session() as db:
        reserva = db.get(Reserva, reserva_id)
        if not reserva:
            raise ServiceError("Reserva no encontrada")
        estado_actual = db.get(EstadoReserva, reserva.estado_id)
        nuevo_estado = db.get(EstadoReserva, estado_id)
        if not nuevo_estado:
            raise ServiceError("Estado destino inválido")
        if nuevo_estado.nombre not in {
            "Pendiente": ["Confirmada", "Cancelada"],
            "Confirmada": ["Check-In", "Cancelada", "No-Show"],
            "Check-In": ["Finalizada"],
            "Finalizada": [],
            "Cancelada": [],
            "No-Show": [],
        }.get(estado_actual.nombre, []):
            raise ServiceError("Transición de estado no permitida")
        historial = HistorialEstadoReserva(
            reserva_id=reserva.id,
            estado_anterior=estado_actual.nombre,
            estado_nuevo=nuevo_estado.nombre,
            usuario_id=usuario_id,
        )
        reserva.estado_id = nuevo_estado.id
        if nuevo_estado.nombre == "Confirmada":
            reserva.fecha_confirmacion = datetime.utcnow()
        db.add(historial)
        db.commit()
        db.refresh(reserva)
        return {"mensaje": "Estado actualizado", "estado": nuevo_estado.nombre}


def checkin_reserva(payload: Dict[str, Any]) -> Dict[str, Any]:
    reserva_id = int(payload.get("reserva_id"))
    with db_session() as db:
        reserva = db.get(Reserva, reserva_id)
        if not reserva:
            raise ServiceError("Reserva no encontrada")
        estado_actual = db.get(EstadoReserva, reserva.estado_id)
        if estado_actual.nombre != "Confirmada":
            raise ServiceError("Solo reservas confirmadas pueden hacer check-in")
        nuevo_estado = obtener_estado(db, "Check-In")
        historial = HistorialEstadoReserva(
            reserva_id=reserva.id,
            estado_anterior=estado_actual.nombre,
            estado_nuevo=nuevo_estado.nombre,
            usuario_id=None,
        )
        reserva.estado_id = nuevo_estado.id
        db.add(historial)
        db.commit()
        db.refresh(reserva)
        return {"mensaje": "Check-in registrado", "estado": nuevo_estado.nombre}


def disponibilidad(payload: Dict[str, Any]) -> Dict[str, Any]:
    sucursal_id = int(payload.get("sucursal_id"))
    fecha = payload.get("fecha")
    hora = payload.get("hora")
    numero_personas = int(payload.get("numero_personas"))
    if not fecha or not hora:
        raise ServiceError("Fecha y hora son requeridas")
    if isinstance(fecha, str):
        fecha = datetime.fromisoformat(fecha)
    if isinstance(hora, str):
        hora = datetime.fromisoformat(hora)
    disponible = validar_disponibilidad_administracion(sucursal_id, fecha, hora, numero_personas)
    return {"disponible": bool(disponible), "detalle": disponible}


def reporte_reservas(payload: Dict[str, Any]) -> Dict[str, Any]:
    with db_session() as db:
        estados = {estado.id: estado.nombre for estado in db.query(EstadoReserva).all()}
        reservas = db.query(Reserva).all()
        items = [
            ReporteReservaItem(
                reserva_id=r.id,
                cliente_id=r.cliente_id,
                sucursal_id=r.sucursal_id,
                mesa_id=r.mesa_id,
                estado_actual=estados.get(r.estado_id, "Desconocido"),
                fecha=r.fecha.isoformat(),
                hora_inicio=r.hora_inicio.isoformat(),
                hora_fin=r.hora_fin.isoformat(),
            )
            for r in reservas
        ]
        reporte = ReporteReservas(total_reservas=len(items), reservas=items)
        return reporte.model_dump(mode="json")
