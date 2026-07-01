from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func
import enum
from app.db import Base


class EstadoAnticipo(str, enum.Enum):
    PAGADO = "Pagado"
    PENDIENTE = "Pendiente"


class Anticipo(Base):
    __tablename__ = "anticipos"

    id = Column(Integer, primary_key=True, index=True)
    reserva_id = Column(Integer, ForeignKey("reservas.id"), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    metodo_pago = Column(String(50), nullable=False)
    fecha_pago = Column(DateTime(timezone=True), server_default=func.now())
    estado = Column(Enum(EstadoAnticipo), nullable=False, default=EstadoAnticipo.PENDIENTE)
