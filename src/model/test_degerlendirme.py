"""TEST degerlendirmesi -- BIR KEZ calistirilir. Bundan sonra hicbir model veya ayar degismez.

Kullanim (proje kok dizininden):
    python src/model/test_degerlendirme.py --deneme   # sadece dogrulama, cikti scratchpad'e (test KAPALI)
    python src/model/test_degerlendirme.py --dizin D  # deneme ciktilarinin yazilacagi dizin
    python src/model/test_degerlendirme.py            # ASIL: test acilir

Uc model (logreg, LightGBM, sinir agi), kalibrasyon oncesi ve sonrasi (kalibrasyon 2009'da
ogrenilmis haliyle, DEGISTIRILMEDEN): log loss, AUC, Gini, tahmin/gercek, yakalama orani.
Dogrulama ve test yan yana. Kusak bazinda vintage egrileri (vintage.py'deki formul).
Cikti: reports/tables/test_sonuclari.csv, test_vintage_ceyrek.csv,
       reports/figures/test_vintage_lgbm.png, test_vintage_modeller.png
"""
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from features import KOK, MODELLER, yukle
from kalibrasyon import uygula
from karsilastir import metrikler, olasiliklar
from vintage import (IKINCIL, MAVI, MUREKKEP, OLAYLAR, SU, TURUNCU, ZEMIN, birikimli,
                     eksen_stili)

METRIK_SIRASI = ["log_loss", "batma_auc", "batma_gini", "batma_t/g", "erken_auc", "erken_gini",
                 "erken_t/g", "batma_yakala_5", "batma_yakala_10", "batma_yakala_20"]


def olasiliklar_ve_kalibre(d, kal_kat):
    ham = olasiliklar(d)
    return ham, {ad: uygula(p, kal_kat[ad]) for ad, p in ham.items()}


def metrik_tablosu(sonuclar):
    """sonuclar: {bolum: (d, ham, kal)} -> satir: (metrik, model), sutun: (bolum, durum)."""
    kayit = []
    for bolum, (d, ham, kal) in sonuclar.items():
        for ad in ham:
            for durum, p in (("once", ham[ad]), ("sonra", kal[ad])):
                for metrik, v in metrikler(d, p).items():
                    kayit.append({"metrik": metrik, "model": ad, "bolum": bolum, "durum": durum, "deger": v})
    t = pd.DataFrame(kayit).pivot_table(index=["metrik", "model"], columns=["durum", "bolum"],
                                        values="deger")
    t = t.reindex(METRIK_SIRASI, level=0)
    sutunlar = [(du, b) for du in ("once", "sonra") for b in sonuclar]
    return t[sutunlar]


