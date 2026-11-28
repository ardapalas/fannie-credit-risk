"""Statik toplulastirilmis tablolari veritabanina yazar: vintage_egri, kusak_ozet, eyalet_ozet,
model_metrik. (senaryo_sonuc ayri: senaryo_izgara.py)

Kullanim (proje kok dizininden):
    python src/export/statik_export.py

- Model CALISTIRILMAZ: model egrileri data/processed/test_tahminleri.parquet'ten,
  metrikler reports/tables/test_sonuclari.csv'den okunur.
- Gercek vintage egrileri kredi_ay tablosunun TAMAMINDAN (orneklemsiz), vintage.py ile ayni
  yarisan risk hesabi: h_k(t) = olay / risk, S(t) = prod(1 - h1 - h2), CIF_k(t) = sum S(t-1) h_k(t).
- LISANS / kucuk hucre kurali: sadece toplulastirilmis veri. Riskte 30'dan az kredi kalan yas
  noktalari ATILIR; eyalet x yil hucrelerinde 30'dan az kredi -> kredi_sayisi ve oran NULL.
- Tekrar calistirilabilir: bu dort tablo silinip yeniden yazilir (senaryo_sonuc'a dokunmaz).
"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(KOK), str(KOK / "src" / "model")]

import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402

from api.integration.db.models import (EyaletOzet, KusakOzet, ModelMetrik, Taban,  # noqa: E402
                                       VintageEgri)
from api.integration.db.session import OturumYap, motor  # noqa: E402
from vintage import birikimli  # noqa: E402

ISLENMIS = (KOK / "data" / "processed").as_posix()
ESIK = 30                                   # kucuk hucre kurali
OLAY_AD = {1: "batti", 2: "erken_kapatti"}


def bolum(ceyrek: str) -> str:
    yil = int(ceyrek[:4])
    return "egitim" if yil <= 2008 else ("dogrulama" if yil == 2009 else "test")


def gercek_egriler(con):
    """Her ceyrek ve yas icin risk kumesi ve olay sayilari (kredi_ay, orneklemsiz) -> CIF."""
    g = con.sql(f"""
        SELECT k.ceyrek, a.yas, COUNT(*) AS risk,
               SUM((a.y = 1)::INT) AS b, SUM((a.y = 2)::INT) AS e
        FROM read_parquet('{ISLENMIS}/kredi_ay.parquet') a
        JOIN read_parquet('{ISLENMIS}/tum_krediler.parquet') k ON a.kredi_id = k.kredi_id
        GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    parcalar = []
    for ceyrek, c in g.groupby("ceyrek"):
        c = c.sort_values("yas")
        h1, h2 = c["b"] / c["risk"], c["e"] / c["risk"]
        s_once = (1 - h1 - h2).cumprod().shift(1, fill_value=1.0)
        c = c.assign(cif1=(s_once * h1).cumsum(), cif2=(s_once * h2).cumsum())
        parcalar.append(c)
    return pd.concat(parcalar)          # ceyrek, yas, risk, b, e, cif1, cif2


def vintage_satirlari(con):
    g = gercek_egriler(con)
    risk = g.set_index(["ceyrek", "yas"])["risk"]
    gizlenen = int((g["risk"] < ESIK).sum())
    g = g[g["risk"] >= ESIK]
    satir = []
    for k in (1, 2):
        satir += [dict(ceyrek=r.ceyrek, olay=OLAY_AD[k], seri="gercek", yas=int(r.yas),
                       bolum=bolum(r.ceyrek), deger=float(getattr(r, f"cif{k}")))
                  for r in g.itertuples()]

    # Kalibre LightGBM egrileri: dogrulama + test kusaklari, kayitli tahminlerden
    t = pd.read_parquet(f"{ISLENMIS}/test_tahminleri.parquet",
                        columns=["ceyrek", "yas", "y", "agirlik", "lgbm_kal_batma", "lgbm_kal_erken"])
    for ceyrek, c in t.groupby("ceyrek"):
        q1, q2 = c["lgbm_kal_batma"].to_numpy(), c["lgbm_kal_erken"].to_numpy()
        p = np.column_stack([1 - q1 - q2, q1, q2])
        e = birikimli(c["yas"].to_numpy().astype(int), c["y"].to_numpy(), c["agirlik"].to_numpy(), p)
        for yas, r in e.iterrows():
            if risk.get((ceyrek, yas), 0) < ESIK:      # ayni kucuk hucre kurali
                continue
            for k in (1, 2):
                satir.append(dict(ceyrek=ceyrek, olay=OLAY_AD[k], seri="lgbm", yas=int(yas),
                                  bolum=bolum(ceyrek), deger=float(r[k])))
    return satir, gizlenen, g


