from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models.estado_reserva import EstadoReserva


ESTADOS_INICIALES = [
    "Pendiente",
    "Confirmada",
    "Check-In",
    "Finalizada",
    "Cancelada",
    "No-Show",
]


def seed_estados_reserva() -> None:
    db: Session = SessionLocal()
    try:
        existentes = {estado.nombre for estado in db.query(EstadoReserva).all()}
        for nombre in ESTADOS_INICIALES:
            if nombre not in existentes:
                db.add(EstadoReserva(nombre=nombre))
        db.commit()
    finally:
        db.close()
