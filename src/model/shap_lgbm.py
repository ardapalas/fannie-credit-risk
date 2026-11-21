"""SHAP: LightGBM, sadece batma sinifi.

Kullanim (proje kok dizininden; model_lgbm.py ve kalibrasyon.py once calismis olmali):
    python src/model/shap_lgbm.py

- SHAP degerleri LightGBM'in kendi TreeSHAP hesabindan (pred_contrib=True): kesin,
  kategorik sutunlarla uyumlu. Birim: batma sinifinin HAM skoru (softmax logit),
  kalibre olasilik degil. Kontrol: katkilar + taban = ham skor.
- Orneklem: dogrulama (2009) bolumunden ~30 bin satir; batma satirlarinin HEPSI +
  geri kalani rastgele. AGIRLIKSIZ (bkz. notlar.txt): batmalar asiri temsil ediliyor.
- Ciktilar:
    reports/figures/shap_onem_lgbm_batma.png        genel onem (toplulastirilmis)
    reports/figures/shap_bagimlilik_lgbm_batma.png  6 degiskenin bagimlilik grafigi
    reports/figures/yerel/shap_tekil_ornekler.png   3 ornek kredi -- TEKIL KREDI BILGISI
        icerir, lisans geregi git disinda (.gitignore) ve paylasilmaz.
Test bolumune DOKUNMAZ.
"""
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from features import KATEGORIK, KOK, MODELLER, OZELLIKLER, yukle
from kalibrasyon import uygula
from model_lgbm import hazirla

SEKILLER = KOK / "reports" / "figures"
YEREL = SEKILLER / "yerel"
ORNEKLEM = 30_000
ZORUNLU = ["guncel_ltv", "yas", "faiz_farki", "borrower_credit_score_at_origination"]

ZEMIN, MUREKKEP, IKINCIL, SOLUK, IZGARA = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
MAVI, KIRMIZI = "#2a78d6", "#e34948"   # diverging: risk azaltan / arttiran


def stil(ax, izgara="x"):
    ax.set_facecolor(ZEMIN)
    ax.grid(axis=izgara, color=IZGARA, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=SOLUK, labelsize=8)


def orneklem_al(d, rng):
    batma = np.flatnonzero(d["y"].to_numpy() == 1)
    diger = np.flatnonzero(d["y"].to_numpy() != 1)
    secilen = rng.choice(diger, size=ORNEKLEM - len(batma), replace=False)
    return np.sort(np.concatenate([batma, secilen]))


def agirlikli_yuzdelik(x, w, q):
    s = np.argsort(x)
    kum = np.cumsum(w[s]) / w.sum()
    return x[s][np.searchsorted(kum, q)]


def onem_grafigi(onem):
    ust = onem.head(15)[::-1]
    fig, ax = plt.subplots(figsize=(8, 5.5), facecolor=ZEMIN)
    stil(ax)
    ax.barh(ust.index, ust.values, color=MAVI, height=0.6)
    for i, v in enumerate(ust.values):
        ax.text(v, i, f" {v:.3f}", va="center", fontsize=8, color=IKINCIL)
    ax.set_xlabel("Ortalama |SHAP| (batma ham skoru)", color=IKINCIL, fontsize=9)
    ax.tick_params(axis="y", colors=IKINCIL, labelsize=8)
    fig.tight_layout()
    fig.savefig(SEKILLER / "shap_onem_lgbm_batma.png", dpi=160, facecolor=ZEMIN)
    plt.close(fig)


def bagimlilik_grafigi(X, shap, degiskenler):
    fig, eksenler = plt.subplots(2, 3, figsize=(13, 7.5), facecolor=ZEMIN)
    for ax, c in zip(eksenler.flat, degiskenler):
        stil(ax, izgara="y")
        j = OZELLIKLER.index(c)
        s = shap[:, j]
        if c in KATEGORIK:
            # Kategori basina ortalama SHAP (en az 50 satir), en yuksek/dusuk 8'er
            g = pd.DataFrame({"k": X[c].astype(str), "s": s}).groupby("k")["s"].agg(["mean", "size"])
            g = g[g["size"] >= 50].sort_values("mean")
            g = pd.concat([g.head(8), g.tail(8)]).drop_duplicates()
            ax.bar(g.index, g["mean"], color=np.where(g["mean"] > 0, KIRMIZI, MAVI), width=0.7)
            ax.tick_params(axis="x", rotation=90)
            ax.set_xlabel(f"{c} (en dusuk / en yuksek 8)", color=IKINCIL, fontsize=9)
        else:
            x = X[c].to_numpy(dtype=float)
            ok = ~np.isnan(x)
            alt, ust = np.percentile(x[ok], [1, 99])
            ok &= (x >= alt) & (x <= ust)
            ax.scatter(x[ok], s[ok], s=3, alpha=0.12, color=MAVI, linewidths=0)
            # Dilim ortalamasi (20 yuzdelik dilim)
            kenar = np.unique(np.percentile(x[ok], np.linspace(0, 100, 21)))
            idx = np.clip(np.digitize(x[ok], kenar[1:-1]), 0, len(kenar) - 2)
            orta = pd.Series(s[ok]).groupby(idx).mean()
            merkez = pd.Series(x[ok]).groupby(idx).median()
            ax.plot(merkez, orta, color=MUREKKEP, lw=2)
            tekil = np.unique(x[ok])
            if len(tekil) <= 5:   # ayrik degisken: sadece gercek degerler
                ax.set_xticks(tekil)
            ax.set_xlabel(c, color=IKINCIL, fontsize=9)
        ax.axhline(0, color="#c3c2b7", lw=1)
        ax.set_ylabel("SHAP (batma ham skoru)", color=IKINCIL, fontsize=8)
    fig.tight_layout()
    fig.savefig(SEKILLER / "shap_bagimlilik_lgbm_batma.png", dpi=160, facecolor=ZEMIN)
    plt.close(fig)


