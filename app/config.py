import os
from functools import lru_cache

from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Microservicio Reservas"
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/reservasdb")
    administracion_url: AnyUrl = os.getenv("ADMINISTRACION_URL", "http://administracion:8001")
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
    rabbitmq_queue: str = os.getenv("RABBITMQ_QUEUE", "reservas_queue")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
