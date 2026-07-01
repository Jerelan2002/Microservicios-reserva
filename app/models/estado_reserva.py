from sqlalchemy import Column, Integer, String
from app.db import Base


class EstadoReserva(Base):
    __tablename__ = "estados_reserva"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)
