from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, condecimal, constr


class AnticipoCreate(BaseModel):
    monto: condecimal(gt=0, max_digits=10, decimal_places=2)
    metodo_pago: constr(strip_whitespace=True, min_length=3)


class AnticipoOut(BaseModel):
    id: int
    reserva_id: int
    monto: Decimal
    metodo_pago: str
    fecha_pago: datetime
    estado: str

    model_config = {
        "from_attributes": True,
    }
