"""FRED'den aylik makro verileri ceker ve data/processed/makro.parquet olarak kaydeder.

Seriler:
    MORTGAGE30US  -> 30 yillik konut kredisi faizi (ulusal, haftalik -> aylik ortalama)
    UNRATE        -> issizlik orani (ulusal)
    <EYALET>UR    -> eyalet issizlik orani (ornek: FLUR)
    <EYALET>STHPI -> FHFA eyalet ev fiyat endeksi (ceyreklik -> aylik, ileri doldurma)

Kullanim (proje kok dizininden):
    python src/fetch_macro.py

Proje kokundeki .env dosyasinda FRED_API_KEY=... satiri olmali.
"""
from pathlib import Path
import time

import pandas as pd
from fredapi import Fred

KOK = Path(__file__).resolve().parents[2]
ISLENMIS = KOK / "data" / "processed"
CIKTI = ISLENMIS / "makro.parquet"
BASLANGIC, BITIS = "2004-01-01", "2020-12-31"


def anahtar():
    """FRED API anahtarini .env dosyasindan okur."""
    for satir in (KOK / ".env").read_text(encoding="utf-8").splitlines():
        if satir.strip().startswith("FRED_API_KEY="):
            return satir.split("=", 1)[1].strip()
    raise RuntimeError(".env dosyasinda FRED_API_KEY bulunamadi")


def aylik(fred, seri):
    """Seriyi ceker ve ay basi (MS) frekansina cevirir.

    Haftalik seriler aylik ortalamaya iner; ceyreklik seriler
    ceyrek icindeki aylara ileri doldurulur.
    """
    s = fred.get_series(seri, observation_start=BASLANGIC, observation_end=BITIS)
    return s.resample("MS").mean().ffill()


def main():
    fred = Fred(api_key=anahtar())

    ulusal = pd.DataFrame({
        "faiz_30y": aylik(fred, "MORTGAGE30US"),
        "issizlik_abd": aylik(fred, "UNRATE"),
    }).rename_axis("ay").reset_index()

    eyaletler = (pd.read_parquet(ISLENMIS / "tum_krediler.parquet", columns=["property_state"])
                 ["property_state"].dropna().unique())

    parcalar = []
    for st in sorted(eyaletler):
        try:
            e = pd.DataFrame({
                "issizlik_eyalet": aylik(fred, f"{st}UR"),
                "hpi_eyalet": aylik(fred, f"{st}STHPI"),
            })
        except Exception as hata:  # FRED'de serisi olmayan bolgeler (orn. bazi adalar)
            print(f"{st}: atlandi ({hata})")
            continue
        e["property_state"] = st
        parcalar.append(e.rename_axis("ay").reset_index())
        time.sleep(0.6)  # FRED dakikada ~120 istek sinirina takilmamak icin

    eyalet = pd.concat(parcalar, ignore_index=True)
    makro = eyalet.merge(ulusal, on="ay", how="left")
    makro.to_parquet(CIKTI, index=False)

    print(makro.shape, "|", makro["property_state"].nunique(), "eyalet")
    print("Bos oranlari:")
    print(makro.isna().mean().round(3).to_string())


if __name__ == "__main__":
    main()