"""Sinir agi: 2 gizli katmanli MLP (64, 32), cok sinifli cikti (devam / batti / erken kapatti).

Kullanim (proje kok dizininden):
    python src/model/model_nn.py

On isleme lojistik regresyonla ayni (onisleyici_dogrusal: yas spline, olcekleme, one-hot).
Ornekleme agirliklari kayip fonksiyonuna girer (sklearn MLPClassifier sample_weight).

Erken durdurma: sklearn'un kendi early_stopping'i satir bazinda rastgele ayirir ve
agirliksiz dogruluga bakar -- bize uymaz. Bunun yerine partial_fit ile epoch epoch
egitilir; her epoch sonunda egitim kredilerinden ayrilan %10'da (kredi bazinda,
LightGBM ile ayni kume) AGIRLIKLI log loss olculur, en iyi epoch saklanir.
Test bolumune DOKUNMAZ.
"""
import copy
import time

import joblib
import numpy as np
from scipy import sparse
from sklearn.metrics import log_loss
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

from features import MODELLER, OZELLIKLER, onisleyici_dogrusal, yukle
from model_lgbm import kredi_bazli_ayir
from model_logreg import rapor

MAKS_EPOCH = 60
SABIR = 5   # bu kadar epoch iyilesme olmazsa dur


def yogun(X):
    return X.toarray() if sparse.issparse(X) else np.asarray(X)


def main():
    veri = yukle(("egitim", "dogrulama"))
    egt, dgr = veri["egitim"], veri["dogrulama"]
    egt_ic, durdurma = kredi_bazli_ayir(egt)
    print(f"egitim: {len(egt_ic):,} satir | erken durdurma: {len(durdurma):,} satir")

    # Ortanca / olcekleme / kategoriler yalnizca egitim kisminda ogrenilir
    on = onisleyici_dogrusal().fit(egt_ic[OZELLIKLER])
    X = yogun(on.transform(egt_ic[OZELLIKLER]))
    y, w = egt_ic["y"].to_numpy(), egt_ic["agirlik"].to_numpy()
    Xd = yogun(on.transform(durdurma[OZELLIKLER]))
    yd, wd = durdurma["y"].to_numpy(), durdurma["agirlik"].to_numpy()
    print(f"girdi boyutu: {X.shape[1]}")

    mlp = MLPClassifier(
        hidden_layer_sizes=(64, 32), activation="relu", solver="adam",
        learning_rate_init=1e-3, batch_size=1024, alpha=1e-4, random_state=42,
    )
    en_iyi, en_iyi_kayip, en_iyi_epoch = None, np.inf, 0
    t = time.time()
    for epoch in range(1, MAKS_EPOCH + 1):
        mlp.partial_fit(X, y, sample_weight=w, classes=[0, 1, 2])
        kayip = log_loss(yd, mlp.predict_proba(Xd), sample_weight=wd, labels=[0, 1, 2])
        isaret = ""
        if kayip < en_iyi_kayip:
            en_iyi, en_iyi_kayip, en_iyi_epoch = copy.deepcopy(mlp), kayip, epoch
            isaret = " *"
        print(f"epoch {epoch:2d}  durdurma log loss {kayip:.5f}{isaret}", flush=True)
        if epoch - en_iyi_epoch >= SABIR:
            break
    print(f"egitim suresi: {time.time() - t:.0f} sn | en iyi epoch: {en_iyi_epoch}")

    model = Pipeline([("onisleme", on), ("mlp", en_iyi)])
    for ad, d in [("egitim", egt), ("dogrulama", dgr)]:
        rapor(ad, d, model.predict_proba(d[OZELLIKLER]))

    MODELLER.mkdir(exist_ok=True)
    joblib.dump(model, MODELLER / "nn.joblib")
    print(f"\nmodel kaydedildi: {MODELLER / 'nn.joblib'}")


if __name__ == "__main__":
    main()
