"""Modellerin ortak kullandigi ozellik listeleri, veri yukleme ve on isleme."""
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler

KOK = Path(__file__).resolve().parents[2]
EGITIM_SETI = KOK / "data" / "processed" / "egitim_seti.parquet"
MODELLER = KOK / "models"

# Sayisal ozellikler: kredinin sabit bilgileri + o ayki yas ve ekonomik kosullar
SAYISAL = [
    "yas",
    "original_interest_rate", "original_upb", "original_loan_term",
    "original_loan_to_value_ratio_ltv", "original_combined_loan_to_value_ratio_cltv",
    "number_of_borrowers", "debt_to_income_dti", "borrower_credit_score_at_origination",
    "mortgage_insurance_percentage", "skor_min",
    "issizlik_eyalet",
    "faiz_farki", "guncel_ltv", "issizlik_degisim",
]
# faiz_30y ve issizlik_abd CIKARILDI (veri setinde duruyorlar, sadece modele girmiyorlar).
# Neden: ulusal zaman serileri -> her ay tum krediler icin ayni deger, pratikte "takvim".
# Cikarma deneyinde (deney_cikarma.py, LightGBM, dogrulama 2009) AUC degismedi
# (batma 0,833 -> 0,833) ama fazla tahmin azaldi (batma 1,45 -> 1,38; erken kapanis
# 1,42 -> 1,26): model kriz yillarinin seviyelerini 2009'a tasiyordu.

# 0/1 eksiklik ve durum isaretleri
ISARET = ["dti_eksik", "skor_eksik", "ortak_borclu_var", "ortak_skor_eksik", "mi_eksik"]
# Kategorik ozellikler
KATEGORIK = [
    "channel", "first_time_home_buyer_indicator", "loan_purpose", "property_type",
    "occupancy_status", "property_state", "mortgage_insurance_type",
]
OZELLIKLER = SAYISAL + ISARET + KATEGORIK

# Bilerek DISARIDA birakilanlar:
#   ceyrek -> test donemindeki ceyrekler egitimde hic yok; model "hangi ceyrek" ezberlerdi
#   ay     -> takvim tarihi; ekonomik etkisi zaten makro degiskenlerde


def yukle(bolumler=("egitim", "dogrulama", "test"), ozellikler=OZELLIKLER):
    """Egitim setini okur ve bolumlere ayirir: {'egitim': df, 'dogrulama': df, ...}
    ozellikler: okunacak ozellik sutunlari (deneylerde modelden cikarilmislar da okunabilsin)."""
    sutunlar = list(ozellikler) + ["kredi_id", "ay", "ceyrek", "y", "agirlik", "bolum"]
    d = pd.read_parquet(EGITIM_SETI, columns=sutunlar)
    d["agirlik"] = d["agirlik"].astype(float)
    return {b: d[d["bolum"] == b].reset_index(drop=True) for b in bolumler}


def onisleyici_dogrusal():
    """Lojistik regresyon / sinir agi icin on isleme.

    - yas: spline ile esnek egri (batma riski 2-4. yillarda tumsek yapiyor,
      duz bir cizgi bunu yakalayamaz)
    - diger sayisallar: ortanca ile doldur + olcekle
    - kategorikler: one-hot (az gorulen kategoriler 'diger' olarak birlesir)
    Ortanca ve olcekleme yalnizca EGITIM verisinden ogrenilir (fit sirasinda).
    """
    return ColumnTransformer([
        ("yas", make_pipeline(
            SimpleImputer(strategy="median"),
            SplineTransformer(n_knots=6, degree=3, extrapolation="constant")), ["yas"]),
        ("sayisal", make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler()),
         [c for c in SAYISAL if c != "yas"]),
        ("isaret", "passthrough", ISARET),
        ("kategorik", make_pipeline(
            SimpleImputer(strategy="constant", fill_value="bilinmiyor"),
            OneHotEncoder(handle_unknown="ignore", min_frequency=100)), KATEGORIK),
    ])