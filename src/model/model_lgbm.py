"""LightGBM: cok sinifli gradyan arttirmali agaclar (devam / batti / erken kapatti).

Kullanim (proje kok dizininden):
    python src/model/model_lgbm.py

Lojistik regresyonla ayni ozellikler, ayni agirliklar, ayni metrikler.
Agaclar esik etkilerini (ornek: LTV > 80) ve etkilesimleri (ornek: dusuk skor x
yuksek guncel LTV) kendileri bulur; spline / olcekleme gerekmez.

Erken durdurma icin DOGRULAMA kullanilmaz: egitim kredilerinin %10'u (kredi
bazinda) ayrilir. Boylece 2009 dogrulama sonucu logreg ile adil karsilastirilir.
Test bolumune DOKUNMAZ.
"""
import time

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from features import KATEGORIK, MODELLER, OZELLIKLER, yukle
from model_logreg import rapor

PARAMETRELER = dict(
    objective="multiclass",
    num_class=3,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=500,   # nadir olaylar: kucuk yapraklar gurultuyu ezberler
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    n_estimators=3000,       # ust sinir; erken durdurma asil sayiyi belirler
    random_state=42,
    verbose=-1,
)


def kategorileri_ogren(egt):
    """Her kategorik sutunun kategori listesi, yalnizca egitimden."""
    return {c: sorted(egt[c].dropna().unique()) for c in KATEGORIK}


def hazirla(d, kategoriler, ozellikler=OZELLIKLER):
    """Ozellik tablosu; kategorikler egitimdeki kategorilerle sabitlenir
    (egitimde gorulmeyen deger -> eksik)."""
    X = d[ozellikler].copy()
    for c in KATEGORIK:
        if c in ozellikler:
            X[c] = pd.Categorical(X[c], categories=kategoriler[c])
    return X


def kredi_bazli_ayir(d, oran=0.10, tohum=42):
    """Kredileri (aylari degil) ayirir; ayni kredinin aylari ayni tarafta kalir."""
    krediler = d["kredi_id"].unique()
    rng = np.random.default_rng(tohum)
    ayrilan = set(rng.choice(krediler, size=int(len(krediler) * oran), replace=False))
    maske = d["kredi_id"].isin(ayrilan).to_numpy()
    return d[~maske].reset_index(drop=True), d[maske].reset_index(drop=True)


def main():
    veri = yukle(("egitim", "dogrulama"))
    egt, dgr = veri["egitim"], veri["dogrulama"]

    kategoriler = kategorileri_ogren(egt)
    egt_ic, durdurma = kredi_bazli_ayir(egt)
    print(f"egitim: {len(egt_ic):,} satir | erken durdurma: {len(durdurma):,} satir")

    model = lgb.LGBMClassifier(**PARAMETRELER)
    t = time.time()
    model.fit(
        hazirla(egt_ic, kategoriler), egt_ic["y"], sample_weight=egt_ic["agirlik"],
        eval_set=[(hazirla(durdurma, kategoriler), durdurma["y"])],
        eval_sample_weight=[durdurma["agirlik"]],
        callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(200)],
    )
    print(f"egitim suresi: {time.time() - t:.0f} sn | agac sayisi: {model.best_iteration_}")

    for ad, d in [("egitim", egt), ("dogrulama", dgr)]:
        rapor(ad, d, model.predict_proba(hazirla(d, kategoriler)))

    # Ozellik onemi (toplam kazanc, tum siniflar) -- toplulastirilmis, paylasilabilir
    onem = pd.Series(model.booster_.feature_importance("gain"), index=OZELLIKLER)
    print("\nozellik onemi (kazanc payi, ilk 15):")
    print((onem / onem.sum()).sort_values(ascending=False).head(15).round(3).to_string())

    MODELLER.mkdir(exist_ok=True)
    joblib.dump({"model": model, "kategoriler": kategoriler}, MODELLER / "lgbm.joblib")
    print(f"\nmodel kaydedildi: {MODELLER / 'lgbm.joblib'}")


if __name__ == "__main__":
    main()
