from app.config import get_settings
from app.db import Base, engine
from app.rabbitmq import start_consumer
from app.services.seed import seed_estados_reserva
from app.services.noshow_scheduler import start_noshow_scheduler, shutdown_noshow_scheduler

settings = get_settings()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    seed_estados_reserva()
    start_noshow_scheduler()
    try:
        start_consumer()
    except KeyboardInterrupt:
        print("Servicio detenido por usuario.")
    finally:
        shutdown_noshow_scheduler()


if __name__ == "__main__":
    main()
