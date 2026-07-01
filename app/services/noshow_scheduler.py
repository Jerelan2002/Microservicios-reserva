from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.estado_reserva import EstadoReserva
from app.models.historial_estado_reserva import HistorialEstadoReserva
from app.models.reserva import Reserva


scheduler: Optional[BackgroundScheduler] = None


def revisar_no_shows() -> None:
    db: Session = SessionLocal()
    try:
        confirmado = db.query(EstadoReserva).filter(EstadoReserva.nombre == "Confirmada").first()
        no_show = db.query(EstadoReserva).filter(EstadoReserva.nombre == "No-Show").first()
        if not confirmado or not no_show:
            return

        ahora = datetime.utcnow()
        reservas = db.query(Reserva).filter(
            Reserva.estado_id == confirmado.id,
            Reserva.hora_inicio + timedelta(minutes=20) < ahora,
        ).all()

        for reserva in reservas:
            reserva.estado_id = no_show.id
            db.add(HistorialEstadoReserva(
                reserva_id=reserva.id,
                estado_anterior="Confirmada",
                estado_nuevo="No-Show",
            ))
        db.commit()
    finally:
        db.close()


def start_noshow_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(revisar_no_shows, "interval", minutes=5)
    scheduler.start()


def shutdown_noshow_scheduler() -> None:
    global scheduler
    if scheduler is None:
        return
    if scheduler.running:
        scheduler.shutdown(wait=False)
    scheduler = None
