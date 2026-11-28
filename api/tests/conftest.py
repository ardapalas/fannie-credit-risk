"""Test duzeni: bellek ici SQLite + SENTETIK toplulastirilmis veri (gercek veri kullanilmaz).
Uygulamanin oturum bagimliligi bu veritabanina yonlendirilir."""
import itertools
import os

# Testler HER ZAMAN SQLite + sentetik veri: .env'deki DATABASE_URL (Postgres) testlere karismasin.
# api modulleri ice aktarilmadan ONCE ayarlanmali (motor ice aktarmada olusturuluyor).
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.domain import izgara
from api.integration.db.models import (EyaletOzet, KusakOzet, ModelMetrik, SenaryoSonuc, Taban,
                                       VintageEgri)
from api.integration.db.session import oturum_al
from api.main import app

EKSIK_SENARYO = (6.0, -30.0, -1.0)          # 404 testi icin bilerek yazilmayan izgara noktasi


def sentetik_veri(o):
    for ceyrek, bolum in (("2007Q1", "egitim"), ("2009Q1", "dogrulama")):
        o.add(KusakOzet(ceyrek=ceyrek, bolum=bolum, kredi_sayisi=1000, batti_orani=0.1,
                        erken_orani=0.8, sansurlu_orani=0.1))
        for olay, seri, yas in itertools.product(("batti", "erken_kapatti"), ("gercek", "lgbm"), range(3)):
            if seri == "lgbm" and bolum == "egitim":
                continue                    # model egrisi sadece dogrulama/test kusaklarinda
            o.add(VintageEgri(ceyrek=ceyrek, olay=olay, seri=seri, yas=yas, bolum=bolum, deger=0.01 * yas))
    o.add(EyaletOzet(eyalet="CA", yil=2007, kredi_sayisi=500, batti_orani=0.2))
    o.add(EyaletOzet(eyalet="VI", yil=2007, kredi_sayisi=None, batti_orani=None))   # gizli hucre
    o.add(EyaletOzet(eyalet="CA", yil=2008, kredi_sayisi=400, batti_orani=0.15))
    for bolum in ("dogrulama", "test"):
        o.add(ModelMetrik(metrik="batma_auc", model="LightGBM", durum="sonra", bolum=bolum, deger=0.83))
    for iss, ev, faiz in itertools.product(izgara.ISSIZLIK, izgara.EV_FIYATI, izgara.FAIZ):
        if (iss, ev, faiz) == EKSIK_SENARYO:
            continue
        for ay in range(1, izgara.UFUK + 1):
            # sentetik: deger parametreleri kodlar -> hangi noktanin secildigi testten okunabilir
            o.add(SenaryoSonuc(issizlik=iss, ev_fiyati=ev, faiz=faiz, gecis=izgara.GECIS,
                               ufuk=izgara.UFUK, ay=ay, batma=0.001 * ay, erken=0.01 * ay, acik=1 - 0.011 * ay))
    o.commit()


@pytest.fixture(scope="session")
def istemci():
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Taban.metadata.create_all(motor)
    Oturum = sessionmaker(bind=motor)
    with Oturum() as o:
        sentetik_veri(o)

    def test_oturumu():
        with Oturum() as o:
            yield o

    app.dependency_overrides[oturum_al] = test_oturumu
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
