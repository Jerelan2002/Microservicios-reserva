from typing import List
from pydantic import BaseModel


class ReporteReservaItem(BaseModel):
    reserva_id: int
    cliente_id: int
    sucursal_id: int
    mesa_id: int
    estado_actual: str
    fecha: str
    hora_inicio: str
    hora_fin: str


class ReporteReservas(BaseModel):
    total_reservas: int
    reservas: List[ReporteReservaItem]
