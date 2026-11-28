"""Uygulama ayarlari (.env'den, pydantic-settings).

DATABASE_URL verilmezse yerel gelistirme icin data/api.db (SQLite, git disi) kullanilir.
Postgres icin ornek: postgresql+psycopg://kullanici:sifre@localhost:5432/kredi_riski
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

KOK = Path(__file__).resolve().parents[1]


class Ayarlar(BaseSettings):
    model_config = SettingsConfigDict(env_file=KOK / ".env", extra="ignore")

    database_url: str = f"sqlite:///{(KOK / 'data' / 'api.db').as_posix()}"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def ayarlari_al() -> Ayarlar:
    return Ayarlar()
