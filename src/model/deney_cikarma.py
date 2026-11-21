"""Cikarma deneyi: takvim/eyalet bilgisi tasiyan ozellikler model icin ne kadar onemli?

Kullanim (proje kok dizininden):
    python src/model/deney_cikarma.py

Her varyant model_lgbm.py ile ayni ayarlarla egitilir; erken durdurma ayni
%10'luk egitim kredisi kumesinde (kredi bazinda). Sonuclar DOGRULAMA (2009)
bolumunde. Test bolumune DOKUNMAZ. Model kaydetmez.
"""
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from features import yukle
from model_lgbm import PARAMETRELER, hazirla, kategorileri_ogren, kredi_bazli_ayir

# Ozellik listeleri BILEREK burada acikca yazili: features.py'deki guncel liste
# degisse de deney 2026-11-14'teki haliyle tekrarlanabilsin.
TAM = [
    # sayisal
    "yas",
    "original_interest_rate", "original_upb", "original_loan_term",
    "original_loan_to_value_ratio_ltv", "original_combined_loan_to_value_ratio_cltv",
    "number_of_borrowers", "debt_to_income_dti", "borrower_credit_score_at_origination",
    "mortgage_insurance_percentage", "skor_min",
    "faiz_30y", "issizlik_abd", "issizlik_eyalet",
    "faiz_farki", "guncel_ltv", "issizlik_degisim",
    # isaretler
    "dti_eksik", "skor_eksik", "ortak_borclu_var", "ortak_skor_eksik", "mi_eksik",
    # kategorik
    "channel", "first_time_home_buyer_indicator", "loan_purpose", "property_type",
    "occupancy_status", "property_state", "mortgage_insurance_type",
]


def haric(*cikan):
    return [c for c in TAM if c not in cikan]


VARYANTLAR = {
    "(a) tam model": TAM,
    "(b) faiz_30y, issizlik_abd yok": haric("faiz_30y", "issizlik_abd"),
    "(c) property_state yok": haric("property_state"),
    "(d) ucu de yok": haric("faiz_30y", "issizlik_abd", "property_state"),
}


def main():
    veri = yukle(("egitim", "dogrulama"), ozellikler=TAM)
    egt, dgr = veri["egitim"], veri["dogrulama"]
    kategoriler = kategorileri_ogren(egt)
    egt_ic, durdurma = kredi_bazli_ayir(egt)
    y, w = dgr["y"].to_numpy(), dgr["agirlik"].to_numpy()

    satirlar = []
    for ad, ozl in VARYANTLAR.items():
        model = lgb.LGBMClassifier(**PARAMETRELER)
        model.fit(
            hazirla(egt_ic, kategoriler, ozl), egt_ic["y"], sample_weight=egt_ic["agirlik"],
            eval_set=[(hazirla(durdurma, kategoriler, ozl), durdurma["y"])],
            eval_sample_weight=[durdurma["agirlik"]],
            callbacks=[lgb.early_stopping(100, verbose=False)],
        )
        p = model.predict_proba(hazirla(dgr, kategoriler, ozl))
        satir = {"varyant": ad, "agac": model.best_iteration_}
        for k, olay in [(1, "batma"), (2, "erken")]:
            satir[f"{olay}_auc"] = roc_auc_score(y == k, p[:, k], sample_weight=w)
            satir[f"{olay}_tahmin/gercek"] = (np.average(p[:, k], weights=w)
                                             / np.average(y == k, weights=w))
        satirlar.append(satir)
        print(satir, flush=True)

    print("\n" + pd.DataFrame(satirlar).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