def tekil_grafik(ornekler, X, shap, taban, p_kal, ort_p):
    fig, eksenler = plt.subplots(1, 3, figsize=(15, 5), facecolor=ZEMIN)
    for ax, (baslik, i) in zip(eksenler, ornekler.items()):
        stil(ax)
        katki = pd.Series(shap[i], index=OZELLIKLER)
        ust = katki.reindex(katki.abs().sort_values(ascending=False).index[:8])
        geri = katki.drop(ust.index).sum()
        etiketler = []
        for c in ust.index:
            v = X.iloc[i][c]
            etiketler.append(f"{c} = {v:.1f}" if isinstance(v, (int, float, np.floating)) and not pd.isna(v)
                             else f"{c} = {v}")
        etiketler.append(f"diger {len(katki) - len(ust)} degisken")
        degerler = list(ust.values) + [geri]
        ax.barh(range(len(degerler))[::-1], degerler, height=0.6,
                color=[KIRMIZI if v > 0 else MAVI for v in degerler])
        ax.set_yticks(range(len(degerler))[::-1], etiketler, fontsize=8, color=IKINCIL)
        ax.axvline(0, color="#c3c2b7", lw=1)
        ax.set_title(f"{baslik}\naylik kalibre batma olasiligi %{100 * p_kal[i]:.3f}\n"
                     f"(2009 ortalamasi %{100 * ort_p:.3f})", color=MUREKKEP, fontsize=9)
        ax.set_xlabel(f"SHAP katkisi (taban {taban:.2f})", color=IKINCIL, fontsize=8)
    fig.tight_layout()
    YEREL.mkdir(parents=True, exist_ok=True)
    fig.savefig(YEREL / "shap_tekil_ornekler.png", dpi=160, facecolor=ZEMIN)
    plt.close(fig)


def main():
    rng = np.random.default_rng(42)
    d = yukle(("dogrulama",))["dogrulama"]
    lg = joblib.load(MODELLER / "lgbm.joblib")
    model, kategoriler = lg["model"], lg["kategoriler"]
    kal = joblib.load(MODELLER / "kalibrasyon.joblib")["LightGBM"]

    # Kalibre batma olasiligi: tum dogrulama (esik ve ortalama icin) -- agirlikli
    w = d["agirlik"].to_numpy()
    p_tum = uygula(model.predict_proba(hazirla(d, kategoriler)), kal)[:, 1]
    ort_p = np.average(p_tum, weights=w)
    esik_10 = agirlikli_yuzdelik(p_tum, w, 0.90)   # en riskli %10'un siniri
    dusuk_5 = agirlikli_yuzdelik(p_tum, w, 0.05)

    idx = orneklem_al(d, rng)
    o = d.iloc[idx].reset_index(drop=True)
    p_kal = p_tum[idx]
    X = hazirla(o, kategoriler)
    print(f"orneklem: {len(o):,} satir | batma {int((o['y'] == 1).sum()):,} "
          f"| erken {int((o['y'] == 2).sum()):,} | devam {int((o['y'] == 0).sum()):,}")

    F = len(OZELLIKLER)
    katki = model.booster_.predict(X, pred_contrib=True).reshape(len(X), 3, F + 1)
    shap, taban = katki[:, 1, :F], katki[0, 1, F]
    ham = model.booster_.predict(X, raw_score=True)[:, 1]
    assert np.allclose(shap.sum(1) + katki[:, 1, F], ham, atol=1e-6), "SHAP toplami ham skora esit degil"
    print("kontrol gecti: SHAP katkilari + taban = ham skor")

    onem = pd.Series(np.abs(shap).mean(0), index=OZELLIKLER).sort_values(ascending=False)
    print("\nortalama |SHAP|, ilk 15:\n" + onem.head(15).round(4).to_string())
    onem_grafigi(onem)

    digerleri = [c for c in onem.index if c not in ZORUNLU][:2]
    bagimlilik_grafigi(X, shap, ZORUNLU + digerleri)
    print(f"\nbagimlilik grafikleri: {ZORUNLU + digerleri}")

    # 3 ornek: farkli krediler, toplulastirilmis olcutlerle secilir
    y = o["y"].to_numpy()
    batmis = np.flatnonzero(y == 1)
    b = batmis[np.argmin(np.abs(p_kal[batmis] - np.median(p_kal[batmis])))]
    adaylar = np.flatnonzero((y == 0) & (o["kredi_id"] != o["kredi_id"][b]).to_numpy())
    dsk = adaylar[np.argmin(np.abs(p_kal[adaylar] - dusuk_5))]
    adaylar = adaylar[(o["kredi_id"].to_numpy()[adaylar] != o["kredi_id"][dsk])]
    snr = adaylar[np.argmin(np.abs(p_kal[adaylar] - esik_10))]
    ornekler = {"Batmis kredi (battigi ay)": b,
                "Dusuk riskli (en dusuk %5 siniri)": dsk,
                "Sinirda (en riskli %10 esigi)": snr}
    tekil_grafik(ornekler, X, shap, taban, p_kal, ort_p)
    for ad, i in ornekler.items():
        print(f"{ad}: kalibre p = %{100 * p_kal[i]:.3f}")

    print(f"\nsekiller: {SEKILLER / 'shap_onem_lgbm_batma.png'}\n"
          f"          {SEKILLER / 'shap_bagimlilik_lgbm_batma.png'}\n"
          f"          {YEREL / 'shap_tekil_ornekler.png'}  (yerel, git disi)")


if __name__ == "__main__":
    main()
