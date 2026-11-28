"""Veritabani motoru ve oturum (FastAPI Depends ile verilir)."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from api.config import ayarlari_al


def motor_olustur(url: str) -> Engine:
    if url.startswith("sqlite"):
        # SQLite: ayni dosyaya ayni anda yazan export scriptleri icin bekleme suresi
        return create_engine(url, connect_args={"check_same_thread": False, "timeout": 60})
    return create_engine(url, pool_pre_ping=True)


motor = motor_olustur(ayarlari_al().database_url)
OturumYap = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


def oturum_al() -> Iterator[Session]:
    oturum = OturumYap()
    try:
        yield oturum
    finally:
        oturum.close()
