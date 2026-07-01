from datetime import datetime
from typing import Any, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models.anticipo import Anticipo, EstadoAnticipo
from app.models.cliente import Cliente
from app.models.estado_reserva import EstadoReserva
from app.models.historial_estado_reserva import HistorialEstadoReserva
from app.models.reserva import Reserva
from app.schemas.anticipo import AnticipoCreate, AnticipoOut
from app.schemas.reserva import ReservaCreate, ReservaOut, ReservaUpdate

router = APIRouter()
settings = get_settings()

TRANSICIONES_VALIDAS = {
    "Pendiente": ["Confirmada", "Cancelada"],
    "Confirmada": ["Check-In", "Cancelada", "No-Show"],
    "Check-In": ["Finalizada"],
    "Finalizada": [],
    "Cancelada": [],
    "No-Show": [],
}


def obtener_estado(db: Session, nombre: str) -> EstadoReserva:
    estado = db.query(EstadoReserva).filter(EstadoReserva.nombre == nombre).first()
    if not estado:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Estado '{nombre}' no está configurado")
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
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Administración no disponible")
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error al consultar Administración")


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")


def validar_rango_horario(hora_inicio: datetime, hora_fin: datetime) -> None:
    if hora_fin <= hora_inicio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La hora de fin debe ser posterior a la hora de inicio")


@router.get("/", response_model=List[ReservaOut])
def listar_reservas(
    cliente_id: int | None = None,
    sucursal_id: int | None = None,
    estado_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Reserva)
    if cliente_id is not None:
        query = query.filter(Reserva.cliente_id == cliente_id)
    if sucursal_id is not None:
        query = query.filter(Reserva.sucursal_id == sucursal_id)
    if estado_id is not None:
        query = query.filter(Reserva.estado_id == estado_id)
    return query.order_by(Reserva.fecha, Reserva.hora_inicio).all()


@router.post("/", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def crear_reserva(reserva: ReservaCreate, db: Session = Depends(get_db)):
    validar_cliente_existe(db, reserva.cliente_id)
    validar_rango_horario(reserva.hora_inicio, reserva.hora_fin)

    disponibilidad = validar_disponibilidad_administracion(reserva.sucursal_id, reserva.fecha, reserva.hora_inicio, reserva.numero_personas)
    mesa_id = extraer_mesa_disponible(disponibilidad, reserva.mesa_id)
    if mesa_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No hay mesas disponibles")

    if validar_solapamiento(db, mesa_id, reserva.hora_inicio, reserva.hora_fin):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La mesa ya tiene una reserva en ese horario")

    estado = obtener_estado(db, "Pendiente")
    nueva = Reserva(**reserva.dict(exclude={"mesa_id"}), mesa_id=mesa_id, estado_id=estado.id)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.get("/{reserva_id}", response_model=ReservaOut)
def obtener_reserva(reserva_id: int, db: Session = Depends(get_db)):
    reserva = db.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    return reserva


@router.patch("/{reserva_id}", response_model=ReservaOut)
def actualizar_reserva(reserva_id: int, reserva: ReservaUpdate, db: Session = Depends(get_db)):
    registro = db.get(Reserva, reserva_id)
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")

    estado_actual = db.get(EstadoReserva, registro.estado_id)
    if estado_actual.nombre not in ["Pendiente", "Confirmada"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo reservas Pendiente o Confirmada pueden modificarse")

    datos = reserva.dict(exclude_unset=True)
    if "estado_id" in datos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use /reservas/{id}/estado para cambiar el estado")

    if "cliente_id" in datos:
        validar_cliente_existe(db, datos["cliente_id"])

    nuevo_fecha = datos.get("fecha", registro.fecha)
    nuevo_inicio = datos.get("hora_inicio", registro.hora_inicio)
    nuevo_fin = datos.get("hora_fin", registro.hora_fin)
    nuevo_numero_personas = datos.get("numero_personas", registro.numero_personas)
    nuevo_mesa_id = datos.get("mesa_id", registro.mesa_id)

    if any(key in datos for key in ["fecha", "hora_inicio", "hora_fin"]):
        validar_rango_horario(nuevo_inicio, nuevo_fin)

    disponibilidad = validar_disponibilidad_administracion(registro.sucursal_id, nuevo_fecha, nuevo_inicio, nuevo_numero_personas)
    mesa_id_valida = extraer_mesa_disponible(disponibilidad, nuevo_mesa_id)
    if mesa_id_valida is None or ("mesa_id" in datos and mesa_id_valida != nuevo_mesa_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La mesa solicitada no está disponible para el horario indicado")

    if validar_solapamiento(db, mesa_id_valida, nuevo_inicio, nuevo_fin, reserva_id=registro.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La mesa ya tiene una reserva en ese horario")

    for campo, valor in datos.items():
        if campo == "mesa_id":
            setattr(registro, campo, mesa_id_valida)
        else:
            setattr(registro, campo, valor)

    db.commit()
    db.refresh(registro)
    return registro


@router.post("/{reserva_id}/anticipo", response_model=AnticipoOut, status_code=status.HTTP_201_CREATED)
def registrar_anticipo(reserva_id: int, anticipo: AnticipoCreate, db: Session = Depends(get_db)):
    reserva = db.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    if reserva.estado_id != obtener_estado(db, "Pendiente").id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anticipo solo para reservas pendientes")

    pago = Anticipo(reserva_id=reserva_id, monto=anticipo.monto, metodo_pago=anticipo.metodo_pago, estado=EstadoAnticipo.PAGADO)
    db.add(pago)
    reserva.estado_id = obtener_estado(db, "Confirmada").id
    reserva.fecha_confirmacion = datetime.utcnow()
    db.commit()
    db.refresh(pago)
    return pago


@router.patch("/{reserva_id}/estado")
def cambiar_estado(reserva_id: int, estado_id: int, usuario_id: int | None = None, db: Session = Depends(get_db)):
    reserva = db.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    estado_actual = db.get(EstadoReserva, reserva.estado_id)
    nuevo_estado = db.get(EstadoReserva, estado_id)
    if not nuevo_estado:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado destino inválido")
    if nuevo_estado.nombre not in TRANSICIONES_VALIDAS.get(estado_actual.nombre, []):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transición de estado no permitida")

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


@router.patch("/{reserva_id}/checkin")
def checkin_reserva(reserva_id: int, db: Session = Depends(get_db)):
    reserva = db.get(Reserva, reserva_id)
    if not reserva:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    estado_actual = db.get(EstadoReserva, reserva.estado_id)
    if estado_actual.nombre != "Confirmada":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo reservas confirmadas pueden hacer check-in")

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


@router.get("/disponibilidad")
def disponibilidad(sucursal_id: int, fecha: datetime, hora: datetime, numero_personas: int):
    disponible = validar_disponibilidad_administracion(sucursal_id, fecha, hora, numero_personas)
    return {"disponible": bool(disponible), "detalle": disponible}