def kusak_satirlari(con):
    d = con.sql(f"""
        SELECT ceyrek, COUNT(*) AS n,
               AVG((olay = 'batti')::INT) AS b, AVG((olay = 'erken_kapatti')::INT) AS e,
               AVG((olay = 'sansurlu')::INT) AS s
        FROM read_parquet('{ISLENMIS}/tum_krediler.parquet') GROUP BY 1 ORDER BY 1
    """).df()
    return [dict(ceyrek=r.ceyrek, bolum=bolum(r.ceyrek), kredi_sayisi=int(r.n), batti_orani=float(r.b),
                 erken_orani=float(r.e), sansurlu_orani=float(r.s)) for r in d.itertuples()]


def eyalet_satirlari(con):
    d = con.sql(f"""
        SELECT property_state AS eyalet, CAST(left(ceyrek, 4) AS INT) AS yil, COUNT(*) AS n,
               AVG((olay = 'batti')::INT) AS b
        FROM read_parquet('{ISLENMIS}/tum_krediler.parquet')
        WHERE property_state IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    kucuk = d["n"] < ESIK
    satir = [dict(eyalet=r.eyalet, yil=int(r.yil),
                  kredi_sayisi=None if r.n < ESIK else int(r.n),
                  batti_orani=None if r.n < ESIK else float(r.b)) for r in d.itertuples()]
    return satir, int(kucuk.sum())


def metrik_satirlari():
    t = pd.read_csv(KOK / "reports" / "tables" / "test_sonuclari.csv", header=[0, 1], index_col=[0, 1])
    uzun = t.stack([0, 1], future_stack=True).dropna()
    return [dict(metrik=m, model=mo, durum=du, bolum=b, deger=float(v))
            for (m, mo, du, b), v in uzun.items()]


def main():
    tablolar = [VintageEgri, KusakOzet, EyaletOzet, ModelMetrik]
    Taban.metadata.create_all(motor, tables=[t.__table__ for t in tablolar])
    con = duckdb.connect()
    con.execute("SET memory_limit='6GB'")

    vintage, gizli_yas, g = vintage_satirlari(con)
    kusak = kusak_satirlari(con)
    eyalet, gizli_eyalet = eyalet_satirlari(con)
    metrik = metrik_satirlari()

    with OturumYap.begin() as o:                # tek transaction: ya hepsi ya hicbiri
        for tablo, satirlar in [(VintageEgri, vintage), (KusakOzet, kusak),
                                (EyaletOzet, eyalet), (ModelMetrik, metrik)]:
            o.execute(delete(tablo))
            o.execute(tablo.__table__.insert(), satirlar)

    # ------------------------------------------------------------------ kontroller
    with OturumYap() as o:
        for tablo in tablolar:
            print(f"{tablo.__tablename__:14s} {o.scalar(select(func.count()).select_from(tablo)):>7,} satir")
        print(f"gizlenen: {gizli_yas} vintage yas noktasi (risk < {ESIK}), "
              f"{gizli_eyalet} eyalet x yil hucresi (kredi < {ESIK})")
        toplam = o.scalar(select(func.sum(KusakOzet.kredi_sayisi)))
        print(f"kusak_ozet toplam kredi: {toplam:,} (beklenen 688.611)")
        for c in ("2007Q1", "2009Q1", "2012Q4"):
            k = o.get(KusakOzet, c)
            print(f"  {c}: {k.kredi_sayisi:,} kredi | batti %{100 * k.batti_orani:.1f} "
                  f"erken %{100 * k.erken_orani:.1f} sansurlu %{100 * k.sansurlu_orani:.1f}")
        seri_sayisi = o.execute(select(VintageEgri.seri, func.count(func.distinct(VintageEgri.ceyrek)))
                                .group_by(VintageEgri.seri)).all()
        print(f"vintage_egri kusak sayisi (seri basina): {dict(seri_sayisi)}")
        # notlar.txt: 2009Q1 gercek batma 36. ay 1,52 / 60. ay 2,36 (orneklemli egitim setinden)
        for yas in (36, 60):
            v = o.get(VintageEgri, ("2009Q1", "batti", "gercek", yas))
            l = o.get(VintageEgri, ("2009Q1", "batti", "lgbm", yas))
            print(f"  2009Q1 batma {yas}. ay: gercek %{100 * v.deger:.2f}, lgbm %{100 * l.deger:.2f}")
    print(f"en kucuk risk kumesi (tutulan noktalar): {int(g['risk'].min())}")


if __name__ == "__main__":
    main()
