"""Kaydedilmis modelleri dogrulama bolumunde ayni metriklerle karsilastirir.

Kullanim (proje kok dizininden, modeller once egitilmis olmali):
    python src/model/karsilastir.py

Metrikler agirlikli: log loss, batma / erken kapanis AUC, ve tahmin/gercek oran
(ortalama tahmin edilen aylik oran / gercek aylik oran; 1 = dogru kalibre).
Test bolumune DOKUNMAZ.
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from features import MODELLER, OZELLIKLER, yukle
from model_lgbm import hazirla

OLAYLAR = [(1, "batma"), (2, "erken")]


def olasiliklar(d):
    """Her model icin (n, 3) olasilik matrisi."""
    lg = joblib.load(MODELLER / "lgbm.joblib")
    return {
        "Lojistik reg.": joblib.load(MODELLER / "logreg.joblib").predict_proba(d[OZELLIKLER]),
        "LightGBM": lg["model"].predict_proba(hazirla(d, lg["kategoriler"])),
        "Sinir agi": joblib.load(MODELLER / "nn.joblib").predict_proba(d[OZELLIKLER]),
    }


DILIMLER = (5, 10, 20)   # yakalama orani icin en riskli dilimler (%)


def yakalama(olay, skor, w, dilimler=DILIMLER):
    """En riskli %x'lik dilimin (agirlikli nufusa gore) gercek olaylarin yuzde kacini
    (agirlikli) icerdigi. Kredi-ay duzeyinde: dilim = en yuksek skorlu satirlar."""
    sira = np.argsort(-skor, kind="stable")
    w_s, olay_s = w[sira], olay[sira]
    nufus_payi = np.cumsum(w_s) / w_s.sum()
    sonuc = {}
    for x in dilimler:
        dilimde = nufus_payi <= x / 100
        sonuc[f"yakala_{x}"] = (w_s[dilimde] * olay_s[dilimde]).sum() / (w_s * olay_s).sum()
    return sonuc


def metrikler(d, p):
    y, w = d["y"].to_numpy(), d["agirlik"].to_numpy()
    s = {"log_loss": log_loss(y, p, sample_weight=w, labels=[0, 1, 2])}
    for k, olay in OLAYLAR:
        auc = roc_auc_score(y == k, p[:, k], sample_weight=w)
        s[f"{olay}_auc"] = auc
        s[f"{olay}_gini"] = 2 * auc - 1
        s[f"{olay}_t/g"] = np.average(p[:, k], weights=w) / np.average(y == k, weights=w)
    # Yakalama orani: sadece batma (kredi riski acisindan asil soru)
    s.update({f"batma_{a}": v for a, v in yakalama((y == 1).astype(float), p[:, 1], w).items()})
    return s


def main():
    d = yukle(("dogrulama",))["dogrulama"]
    tablo = pd.DataFrame(
        [{"model": ad, **metrikler(d, p)} for ad, p in olasiliklar(d).items()])
    # Genis tablo: modeller sutunda okunur
    print(tablo.set_index("model").T.round(4).to_string())


if __name__ == "__main__":
    main()