def vintage_grafikleri(d, ham, kal, dizin, onek):
    y, w = d["y"].to_numpy(), d["agirlik"].to_numpy()
    yas = d["yas"].to_numpy().astype(int)
    yil = d["ceyrek"].astype(str).str[:4].to_numpy()
    ceyrek = d["ceyrek"].astype(str).to_numpy()
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]

    # Sekil 1: LightGBM, kusak yili x olay
    yillar = sorted(set(yil))
    fig, eksenler = plt.subplots(2, len(yillar), figsize=(4.2 * len(yillar) + 1, 6), sharex=True,
                                 sharey="row", facecolor=ZEMIN, squeeze=False)
    for j, v in enumerate(yillar):
        m = yil == v
        g = birikimli(yas[m], y[m], w[m])
        o = birikimli(yas[m], y[m], w[m], ham["LightGBM"][m])
        s = birikimli(yas[m], y[m], w[m], kal["LightGBM"][m])
        for i, (k, olay) in enumerate(OLAYLAR):
            ax = eksenler[i, j]
            eksen_stili(ax, ondalik=1 if k == 1 else 0)
            ax.plot(o.index, o[k], color=TURUNCU, lw=2, ls="--", label="Tahmin (kalibrasyon oncesi)")
            ax.plot(s.index, s[k], color=MAVI, lw=2, label="Tahmin (kalibrasyon sonrasi)")
            ax.plot(g.index, g[k], color=MUREKKEP, lw=2, label="Gercek")
            if i == 0:
                ax.set_title(f"{v} kusagi", color=MUREKKEP, fontsize=10)
            if j == 0:
                ax.set_ylabel(f"Birikimli {olay.lower()}", color=IKINCIL, fontsize=9)
            if i == 1:
                ax.set_xlabel("Kredi yasi (ay)", color=IKINCIL, fontsize=9)
    h, l = eksenler[0, 0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
               frameon=False, fontsize=9, labelcolor=IKINCIL)
    fig.tight_layout()
    fig.savefig(dizin / f"{onek}_vintage_lgbm.png", dpi=160, bbox_inches="tight", facecolor=ZEMIN)
    plt.close(fig)

    # Sekil 2: tum bolum, uc kalibre model vs gercek
    fig, eksenler = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=ZEMIN)
    g = birikimli(yas, y, w)
    renkler = {"LightGBM": MAVI, "Sinir agi": TURUNCU, "Lojistik reg.": SU}
    for ax, (k, olay) in zip(eksenler, OLAYLAR):
        eksen_stili(ax, ondalik=1 if k == 1 else 0)
        for ad, renk in renkler.items():
            e = birikimli(yas, y, w, kal[ad])
            ax.plot(e.index, e[k], color=renk, lw=2, label=ad)
        ax.plot(g.index, g[k], color=MUREKKEP, lw=2, label="Gercek")
        ax.set_title(f"Birikimli {olay.lower()}", color=MUREKKEP, fontsize=10)
        ax.set_xlabel("Kredi yasi (ay)", color=IKINCIL, fontsize=9)
    h, l = eksenler[0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4,
               frameon=False, fontsize=9, labelcolor=IKINCIL)
    fig.tight_layout()
    fig.savefig(dizin / f"{onek}_vintage_modeller.png", dpi=160, bbox_inches="tight", facecolor=ZEMIN)
    plt.close(fig)

    # Ceyrek bazinda tablo: LightGBM kalibre vs gercek, 24/36/60. ay (varsa)
    satirlar = []
    for v in sorted(set(ceyrek)):
        m = ceyrek == v
        g = birikimli(yas[m], y[m], w[m])
        s = birikimli(yas[m], y[m], w[m], kal["LightGBM"][m])
        for k, olay in OLAYLAR:
            for t in (24, 36, 60):
                if t in g.index:
                    satirlar.append({"kusak": v, "olay": olay, "yas": t,
                                     "gercek": 100 * g.loc[t, k], "lgbm_kalibre": 100 * s.loc[t, k]})
    return pd.DataFrame(satirlar)


def main():
    deneme = "--deneme" in sys.argv
    if deneme:
        i = sys.argv.index("--dizin") if "--dizin" in sys.argv else None
        dizin_s = dizin_t = Path(sys.argv[i + 1]) if i else Path.cwd() / "deneme_cikti"
        bolumler = ("dogrulama",)
        print("DENEME MODU: sadece dogrulama, test KAPALI")
    else:
        dizin_s, dizin_t = KOK / "reports" / "figures", KOK / "reports" / "tables"
        bolumler = ("dogrulama", "test")
        print("ASIL MOD: test bolumu aciliyor (bir kez)")
    dizin_s.mkdir(parents=True, exist_ok=True)
    dizin_t.mkdir(parents=True, exist_ok=True)

    veri = yukle(bolumler)
    kal_kat = joblib.load(MODELLER / "kalibrasyon.joblib")   # 2009'da ogrenilmis, degismedi
    sonuclar = {}
    for b in bolumler:
        d = veri[b]
        assert d["yas"].notna().all() and (d["yas"] >= 0).all(), f"{b}: yas bos/negatif"
        ham, kal = olasiliklar_ve_kalibre(d, kal_kat)
        sonuclar[b] = (d, ham, kal)
        print(f"{b}: {len(d):,} satir, batma {int((d['y'] == 1).sum()):,}, erken {int((d['y'] == 2).sum()):,}")

    tablo = metrik_tablosu(sonuclar)
    pd.set_option("display.width", 220)
    print("\n" + tablo.round(4).to_string())
    tablo.to_csv(dizin_t / "test_sonuclari.csv")

    hedef = bolumler[-1]
    onek = "test" if hedef == "test" else "deneme"
    d, ham, kal = sonuclar[hedef]
    vt = vintage_grafikleri(d, ham, kal, dizin_s, onek)
    print(f"\n{hedef}: kusak bazinda birikimli % (LightGBM kalibre vs gercek)\n"
          + vt.pivot_table(index="kusak", columns=["olay", "yas"], values=["gercek", "lgbm_kalibre"])
              .swaplevel(0, 2, axis=1).sort_index(axis=1).round(2).to_string())
    vt.to_csv(dizin_t / f"{onek}_vintage_ceyrek.csv", index=False)
    print(f"\nciktilar: {dizin_s}, {dizin_t}")


if __name__ == "__main__":
    main()
