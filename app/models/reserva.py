from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func
from app.db import Base


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    restaurante_id = Column(Integer, nullable=False)
    sucursal_id = Column(Integer, nullable=False)
    mesa_id = Column(Integer, nullable=False)
    fecha = Column(DateTime(timezone=True), nullable=False)
    hora_inicio = Column(DateTime(timezone=True), nullable=False)
    hora_fin = Column(DateTime(timezone=True), nullable=False)
    numero_personas = Column(Integer, nullable=False)
    estado_id = Column(Integer, ForeignKey("estados_reserva.id"), nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_confirmacion = Column(DateTime(timezone=True), nullable=True)
