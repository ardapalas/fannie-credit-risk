"""Temel model: cok sinifli lojistik regresyon (devam / batti / erken kapatti).

Kullanim (proje kok dizininden):
    python src/train_logreg.py

Egitim bolumunde egitir, egitim ve dogrulama bolumlerinde sonuclari basar,
modeli models/logreg.joblib olarak kaydeder. Test bolumune DOKUNMAZ;
o, butun modeller bittikten sonra bir kez kullanilacak.
"""
import time

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.pipeline import Pipeline

from features import MODELLER, OZELLIKLER, onisleyici_dogrusal, yukle

OLAYLAR = [(1, "batti"), (2, "erken_kapatti")]


def rapor(ad, d, p):
    """Agirlikli metrikleri basar. p: (n, 3) olasilik matrisi."""
    y, w = d["y"].to_numpy(), d["agirlik"].to_numpy()
    print(f"\n--- {ad} ({len(d):,} satir) ---")
    print(f"log loss: {log_loss(y, p, sample_weight=w, labels=[0, 1, 2]):.5f}")
    for k, olay in OLAYLAR:
        auc = roc_auc_score(y == k, p[:, k], sample_weight=w)
        gercek = np.average(y == k, weights=w)
        tahmin = np.average(p[:, k], weights=w)
        print(f"{olay:14s} AUC {auc:.3f} | aylik oran  gercek {gercek:.5f}  tahmin {tahmin:.5f}")

    # Karsilastirma noktasi: sadece kredi skoruna bakan "model"
    skor = d["borrower_credit_score_at_origination"]
    skor = skor.fillna(skor.median())
    print(f"karsilastirma: sadece kredi skoru ile batti AUC "
          f"{roc_auc_score(y == 1, -skor, sample_weight=w):.3f}")


def main():
    veri = yukle(("egitim", "dogrulama"))
    egt, dgr = veri["egitim"], veri["dogrulama"]

    model = Pipeline([
        ("onisleme", onisleyici_dogrusal()),
        ("lr", LogisticRegression(max_iter=1000)),
    ])

    t = time.time()
    model.fit(egt[OZELLIKLER], egt["y"], lr__sample_weight=egt["agirlik"])
    print(f"egitim suresi: {time.time() - t:.0f} sn")

    for ad, d in [("egitim", egt), ("dogrulama", dgr)]:
        rapor(ad, d, model.predict_proba(d[OZELLIKLER]))

    MODELLER.mkdir(exist_ok=True)
    joblib.dump(model, MODELLER / "logreg.joblib")
    print(f"\nmodel kaydedildi: {MODELLER / 'logreg.joblib'}")


if __name__ == "__main__":
    main()