import os
from functools import lru_cache

from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Microservicio Reservas"
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@localhost:5432/reservasdb")
    administracion_url: AnyUrl = os.getenv("ADMINISTRACION_URL", "http://administracion:8001")
    jwt_public_key: str = os.getenv("JWT_PUBLIC_KEY", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "RS256")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "reservas-service")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "security-service")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
