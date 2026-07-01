from datetime import datetime
from pydantic import BaseModel, conint, constr


class ReservaBase(BaseModel):
    cliente_id: int
    restaurante_id: int
    sucursal_id: int
    fecha: datetime
    hora_inicio: datetime
    hora_fin: datetime
    numero_personas: conint(gt=0)


class ReservaCreate(ReservaBase):
    mesa_id: int | None = None


class ReservaUpdate(BaseModel):
    cliente_id: int | None = None
    mesa_id: int | None = None
    fecha: datetime | None = None
    hora_inicio: datetime | None = None
    hora_fin: datetime | None = None
    numero_personas: conint(gt=0) | None = None
    estado_id: int | None = None


class ReservaOut(ReservaBase):
    id: int
    mesa_id: int
    estado_id: int
    fecha_creacion: datetime
    fecha_confirmacion: datetime | None = None

    model_config = {
        "from_attributes": True,
    }
