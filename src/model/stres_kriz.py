"""Kriz karsilastirmasi, GERCEKLESEN sokla: 2006-2007 kusaklari, Ocak 2008'de acik krediler.

Kullanim (proje kok dizininden):
    python src/model/stres_kriz.py

Sok, bu portfoyun 36 aylik pencerede gercekte yasadigi makro degisim:
  issizlik +4,4 puan, ev fiyati -%16 (portfoyun eyalet dagilimiyla, stres.py ciktisi),
  30y faiz: makro tablosundan Ocak 2008 -> Ocak 2011 farki (-1,0 puan).
Gecis suresi 24 ve 30 ay (gercek krizde soklar 2-3 yila yayildi).
Test kusaklarina DOKUNMAZ.
"""
import pandas as pd

from stres import (ISLENMIS, TABLOLAR, gerceklesen, model_yukle, ozet, portfoy_yukle,
                   senaryo_calistir, SENARYOLAR)

T, B, S = "2008-01-01", 2006, 2007
ISSIZLIK, EV_FIYATI = 4.4, -0.16


def main():
    mk = pd.read_parquet(ISLENMIS / "makro.parquet")
    mk["ay"] = pd.to_datetime(mk["ay"])
    f = mk.drop_duplicates("ay").set_index("ay")["faiz_30y"]
    faiz = round(float(f["2011-01-01"] - f["2008-01-01"]), 2)
    print(f"gerceklesen sok: issizlik +{ISSIZLIK}, ev fiyati {100 * EV_FIYATI:.0f}%, faiz {faiz:+.2f} puan")

    m = model_yukle()
    pf = portfoy_yukle(T, B, S)
    satirlar = [ozet(gerceklesen(T, B, S), "Gerceklesen 2008-2010 (kriz)")]
    for gecis in (24, 30):
        e = senaryo_calistir(pf, m, issizlik_artis=ISSIZLIK, ev_fiyati_degisim=EV_FIYATI,
                             faiz_degisim=faiz, gecis_ay=gecis)
        satirlar.append(ozet(e, f"Model: gerceklesen sok, gecis {gecis} ay"))
        print(f"  gecis {gecis} ay bitti", flush=True)
    # Karsilastirma icin onceki satirlar (stres.py ciktisi)
    onceki = pd.read_csv(TABLOLAR / "stres_kriz_karsilastirma.csv")
    tablo = pd.concat([pd.DataFrame(satirlar), onceki[onceki["senaryo"].str.startswith("Model")]])
    print("\n(birikimli %)\n" + tablo.round(2).to_string(index=False))
    tablo.to_csv(TABLOLAR / "stres_kriz_gercek_sok.csv", index=False)


if __name__ == "__main__":
    main()
