"""Fannie Mae ceyrek dosyasini kredi bazinda, modele hazir bir tabloya cevirir.

Kullanim (proje kok dizininden):
    python src/prepare_data.py 2007Q1
    python src/prepare_data.py 2005Q1 2005Q2 2005Q3

Her ceyrek icin iki dosya uretir:
    data/processed/<ceyrek>_raw.parquet    -> orneklenmis ham kredi-ay verisi
    data/processed/<ceyrek>_kredi.parquet  -> kredi basina sonuc + baslangic ozellikleri
"""
from pathlib import Path
import re
import sys

import duckdb
import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
HAM = KOK / "data" / "raw"
ISLENMIS = KOK / "data" / "processed"
SOZLUK = HAM / "crt-file-layout-and-glossary.xlsx"

KESIM = pd.Timestamp("2020-02-01")           # COVID ertelemeleri oncesi gozlem sonu
ZARAR_KODLARI = ("02", "03", "09", "15")     # zararla kapanis kodlari

SAYISAL = [
    "original_interest_rate", "original_upb", "original_loan_term",
    "original_loan_to_value_ratio_ltv", "original_combined_loan_to_value_ratio_cltv",
    "number_of_borrowers", "debt_to_income_dti", "borrower_credit_score_at_origination",
    "co_borrower_credit_score_at_origination", "mortgage_insurance_percentage",
]
KATEGORIK = [
    "channel", "first_time_home_buyer_indicator", "loan_purpose", "property_type",
    "occupancy_status", "property_state", "mortgage_insurance_type",
]
# Modele ASLA girdi olarak verilmeyecek sutunlar ("ne oldu" bilgisi + kimlik)
SONUC = ["kredi_id", "ceyrek", "ilk_90_ay", "son_ay", "zb_kod", "batma_ay", "olay", "olay_ay"]


def alan_adlari(sozluk_yolu=SOZLUK):
    """Sozlukteki alan adlarini pozisyon sirasiyla, snake_case olarak dondurur."""
    lay = pd.read_excel(sozluk_yolu, sheet_name=0)
    lay["pos"] = pd.to_numeric(lay["Field Position"], errors="coerce")
    lay = lay.dropna(subset=["pos"]).sort_values("pos")
    return [re.sub(r"[^a-z0-9]+", "_", str(n).strip().lower()).strip("_")
            for n in lay["Field Name"]]


def alan_sayisi(csv_yolu):
    """Dosyanin ilk satirindaki alan sayisi (ayirici sayisi + 1)."""
    with open(csv_yolu) as f:
        return f.readline().count("|") + 1


def ham_parquet(con, ceyrek, oran):
    """CSV'yi isimlendirip kredilerin bir kismini orneklenmis olarak Parquet'e yazar.

    Ornekleme kredi kimligine gore yapilir: bir kredi seciliyse tum aylari gelir.
    hash() ile yapildigi icin her calistirmada ayni krediler secilir.
    """
    csv = HAM / f"{ceyrek}.csv"
    cikti = ISLENMIS / f"{ceyrek}_raw.parquet"
    adlar = alan_adlari()
    n = alan_sayisi(csv)
    if n > len(adlar):
        raise ValueError(f"{ceyrek}: dosyada {n} alan var, sozlukte {len(adlar)}")
    adlar = adlar[:n]
    esik = int(round(oran * 1000))
    con.execute(f"""
        COPY (
            SELECT * FROM read_csv('{csv}', delim='|', header=false,
                                   all_varchar=true, names={adlar})
            WHERE hash(loan_identifier) % 1000 < {esik}
        ) TO '{cikti}' (FORMAT parquet)
    """)
    return cikti


