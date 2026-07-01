from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.db import Base


class HistorialEstadoReserva(Base):
    __tablename__ = "historial_estados_reserva"

    id = Column(Integer, primary_key=True, index=True)
    reserva_id = Column(Integer, nullable=False)
    estado_anterior = Column(String(50), nullable=False)
    estado_nuevo = Column(String(50), nullable=False)
    fecha_cambio = Column(DateTime(timezone=True), server_default=func.now())
    usuario_id = Column(Integer, nullable=True)
