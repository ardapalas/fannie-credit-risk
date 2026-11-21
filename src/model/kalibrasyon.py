"""Kalibrasyon: olay basina Platt olcekleme (uc model icin).

Kullanim (proje kok dizininden, modeller once egitilmis olmali):
    python src/model/kalibrasyon.py

Her model ve her olay (k = 1 batti, 2 erken kapatti) icin ayri:
    q_k = sigmoid(a_k * logit(p_k) + b_k)
    q_0 = 1 - q_1 - q_2   (devam)
a_k, b_k: hedef (y == k), girdi logit(p_k) olan tek degiskenli AGIRLIKLI lojistik
regresyon; DOGRULAMA (2009) bolumunun tamaminda ogrenilir. Model basina 4 parametre.

Dogrulamadaki "sonra" degerleri bu yuzden orneklem ici (iyimser); kalibrasyonun
gercek degerlendirmesi en sonda test bolumunde yapilacak. Test bolumune DOKUNMAZ.

Kontroller: a_k > 0 olmali (donusum monoton -> AUC degismez); q_1 + q_2 < 1 olmali.
"""
import joblib
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.linear_model import LogisticRegression

from features import MODELLER, yukle
from karsilastir import OLAYLAR, metrikler, olasiliklar

EPS = 1e-12


def ogren(p, y, w):
    """Her olay icin (a, b) katsayilari."""
    # Agirliklar ortalamaya bolunur: katsayilari degistirmez ama toplam ~6,5 milyon
    # olunca lbfgs erken "yakinsadim" diyordu (orneklem ici t/g 1,00 yerine 1,02 cikiyordu).
    w = w / w.mean()
    katsayilar = {}
    for k, _ in OLAYLAR:
        x = logit(np.clip(p[:, k], EPS, 1 - EPS)).reshape(-1, 1)
        lr = LogisticRegression(C=1e10, tol=1e-10, max_iter=10000).fit(
            x, y == k, sample_weight=w)
        katsayilar[k] = (float(lr.coef_[0, 0]), float(lr.intercept_[0]))
    return katsayilar


def uygula(p, katsayilar):
    """Kalibre edilmis (n, 3) olasilik matrisi."""
    q = np.empty_like(p)
    for k, (a, b) in katsayilar.items():
        q[:, k] = expit(a * logit(np.clip(p[:, k], EPS, 1 - EPS)) + b)
    q[:, 0] = 1 - q[:, 1] - q[:, 2]
    return q


def main():
    d = yukle(("dogrulama",))["dogrulama"]
    y, w = d["y"].to_numpy(), d["agirlik"].to_numpy()

    satirlar, kalibratorler = [], {}
    for ad, p in olasiliklar(d).items():
        kat = ogren(p, y, w)
        for k, olay in OLAYLAR:
            a, b = kat[k]
            print(f"{ad:14s} {olay:6s} a = {a:.3f}  b = {b:+.3f}")
            assert a > 0, f"{ad} {olay}: a <= 0, donusum monoton degil"
        q = uygula(p, kat)
        assert (q[:, 0] > 0).all(), f"{ad}: q_batma + q_erken >= 1 olan satir var"

        once, sonra = metrikler(d, p), metrikler(d, q)
        for k, olay in OLAYLAR:
            assert abs(once[f"{olay}_auc"] - sonra[f"{olay}_auc"]) < 1e-9, \
                f"{ad} {olay}: AUC degisti -> hata"
        for a in once:
            if a.startswith("batma_yakala"):
                assert abs(once[a] - sonra[a]) < 1e-9, f"{ad} {a}: yakalama degisti -> hata"
        satirlar += [{"model": ad, "": "once", **once}, {"model": ad, "": "sonra", **sonra}]
        kalibratorler[ad] = kat

    print("\n" + pd.DataFrame(satirlar).round(4).to_string(index=False))
    print("\nkontroller gecti: a > 0, q_1 + q_2 < 1, AUC ve yakalama oranlari degismedi")

    joblib.dump(kalibratorler, MODELLER / "kalibrasyon.joblib")
    print(f"kalibratorler kaydedildi: {MODELLER / 'kalibrasyon.joblib'}")


if __name__ == "__main__":
    main()
