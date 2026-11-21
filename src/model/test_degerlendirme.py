"""TEST degerlendirmesi -- test 2026-11-21'de BIR KEZ acildi. Hicbir model veya ayar degismez.

Kullanim (proje kok dizininden):
    python src/model/test_degerlendirme.py --deneme   # sadece dogrulama, cikti scratchpad'e (test KAPALI)
    python src/model/test_degerlendirme.py --dizin D  # deneme ciktilarinin yazilacagi dizin
    python src/model/test_degerlendirme.py            # ASIL: test (dondurulmus modeller)
    python src/model/test_degerlendirme.py --cizim    # model CALISTIRMADAN kayitli egrilerden ciz

Uc model (logreg, LightGBM, sinir agi), kalibrasyon oncesi ve sonrasi (kalibrasyon 2009'da
ogrenilmis haliyle, DEGISTIRILMEDEN): log loss, AUC, Gini, tahmin/gercek, yakalama orani.
Dogrulama ve test yan yana. Kusak bazinda vintage egrileri (vintage.py'deki formul).
Cikti: reports/tables/test_sonuclari.csv, test_vintage_ceyrek.csv, test_vintage_egriler.csv
       (toplulastirilmis egri verisi -> --cizim ile model calistirmadan yeniden cizilir),
       reports/figures/test_vintage_lgbm.png, test_vintage_modeller.png,
       data/processed/test_tahminleri.parquet (satir bazinda tahminler; lisans geregi git disi)

2026-11-22: ikinci calistirma SADECE eksen etiketi duzeltmesi icin (notlar.txt); modeller ayni.
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
RENKLER = {"LightGBM": MAVI, "Sinir agi": TURUNCU, "Lojistik reg.": SU}
KISA = {"LightGBM": "lgbm", "Sinir agi": "nn", "Lojistik reg.": "logreg"}


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


def egriler_hesapla(d, ham, kal):
    """Cizim icin TOPLULASTIRILMIS egri verisi (uzun bicim): panel, seri, olay, yas, deger.
    panel = 'yil:2010' gibi kusak yili veya 'tum'. Kredi bazinda bilgi icermez."""
    y, w = d["y"].to_numpy(), d["agirlik"].to_numpy()
    yas = d["yas"].to_numpy().astype(int)
    yil = d["ceyrek"].astype(str).str[:4].to_numpy()
    parcalar = []

    def ekle(panel, seri, e):
        for k, _ in OLAYLAR:
            parcalar.append(pd.DataFrame({"panel": panel, "seri": seri, "olay": k,
                                          "yas": e.index, "deger": e[k].to_numpy()}))

    for v in sorted(set(yil)):
        m = yil == v
        ekle(f"yil:{v}", "gercek", birikimli(yas[m], y[m], w[m]))
        ekle(f"yil:{v}", "lgbm_once", birikimli(yas[m], y[m], w[m], ham["LightGBM"][m]))
        ekle(f"yil:{v}", "lgbm_sonra", birikimli(yas[m], y[m], w[m], kal["LightGBM"][m]))
    ekle("tum", "gercek", birikimli(yas, y, w))
    for ad in RENKLER:
        ekle("tum", ad, birikimli(yas, y, w, kal[ad]))
    return pd.concat(parcalar, ignore_index=True)


def egrileri_ciz(egr, dizin, onek):
    """Kaydedilmis egri verisinden cizer (model calistirmaz)."""
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]

    def seri(panel, ad, k):
        e = egr[(egr["panel"] == panel) & (egr["seri"] == ad) & (egr["olay"] == k)]
        return e["yas"].to_numpy(), e["deger"].to_numpy()

    # Sekil 1: LightGBM, kusak yili x olay
    yillar = sorted(p for p in egr["panel"].unique() if p.startswith("yil:"))
    fig, eksenler = plt.subplots(2, len(yillar), figsize=(4.2 * len(yillar) + 1, 6), sharex=True,
                                 sharey="row", facecolor=ZEMIN, squeeze=False)
    for j, panel in enumerate(yillar):
        for i, (k, olay) in enumerate(OLAYLAR):
            ax = eksenler[i, j]
            eksen_stili(ax, ondalik=1 if k == 1 else 0)
            ax.plot(*seri(panel, "lgbm_once", k), color=TURUNCU, lw=2, ls="--",
                    label="Tahmin (kalibrasyon oncesi)")
            ax.plot(*seri(panel, "lgbm_sonra", k), color=MAVI, lw=2, label="Tahmin (kalibrasyon sonrasi)")
            ax.plot(*seri(panel, "gercek", k), color=MUREKKEP, lw=2, label="Gercek")
            if i == 0:
                ax.set_title(f"{panel[4:]} kusagi", color=MUREKKEP, fontsize=10)
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
    for ax, (k, olay) in zip(eksenler, OLAYLAR):
        eksen_stili(ax, ondalik=1 if k == 1 else 0)
        for ad, renk in RENKLER.items():
            ax.plot(*seri("tum", ad, k), color=renk, lw=2, label=ad)
        ax.plot(*seri("tum", "gercek", k), color=MUREKKEP, lw=2, label="Gercek")
        ax.set_title(f"Birikimli {olay.lower()}", color=MUREKKEP, fontsize=10)
        ax.set_xlabel("Kredi yasi (ay)", color=IKINCIL, fontsize=9)
    h, l = eksenler[0].get_legend_handles_labels()
    fig.legend(h[::-1], l[::-1], loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4,
               frameon=False, fontsize=9, labelcolor=IKINCIL)
    fig.tight_layout()
    fig.savefig(dizin / f"{onek}_vintage_modeller.png", dpi=160, bbox_inches="tight", facecolor=ZEMIN)
    plt.close(fig)


def ceyrek_tablosu(d, kal):
    """Ceyrek bazinda: LightGBM kalibre vs gercek, 24/36/60. ay (varsa)."""
    y, w = d["y"].to_numpy(), d["agirlik"].to_numpy()
    yas = d["yas"].to_numpy().astype(int)
    ceyrek = d["ceyrek"].astype(str).to_numpy()
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


def tahminleri_kaydet(sonuclar, yol):
    """Satir bazinda tahminler (KREDI-AY satirlari -> lisans geregi data/ altinda, git disi).
    Bir daha metrik/cizim gerekirse model calistirmadan buradan uretilir."""
    parcalar = []
    for bolum, (d, ham, kal) in sonuclar.items():
        t = d[["kredi_id", "ay", "ceyrek", "yas", "y", "agirlik"]].copy()
        t["bolum"] = bolum
        for ad in ham:
            for durum, p in (("ham", ham[ad]), ("kal", kal[ad])):
                for k, olay in ((1, "batma"), (2, "erken")):
                    t[f"{KISA[ad]}_{durum}_{olay}"] = p[:, k]
        parcalar.append(t)
    pd.concat(parcalar, ignore_index=True).to_parquet(yol, index=False)


def main():
    if "--cizim" in sys.argv:
        # Model CALISTIRMADAN, kayitli egri verisinden yeniden ciz
        egr = pd.read_csv(KOK / "reports" / "tables" / "test_vintage_egriler.csv")
        egrileri_ciz(egr, KOK / "reports" / "figures", "test")
        print("kayitli egri verisinden cizildi (model calistirilmadi)")
        return
    deneme = "--deneme" in sys.argv
    if deneme:
        i = sys.argv.index("--dizin") if "--dizin" in sys.argv else None
        dizin_s = dizin_t = Path(sys.argv[i + 1]) if i else Path.cwd() / "deneme_cikti"
        bolumler = ("dogrulama",)
        print("DENEME MODU: sadece dogrulama, test KAPALI")
    else:
        dizin_s, dizin_t = KOK / "reports" / "figures", KOK / "reports" / "tables"
        bolumler = ("dogrulama", "test")
        print("ASIL MOD: test bolumu, dondurulmus modellerle")
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
    egr = egriler_hesapla(d, ham, kal)
    egr.to_csv(dizin_t / f"{onek}_vintage_egriler.csv", index=False)
    egrileri_ciz(egr, dizin_s, onek)
    vt = ceyrek_tablosu(d, kal)
    print(f"\n{hedef}: kusak bazinda birikimli % (LightGBM kalibre vs gercek)\n"
          + vt.pivot_table(index="kusak", columns=["olay", "yas"], values=["gercek", "lgbm_kalibre"])
              .swaplevel(0, 2, axis=1).sort_index(axis=1).round(2).to_string())
    vt.to_csv(dizin_t / f"{onek}_vintage_ceyrek.csv", index=False)
    if not deneme:
        yol = KOK / "data" / "processed" / "test_tahminleri.parquet"
        tahminleri_kaydet(sonuclar, yol)
        print(f"satir bazinda tahminler (git disi): {yol}")
    print(f"\nciktilar: {dizin_s}, {dizin_t}")


if __name__ == "__main__":
    main()
