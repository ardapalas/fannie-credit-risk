"""Vintage bazinda gercek vs tahmin birikimli batma / erken kapanis egrileri.

Kullanim (proje kok dizininden; modeller ve kalibrasyon once calistirilmis olmali):
    python src/model/vintage.py

Yontem (yarisan riskler, Aalen-Johansen tipi):
  her vintage (kredinin verildigi ceyrek) ve kredi yasi t icin, o ay riskte olan
  satirlarin AGIRLIKLI ortalamasi:
    gercek hazard   h_k(t) = sum w * (y == k) / sum w
    tahmin hazard   h_k(t) = sum w * p_k      / sum w
  birikimli: S(t) = prod (1 - h_1 - h_2),  CIF_k(t) = sum S(t-1) * h_k(t)
Gercek ve tahmin ayni satirlar ve agirliklarla hesaplanir -> birebir karsilastirma.

Veri: DOGRULAMA (2009 kredileri). Kalibrasyon da 2009'da ogrenildigi icin
"kalibre" egrilerin ortalama seviyesi orneklem ici; asil bilgi egrinin SEKLINDE
(yasa ve vintage'a gore sapma). Test bolumune DOKUNMAZ.

Cikti: reports/figures/*.png (toplulastirilmis, paylasilabilir) + tablolar.
"""
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from features import KOK, MODELLER, yukle
from kalibrasyon import uygula
from karsilastir import olasiliklar

SEKILLER = KOK / "reports" / "figures"
MAKS_YAS = 120
OLAYLAR = [(1, "Batma"), (2, "Erken kapanis")]

# Renkler: dataviz referans paleti (acik zemin), kategorik sira sabit
ZEMIN, MUREKKEP, IKINCIL, SOLUK, IZGARA = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
MAVI, TURUNCU, SU = "#2a78d6", "#eb6834", "#1baf7a"


def birikimli(yas, y, w, p=None):
    """Yasa gore birikimli olay oranlari. p verilirse tahmin, yoksa gercek.
    Doner: DataFrame index=yas, sutunlar 1, 2 (CIF)."""
    d = pd.DataFrame({"yas": yas, "w": w})
    for k, _ in OLAYLAR:
        d[k] = w * (p[:, k] if p is not None else (y == k))
    g = d.groupby("yas")[["w", 1, 2]].sum()
    g = g[g.index <= MAKS_YAS]   # yas 0 ve -1 de dahil (ilk aylar)
    h = g[[1, 2]].div(g["w"], axis=0)
    S_once = (1 - h[1] - h[2]).cumprod().shift(1, fill_value=1.0)
    return pd.DataFrame({k: (S_once * h[k]).cumsum() for k, _ in OLAYLAR})


def eksen_stili(ax, ondalik=0):
    ax.set_facecolor(ZEMIN)
    ax.grid(axis="y", color=IZGARA, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=SOLUK, labelsize=8)
    # Isaret araliklari etiketin ondalik sayisiyla temsil edilebilir olsun (0,25% "0,2%" yazmasin)
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=6, steps=[1, 2, 5, 10]))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=ondalik))
    ax.set_xticks(range(0, MAKS_YAS + 1, 24))