def sonuclar(con, p):
    """Her kredi icin olay (batti / erken_kapatti / sansurlu) ve olay tarihini cikarir."""
    s = con.sql(f"""
        WITH aylik AS (
            SELECT loan_identifier AS kredi_id,
                   strptime(monthly_reporting_period, '%m%Y')::DATE AS ay,
                   TRY_CAST(current_loan_delinquency_status AS INT) AS gecikme,
                   zero_balance_code AS zb_kod
            FROM '{p}')
        SELECT kredi_id,
               MIN(ay) FILTER (WHERE gecikme >= 3) AS ilk_90_ay,
               MAX(ay) AS son_ay,
               MAX(zb_kod) AS zb_kod
        FROM aylik GROUP BY 1
    """).df()
    s["ilk_90_ay"] = pd.to_datetime(s["ilk_90_ay"])
    s["son_ay"] = pd.to_datetime(s["son_ay"])

    # 90+'ya hic dusmeden zararla kapananlarda batma tarihi = kapanis ayi
    zarar = s["zb_kod"].isin(ZARAR_KODLARI)
    s["batma_ay"] = s["ilk_90_ay"].fillna(s["son_ay"].where(zarar))

    batti = s["batma_ay"] <= KESIM
    erken = ~batti & (s["zb_kod"] == "01") & (s["son_ay"] <= KESIM)
    s["olay"] = np.select([batti, erken], ["batti", "erken_kapatti"], "sansurlu")
    s["olay_ay"] = pd.to_datetime(np.select(
        [batti, erken], [s["batma_ay"], s["son_ay"]], s["son_ay"].clip(upper=KESIM)))
    return s


def baslangic(con, p):
    """Her kredinin ilk ayindan, kredi verildigi anda bilinen bilgileri ceker."""
    secim = ", ".join([f"TRY_CAST({c} AS DOUBLE) AS {c}" for c in SAYISAL] + KATEGORIK)
    return con.sql(f"""
        SELECT loan_identifier AS kredi_id, {secim} FROM '{p}'
        QUALIFY ROW_NUMBER() OVER (PARTITION BY loan_identifier
                ORDER BY strptime(monthly_reporting_period, '%m%Y')) = 1
    """).df()


def eksikleri_isle(d):
    """Eksikler icin isaretler koyar ve sadece MANTIKSAL doldurmalari yapar.

    Ortanca ile doldurma burada YAPILMAZ: ortanca egitim verisinden hesaplanmali,
    o yuzden modelleme asamasina birakiliyor.
    """
    b = "borrower_credit_score_at_origination"
    c = "co_borrower_credit_score_at_origination"
    ltv = "original_loan_to_value_ratio_ltv"
    cltv = "original_combined_loan_to_value_ratio_cltv"
    mi = "mortgage_insurance_percentage"

    d["dti_eksik"] = d["debt_to_income_dti"].isna().astype(int)
    d["skor_eksik"] = d[b].isna().astype(int)
    d["ortak_borclu_var"] = (d["number_of_borrowers"] >= 2).astype(int)
    d["ortak_skor_eksik"] = ((d["ortak_borclu_var"] == 1) & d[c].isna()).astype(int)
    d["skor_min"] = d[[b, c]].min(axis=1)        # iki borclunun dusuk skoru

    d[cltv] = d[cltv].fillna(d[ltv])             # ikinci kredi bilgisi yoksa CLTV = LTV
    ltv80 = d[ltv] <= 80
    d["mi_eksik"] = (~ltv80 & d[mi].isna()).astype(int)
    d.loc[ltv80, mi] = 0                         # LTV <= 80: sigorta zorunlu degil

    d["first_time_home_buyer_indicator"] = d["first_time_home_buyer_indicator"].fillna("U")
    d["mortgage_insurance_type"] = d["mortgage_insurance_type"].fillna("yok")
    return d.drop(columns=[c])


def hazirla(ceyrek, oran=0.05, con=None):
    """Tek bir ceyregi bastan sona isler ve kredi tablosunu kaydeder."""
    ISLENMIS.mkdir(parents=True, exist_ok=True)
    if con is None:
        con = duckdb.connect()
        con.execute("SET memory_limit='4GB'")
    p = ham_parquet(con, ceyrek, oran)
    d = sonuclar(con, p).merge(baslangic(con, p), on="kredi_id", how="left")
    d = eksikleri_isle(d)
    d.insert(1, "ceyrek", ceyrek)
    d.to_parquet(ISLENMIS / f"{ceyrek}_kredi.parquet", index=False)
    return d


def ozellikler(d):
    """Modele girecek sutunlar: SONUC listesinde olmayan her sey."""
    return [c for c in d.columns if c not in SONUC]


if __name__ == "__main__":
    for ceyrek in sys.argv[1:]:
        d = hazirla(ceyrek)
        oranlar = d["olay"].value_counts(normalize=True).round(3).to_dict()
        print(f"{ceyrek}: {len(d)} kredi, {len(ozellikler(d))} ozellik, {oranlar}")
