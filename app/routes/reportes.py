from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.estado_reserva import EstadoReserva
from app.models.reserva import Reserva
from app.schemas.reporte import ReporteReservas, ReporteReservaItem

router = APIRouter()


@router.get("/reservas", response_model=ReporteReservas)
def reporte_reservas(db: Session = Depends(get_db)):
    estados = {estado.id: estado.nombre for estado in db.query(EstadoReserva).all()}
    reservas = db.query(Reserva).all()
    items = [ReporteReservaItem(
        reserva_id=r.id,
        cliente_id=r.cliente_id,
        sucursal_id=r.sucursal_id,
        mesa_id=r.mesa_id,
        estado_actual=estados.get(r.estado_id, "Desconocido"),
        fecha=r.fecha.isoformat(),
        hora_inicio=r.hora_inicio.isoformat(),
        hora_fin=r.hora_fin.isoformat(),
    ) for r in reservas]

    return ReporteReservas(total_reservas=len(items), reservas=items)
