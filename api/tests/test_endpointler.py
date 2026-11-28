"""Her endpoint icin testler (sentetik veri, bkz. conftest.py)."""
import pytest

from api.domain.izgara import en_yakin, izgaraya_yuvarla
from api.domain.nesneler import SenaryoParametreleri
from api.tests.conftest import EKSIK_SENARYO


# ------------------------------------------------------------------ /health
def test_health(istemci):
    r = istemci.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["durum"] == "ok" and j["veritabani"] is True
    assert j["senaryo_sayisi"] == 47 and j["senaryo_izgara_boyutu"] == 48


# ------------------------------------------------------------------ /vintages
def test_vintages_filtre(istemci):
    r = istemci.get("/vintages", params={"ceyrek": "2009Q1", "olay": "batti"})
    assert r.status_code == 200
    seriler = r.json()
    assert {s["seri"] for s in seriler} == {"gercek", "lgbm"}
    assert all(s["ceyrek"] == "2009Q1" and s["olay"] == "batti" for s in seriler)
    assert [n["yas"] for n in seriler[0]["noktalar"]] == [0, 1, 2]


def test_vintages_egitim_kusaginda_model_yok(istemci):
    seriler = istemci.get("/vintages", params={"ceyrek": "2007Q1"}).json()
    assert {s["seri"] for s in seriler} == {"gercek"}


@pytest.mark.parametrize("params", [{"olay": "temerrut"}, {"ceyrek": "2013Q1"}, {"ceyrek": "2009-1"}])
def test_vintages_gecersiz_parametre_422(istemci, params):
    assert istemci.get("/vintages", params=params).status_code == 422


# ------------------------------------------------------------------ /cohorts
def test_cohorts(istemci):
    r = istemci.get("/cohorts")
    assert r.status_code == 200
    assert [k["ceyrek"] for k in r.json()] == ["2007Q1", "2009Q1"]
    assert set(r.json()[0]) == {"ceyrek", "bolum", "kredi_sayisi", "batti_orani", "erken_orani",
                                "sansurlu_orani"}


# ------------------------------------------------------------------ /states
def test_states_kucuk_hucre_gizli(istemci):
    r = istemci.get("/states", params={"yil": 2007})
    assert r.status_code == 200
    satir = {e["eyalet"]: e for e in r.json()}
    assert set(satir) == {"CA", "VI"}
    assert satir["VI"] == {"eyalet": "VI", "yil": 2007, "kredi_sayisi": None, "batti_orani": None,
                           "gizli": True}
    assert satir["CA"]["gizli"] is False and satir["CA"]["kredi_sayisi"] == 500


def test_states_gecersiz_yil_422(istemci):
    assert istemci.get("/states", params={"yil": 2004}).status_code == 422


# ------------------------------------------------------------------ /model/metrics
def test_model_metrics_bolum(istemci):
    r = istemci.get("/model/metrics", params={"bolum": "test"})
    assert r.status_code == 200
    assert [m["bolum"] for m in r.json()] == ["test"]
    assert len(istemci.get("/model/metrics").json()) == 2


def test_model_metrics_gecersiz_bolum_422(istemci):
    assert istemci.get("/model/metrics", params={"bolum": "egitim"}).status_code == 422


# ------------------------------------------------------------------ /scenarios
def test_scenarios_tam_izgara_noktasi(istemci):
    r = istemci.get("/scenarios", params={"issizlik": 2, "ev_fiyati": -10, "faiz": 0})
    assert r.status_code == 200
    j = r.json()
    assert j["kullanilan"] == {"issizlik": 2.0, "ev_fiyati": -10.0, "faiz": 0.0}
    assert j["istenen"] == j["kullanilan"]
    assert len(j["egri"]) == 36 and j["egri"][-1]["ay"] == 36
    assert j["gecis"] == 12 and j["ufuk"] == 36 and "50.000" in j["portfoy"]


def test_scenarios_varsayilan_baz(istemci):
    j = istemci.get("/scenarios").json()
    assert j["kullanilan"] == {"issizlik": 0.0, "ev_fiyati": 0.0, "faiz": 0.0}


def test_scenarios_en_yakina_yuvarlar_esitlikte_kotu(istemci):
    # 3 -> 2 ile 4 esit uzak -> 4 (kotu); -15 -> -10/-20 -> -20; 0,5 -> 0/1 -> 1; 1,2 -> 2
    j = istemci.get("/scenarios", params={"issizlik": 3, "ev_fiyati": -15, "faiz": 0.5}).json()
    assert j["kullanilan"] == {"issizlik": 4.0, "ev_fiyati": -20.0, "faiz": 1.0}
    assert j["istenen"] == {"issizlik": 3.0, "ev_fiyati": -15.0, "faiz": 0.5}
    j = istemci.get("/scenarios", params={"issizlik": 1.2, "ev_fiyati": -4, "faiz": -0.6}).json()
    assert j["kullanilan"] == {"issizlik": 2.0, "ev_fiyati": 0.0, "faiz": -1.0}


@pytest.mark.parametrize("params", [{"issizlik": 8}, {"issizlik": -1}, {"ev_fiyati": -40},
                                    {"ev_fiyati": 5}, {"faiz": 2}, {"faiz": "yuksek"}])
def test_scenarios_aralik_disi_422(istemci, params):
    assert istemci.get("/scenarios", params=params).status_code == 422


def test_scenarios_hesaplanmamis_nokta_404(istemci):
    iss, ev, faiz = EKSIK_SENARYO
    r = istemci.get("/scenarios", params={"issizlik": iss, "ev_fiyati": ev, "faiz": faiz})
    assert r.status_code == 404


# ------------------------------------------------------------------ domain (saf kural)
def test_en_yakin_kurali():
    assert en_yakin(5.0, (0.0, 2.0, 4.0, 6.0), kotu_yuksek=True) == 6.0      # esitlik -> yuksek
    assert en_yakin(-5.0, (-10.0, 0.0), kotu_yuksek=False) == -10.0          # esitlik -> dusuk
    assert en_yakin(0.9, (0.0, 2.0), kotu_yuksek=True) == 0.0
    with pytest.raises(ValueError):
        en_yakin(7.0, (0.0, 6.0), kotu_yuksek=True)
    assert izgaraya_yuvarla(SenaryoParametreleri(6, -30, 1)) == SenaryoParametreleri(6.0, -30.0, 1.0)


# ------------------------------------------------------------------ CORS + Swagger
def test_cors_react_gelistirme_sunucusu(istemci):
    r = istemci.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = istemci.get("/health", headers={"Origin": "http://kotu-site.example"})
    assert "access-control-allow-origin" not in r.headers


def test_openapi_semasi(istemci):
    sema = istemci.get("/openapi.json").json()
    assert {"/health", "/vintages", "/cohorts", "/states", "/model/metrics", "/scenarios"} <= set(sema["paths"])
    assert istemci.get("/docs").status_code == 200