def main():
    d = yukle(("dogrulama",))["dogrulama"]
    # yas bos olan birkac satir var (hepsi y=2; build_dataset.py'de bakilacak) -> atilir
    bos = d["yas"].isna()
    print(f"yas bos satir: {bos.sum()} (y degerleri: {d.loc[bos, 'y'].tolist()}) -> atildi")
    d = d[~bos].reset_index(drop=True)
    y, w = d["y"].to_numpy(), d["agirlik"].to_numpy()
    yas = d["yas"].to_numpy().astype(int)
    vintage = d["ceyrek"].astype(str).to_numpy()
    print(f"vintage'lar: {sorted(set(vintage))} | yas araligi: {yas.min()}-{yas.max()}")

    ham = olasiliklar(d)
    kal_kat = joblib.load(MODELLER / "kalibrasyon.joblib")
    kal = {ad: uygula(p, kal_kat[ad]) for ad, p in ham.items()}
    SEKILLER.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]

    # --- Sekil 1: LightGBM, vintage x olay, once / sonra ---
    vintagelar = sorted(set(vintage))
    fig, eksenler = plt.subplots(2, len(vintagelar), figsize=(13, 6), sharex=True,
                                 sharey="row", facecolor=ZEMIN)
    tablo = []
    for j, v in enumerate(vintagelar):
        m = vintage == v
        gercek = birikimli(yas[m], y[m], w[m])
        once = birikimli(yas[m], y[m], w[m], ham["LightGBM"][m])
        sonra = birikimli(yas[m], y[m], w[m], kal["LightGBM"][m])
        for i, (k, olay) in enumerate(OLAYLAR):
            ax = eksenler[i, j]
            eksen_stili(ax, ondalik=1 if k == 1 else 0)
            ax.plot(once.index, once[k], color=TURUNCU, lw=2, ls="--", label="Tahmin (kalibrasyon oncesi)")
            ax.plot(sonra.index, sonra[k], color=MAVI, lw=2, label="Tahmin (kalibrasyon sonrasi)")
            ax.plot(gercek.index, gercek[k], color=MUREKKEP, lw=2, label="Gercek")
            if i == 0:
                ax.set_title(v, color=MUREKKEP, fontsize=10)
            if j == 0:
                ax.set_ylabel(f"Birikimli {olay.lower()}", color=IKINCIL, fontsize=9)
            if i == 1:
                ax.set_xlabel("Kredi yasi (ay)", color=IKINCIL, fontsize=9)
            for t in (36, 60, gercek.index.max()):
                tablo.append({"vintage": v, "olay": olay, "yas": t,
                              "gercek": gercek.loc[t, k], "once": once.loc[t, k],
                              "sonra": sonra.loc[t, k]})
    h, l = eksenler[0, 0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False,
               fontsize=9, labelcolor=IKINCIL)
    fig.tight_layout()
    yol1 = SEKILLER / "vintage_lgbm_2009.png"
    fig.savefig(yol1, dpi=160, bbox_inches="tight", facecolor=ZEMIN)
    plt.close(fig)

    # --- Sekil 2: 2009 tamami, uc model (kalibre) vs gercek ---
    fig, eksenler = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=ZEMIN)
    gercek = birikimli(yas, y, w)
    renkler = {"LightGBM": MAVI, "Sinir agi": TURUNCU, "Lojistik reg.": SU}
    egriler = {ad: birikimli(yas, y, w, kal[ad]) for ad in renkler}
    tablo2 = []
    for ax, (k, olay) in zip(eksenler, OLAYLAR):
        eksen_stili(ax, ondalik=1 if k == 1 else 0)
        for ad, renk in renkler.items():
            ax.plot(egriler[ad].index, egriler[ad][k], color=renk, lw=2, label=ad)
        ax.plot(gercek.index, gercek[k], color=MUREKKEP, lw=2, label="Gercek")
        ax.set_title(f"Birikimli {olay.lower()}", color=MUREKKEP, fontsize=10)
        ax.set_xlabel("Kredi yasi (ay)", color=IKINCIL, fontsize=9)
        for t in (36, 60, gercek.index.max()):
            tablo2.append({"olay": olay, "yas": t, "gercek": gercek.loc[t, k],
                           **{ad: egriler[ad].loc[t, k] for ad in renkler}})
    h, l = eksenler[0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, frameon=False,
               fontsize=9, labelcolor=IKINCIL)
    fig.tight_layout()
    yol2 = SEKILLER / "vintage_modeller_2009.png"
    fig.savefig(yol2, dpi=160, bbox_inches="tight", facecolor=ZEMIN)
    plt.close(fig)

    pd.set_option("display.width", 200)
    print("\nLightGBM, vintage bazinda birikimli oranlar (%):")
    t1 = pd.DataFrame(tablo)
    t1[["gercek", "once", "sonra"]] *= 100
    print(t1.round(2).to_string(index=False))
    print("\n2009 tamami, kalibre modeller (%):")
    t2 = pd.DataFrame(tablo2)
    t2.iloc[:, 2:] *= 100
    print(t2.round(2).to_string(index=False))
    print(f"\nsekiller: {yol1}\n          {yol2}")


if __name__ == "__main__":
    main()
