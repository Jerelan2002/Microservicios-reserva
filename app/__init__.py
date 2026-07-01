from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import clientes, reservas, reportes
from app.utils.jwt_validator import validar_jwt
from app.db import engine, Base
from app.services.seed import seed_estados_reserva
from app.services.noshow_scheduler import start_noshow_scheduler, shutdown_noshow_scheduler

app = FastAPI(
    title="Reservas Microservice",
    version="0.1.0",
    description="Servicio de reservas con validación de disponibilidad, anticipos y estados de reserva.",
    dependencies=[Depends(validar_jwt)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
app.include_router(reservas.router, prefix="/reservas", tags=["Reservas"])
app.include_router(reportes.router, prefix="/reportes", tags=["Reportes"])


@app.get("/", include_in_schema=False)
def root_status():
    return {
        "status": "ok",
        "message": "Reservas Microservice is running",
        "docs": "/docs",
    }


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    seed_estados_reserva()
    start_noshow_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    shutdown_noshow_scheduler()
