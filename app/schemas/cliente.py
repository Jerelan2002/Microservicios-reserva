from datetime import datetime
from pydantic import BaseModel, EmailStr, constr


class ClienteBase(BaseModel):
    nombre: constr(strip_whitespace=True, min_length=1)
    apellido: constr(strip_whitespace=True, min_length=1)
    identificacion: constr(strip_whitespace=True, min_length=5)
    telefono: constr(strip_whitespace=True, min_length=7)
    email: EmailStr


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: constr(strip_whitespace=True, min_length=1) | None = None
    apellido: constr(strip_whitespace=True, min_length=1) | None = None
    telefono: constr(strip_whitespace=True, min_length=7) | None = None
    email: EmailStr | None = None


class ClienteOut(ClienteBase):
    id: int
    fecha_registro: datetime

    model_config = {
        "from_attributes": True,
    }
