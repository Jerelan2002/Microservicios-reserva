from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.db import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    identificacion = Column(String(50), nullable=False, unique=True)
    telefono = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
