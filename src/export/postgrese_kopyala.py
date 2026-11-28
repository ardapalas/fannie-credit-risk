"""SQLite (data/api.db) -> PostgreSQL: senaryo_sonuc kopyalama ve tablolari karsilastirma.

Kullanim (proje kok dizininden; hedef DATABASE_URL ile verilir, .env veya ortam degiskeni):
    python src/export/postgrese_kopyala.py                # senaryo_sonuc'u kopyala + tum tablolari karsilastir
    python src/export/postgrese_kopyala.py --karsilastir  # HICBIR SEY YAZMAZ: tablolari karsilastir

- Kaynak her zaman SQLite (data/api.db). Hedef SQLite ise calismaz.
- Izgara TAM degilse (48 senaryo x 36 ay = 1.728 satir) kopyalamaz -> yarim veri gitmez.
- Kopyalama tek transaction: hedefteki senaryo_sonuc silinir, kaynaktan yazilir, sonra satir
  sayisi ve degerler dogrulanir.
- Statik tablolar (vintage_egri, kusak_ozet, eyalet_ozet, model_metrik) kopyalanmaz; Postgres'e
  statik_export.py ile dogrudan yazilir. Bu script onlari sadece karsilastirir.
"""
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

import pandas as pd  # noqa: E402
from sqlalchemy import delete, func, select  # noqa: E402

from api.domain import izgara  # noqa: E402
from api.integration.db.models import (EyaletOzet, KusakOzet, ModelMetrik, SenaryoSonuc,  # noqa: E402
                                       Taban, VintageEgri)
from api.integration.db.session import motor as hedef_motor, motor_olustur  # noqa: E402

KAYNAK_URL = f"sqlite:///{(KOK / 'data' / 'api.db').as_posix()}"
BEKLENEN = len(izgara.ISSIZLIK) * len(izgara.EV_FIYATI) * len(izgara.FAIZ) * izgara.UFUK   # 1.728
TABLOLAR = [VintageEgri, KusakOzet, EyaletOzet, ModelMetrik, SenaryoSonuc]


def oku(motor, tablo) -> pd.DataFrame:
    anahtar = [c.name for c in tablo.__table__.primary_key.columns]
    return pd.read_sql(select(tablo.__table__), motor).sort_values(anahtar).reset_index(drop=True)


def karsilastir(kaynak, hedef):
    """Her tablo: satir sayisi, ayni anahtarlar, en buyuk sayisal fark, null'lar ayni yerde mi."""
    tamam = True
    for tablo in TABLOLAR:
        a, b = oku(kaynak, tablo), oku(hedef, tablo)
        if a.shape != b.shape:
            print(f"  {tablo.__tablename__:14s} FARKLI: sqlite {len(a):,} / postgres {len(b):,} satir")
            tamam = False
            continue
        sayisal = a.select_dtypes("number").columns
        metin = [c for c in a.columns if c not in sayisal]
        anahtar_ayni = a[metin].astype(str).equals(b[metin].astype(str))
        null_ayni = a.isna().equals(b.isna())
        fark = float((a[sayisal] - b[sayisal]).abs().max().max()) if len(a) else 0.0
        ok = anahtar_ayni and null_ayni and fark < 1e-12
        tamam &= ok
        print(f"  {tablo.__tablename__:14s} {len(a):>6,} satir | anahtarlar ayni: {anahtar_ayni} | "
              f"null'lar ayni: {null_ayni} | en buyuk fark: {fark:.1e} | {'TAMAM' if ok else 'FARKLI'}")
    return tamam


def main():
    if hedef_motor.dialect.name == "sqlite":
        sys.exit("hedef SQLite: DATABASE_URL'i Postgres'e ayarlayin (bkz. .env.example)")
    kaynak = motor_olustur(KAYNAK_URL)
    Taban.metadata.create_all(hedef_motor)

    if "--karsilastir" not in sys.argv:
        df = oku(kaynak, SenaryoSonuc)
        senaryo = df[["issizlik", "ev_fiyati", "faiz"]].drop_duplicates().shape[0]
        if len(df) != BEKLENEN:
            sys.exit(f"izgara tamam degil: SQLite'ta {len(df):,} / {BEKLENEN:,} satir ({senaryo} senaryo). "
                     "Kopyalanmadi.")
        with hedef_motor.begin() as c:                 # tek transaction
            c.execute(delete(SenaryoSonuc))
            c.execute(SenaryoSonuc.__table__.insert(), df.to_dict("records"))
        with hedef_motor.connect() as c:
            n = c.scalar(select(func.count()).select_from(SenaryoSonuc))
        print(f"senaryo_sonuc kopyalandi: {n:,} satir (beklenen {BEKLENEN:,}), {senaryo} senaryo")

    print("SQLite -> Postgres karsilastirma:")
    tamam = karsilastir(kaynak, hedef_motor)
    print("SONUC:", "tum tablolar ayni" if tamam else "FARK VAR (senaryo_sonuc kopyalanmadiysa beklenen)")


if __name__ == "__main__":
    main()
