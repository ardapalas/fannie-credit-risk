"""Stres testi: makro senaryolar altinda portfoyun birikimli batma / erken kapanis oranlari.

Kullanim (proje kok dizininden; model_lgbm.py ve kalibrasyon.py once calismis olmali):
    python src/model/stres.py            # tam portfoy, ~20 dk
    python src/model/stres.py 50000      # 50 bin kredilik orneklemle (hizli deneme)

Backend'den:
    from stres import model_yukle, portfoy_yukle, senaryo_calistir
    m = model_yukle(); pf = portfoy_yukle("2010-01-01", 2005, 2009, orneklem=50_000)
    egri = senaryo_calistir(pf, m, issizlik_artis=2, ev_fiyati_degisim=-0.10, ufuk=36)

Yontem:
- Portfoy: verilen tarihte kredi-ay tablosunda satiri olan (o ay riskte, acik) krediler.
  Ozellikler build_dataset.py'deki formullerin aynisiyla o ayin makrosundan hesaplanir
  (egitim setindeki ayni satirlarla birebir karsilastirilarak kontrol edilir).
- Senaryo: makro baslangic ayinin seviyesinde SABIT + soklar. Soklar gecis_ay boyunca
  dogrusal artar, sonra sabit kalir (gecis_ay=0 -> aninda):
    issizlik_eyalet, issizlik_degisim  + issizlik_artis (puan)
    guncel_ltv                         / (1 + ev_fiyati_degisim)   (ornek: -0.25 = %25 dusus)
    faiz_farki                         - faiz_degisim (puan; piyasa faizi artarsa fark azalir)
  yas her ay 1 artar; kredinin diger ozellikleri sabit.
- Zincirleme hesap (vintage.py ile ayni formul, kredi basina):
    S_i(t) = prod (1 - q_batma - q_erken),  CIF_i,k(t) = sum S_i(t-1) q_k,i(t)
  q = kalibre LightGBM olasiliklari. Portfoy egrisi = kredilerin esit agirlikli ortalamasi.
Test kusaklarina (2010-2012 kredileri) DOKUNMAZ.
"""
import sys
import time

import duckdb
import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from features import KOK, MODELLER, OZELLIKLER
from kalibrasyon import uygula
from model_lgbm import hazirla

ISLENMIS = KOK / "data" / "processed"
SEKILLER = KOK / "reports" / "figures"
TABLOLAR = KOK / "reports" / "tables"
UFUKLAR = (12, 24, 36)

SENARYOLAR = {
    "Baz":      dict(issizlik_artis=0.0, ev_fiyati_degisim=0.00, faiz_degisim=0.0),
    "Ilimli":   dict(issizlik_artis=2.0, ev_fiyati_degisim=-0.10, faiz_degisim=0.0),
    "Siddetli": dict(issizlik_artis=5.0, ev_fiyati_degisim=-0.25, faiz_degisim=0.0),
}

ZEMIN, MUREKKEP, IKINCIL, SOLUK, IZGARA = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SIRA = {"Baz": "#86b6ef", "Ilimli": "#2a78d6", "Siddetli": "#104281"}   # siralı mavi rampa


# ----------------------------------------------------------------- yukleme
def model_yukle():
    lg = joblib.load(MODELLER / "lgbm.joblib")
    return {"model": lg["model"], "kategoriler": lg["kategoriler"],
            "kalibrasyon": joblib.load(MODELLER / "kalibrasyon.joblib")["LightGBM"]}


def _portfoy_sql(tarih, bas_yil, son_yil):
    P = ISLENMIS.as_posix()
    return f"""
        WITH makro AS (SELECT * REPLACE (ay::DATE AS ay) FROM read_parquet('{P}/makro.parquet')),
             ulusal AS (SELECT DISTINCT ay, faiz_30y, issizlik_abd FROM makro)
        SELECT a.kredi_id, a.yas, k.*  EXCLUDE (kredi_id),
               COALESCE(m.issizlik_eyalet, u.issizlik_abd)::DOUBLE AS issizlik_eyalet,
               (k.original_interest_rate - u.faiz_30y)::DOUBLE AS faiz_farki,
               (k.original_loan_to_value_ratio_ltv
                   * COALESCE(m0.hpi_eyalet / m.hpi_eyalet, 1))::DOUBLE AS guncel_ltv,
               COALESCE(m.issizlik_eyalet - m0.issizlik_eyalet, 0)::DOUBLE AS issizlik_degisim
        FROM read_parquet('{P}/kredi_ay.parquet') a
        JOIN read_parquet('{P}/tum_krediler.parquet') k ON a.kredi_id = k.kredi_id
        LEFT JOIN ulusal u ON u.ay = a.ay
        LEFT JOIN makro m ON m.ay = a.ay AND m.property_state = k.property_state
        LEFT JOIN makro m0 ON m0.ay = (a.ay - to_months(a.yas))::DATE
                          AND m0.property_state = k.property_state
        WHERE a.ay = DATE '{tarih}'
          AND left(k.ceyrek, 4) BETWEEN '{bas_yil}' AND '{son_yil}'
    """


def portfoy_yukle(tarih="2010-01-01", bas_yil=2005, son_yil=2009, orneklem=None, tohum=42):
    """tarih'te acik (o ay riskte) krediler ve o ayki ozellikleri.
    Test kusaklari (2010+) istenirse hata verir."""
    if int(son_yil) >= 2010:
        raise ValueError("test kusaklari (2010-2012) stres portfoyune alinmaz")
    con = duckdb.connect()
    con.execute("SET memory_limit='6GB'")
    pf = con.sql(_portfoy_sql(tarih, bas_yil, son_yil)).df()
    if orneklem and orneklem < len(pf):
        pf = pf.sample(orneklem, random_state=tohum)
    return pf[["kredi_id", "ceyrek"] + OZELLIKLER].reset_index(drop=True)


def portfoy_kontrol(pf, tarih):
    """Portfoy ozellikleri egitim setindeki ayni kredi-ay satirlariyla birebir ayni mi?"""
    es = pd.read_parquet(ISLENMIS / "egitim_seti.parquet", columns=["kredi_id", "ay", "bolum"] + OZELLIKLER)
    es = es[(pd.to_datetime(es["ay"]) == pd.Timestamp(tarih)) & (es["bolum"] != "test")]
    b = pf.merge(es, on="kredi_id", suffixes=("", "_es"))
    assert len(b) > 0, "kontrol icin egitim setinde eslesen satir yok"
    sayisal = [c for c in OZELLIKLER if pd.api.types.is_numeric_dtype(pf[c])]
    fark = max(float(np.nanmax(np.abs(b[c].astype(float) - b[c + "_es"].astype(float)))) for c in sayisal)
    kat = all((b[c].astype(str) == b[c + "_es"].astype(str)).all()
              for c in OZELLIKLER if c not in sayisal)
    print(f"portfoy kontrolu ({tarih}): {len(b):,} satir egitim setinde de var | "
          f"en buyuk sayisal fark {fark:.2e} | kategorikler ayni: {kat}")
    assert fark < 1e-6 and kat, "portfoy ozellikleri egitim setiyle uyusmuyor"


# ----------------------------------------------------------------- senaryo
def senaryo_calistir(pf, m, issizlik_artis=0.0, ev_fiyati_degisim=0.0, faiz_degisim=0.0,
                     ufuk=36, gecis_ay=12):
    """Portfoyun aylik birikimli batma / erken kapanis egrisi.
    Doner: DataFrame index=ay (1..ufuk), sutunlar batma, erken, acik (hala acik payi)."""
    if ev_fiyati_degisim <= -1:
        raise ValueError("ev_fiyati_degisim -1'den buyuk olmali (ornek: -0.25)")
    X0 = hazirla(pf, m["kategoriler"])
    n = len(X0)
    S, cif1, cif2 = np.ones(n), np.zeros(n), np.zeros(n)
    satirlar = []
    for t in range(1, ufuk + 1):
        r = 1.0 if gecis_ay == 0 else min(t / gecis_ay, 1.0)   # sokun ne kadari uygulandi
        X = X0.copy()
        X["yas"] = X0["yas"] + (t - 1)
        X["issizlik_eyalet"] = X0["issizlik_eyalet"] + issizlik_artis * r
        X["issizlik_degisim"] = X0["issizlik_degisim"] + issizlik_artis * r
        X["guncel_ltv"] = X0["guncel_ltv"] / (1 + ev_fiyati_degisim * r)
        X["faiz_farki"] = X0["faiz_farki"] - faiz_degisim * r
        q = uygula(m["model"].predict_proba(X), m["kalibrasyon"])
        assert (q[:, 0] > 0).all()
        cif1 += S * q[:, 1]
        cif2 += S * q[:, 2]
        S *= q[:, 0]
        satirlar.append({"ay": t, "batma": cif1.mean(), "erken": cif2.mean(), "acik": S.mean()})
    return pd.DataFrame(satirlar).set_index("ay")


def gerceklesen(tarih, bas_yil, son_yil, ufuk=36):
    """Portfoyun gercekte yasadigi birikimli oranlar (kredi-ay tablosu, orneklemsiz).
    Ayni zincirleme formul: her ay riskteki kredilerde olay payi -> birikim."""
    P = ISLENMIS.as_posix()
    g = duckdb.sql(f"""
        WITH pf AS (
            SELECT a.kredi_id FROM read_parquet('{P}/kredi_ay.parquet') a
            JOIN read_parquet('{P}/tum_krediler.parquet') k ON a.kredi_id = k.kredi_id
            WHERE a.ay = DATE '{tarih}' AND left(k.ceyrek, 4) BETWEEN '{bas_yil}' AND '{son_yil}')
        SELECT datediff('month', DATE '{tarih}', a.ay) + 1 AS ay,
               COUNT(*) AS risk, SUM((a.y = 1)::INT) AS b, SUM((a.y = 2)::INT) AS e
        FROM read_parquet('{P}/kredi_ay.parquet') a JOIN pf USING (kredi_id)
        WHERE a.ay >= DATE '{tarih}' AND a.ay < DATE '{tarih}' + INTERVAL {ufuk} MONTH
        GROUP BY 1 ORDER BY 1
    """).df().set_index("ay")
    h1, h2 = g["b"] / g["risk"], g["e"] / g["risk"]
    S_once = (1 - h1 - h2).cumprod().shift(1, fill_value=1.0)
    return pd.DataFrame({"batma": (S_once * h1).cumsum(), "erken": (S_once * h2).cumsum(),
                         "acik": (1 - h1 - h2).cumprod()})


def gerceklesen_makro(pf, tarih, ufuk=36):
    """Portfoyun eyalet dagilimiyla agirliklanmis gercek makro degisim (baslangic -> ufuk)
    ve pencere icindeki en kotu nokta."""
    mk = pd.read_parquet(ISLENMIS / "makro.parquet")
    mk["ay"] = pd.to_datetime(mk["ay"])
    bas = pd.Timestamp(tarih)
    pencere = mk[(mk["ay"] >= bas) & (mk["ay"] <= bas + pd.DateOffset(months=ufuk))]
    p = pencere.pivot(index="ay", columns="property_state", values=["issizlik_eyalet", "hpi_eyalet"])
    # Makro verisi olmayan bolgeler (PR, VI, GU) disarida; agirliklar yeniden normalize
    eyalet = pf["property_state"].astype(str)
    agirlik = eyalet[eyalet.isin(p["hpi_eyalet"].columns)].value_counts(normalize=True)
    iss = (p["issizlik_eyalet"][agirlik.index] * agirlik).sum(1)
    hpi = (p["hpi_eyalet"][agirlik.index] / p["hpi_eyalet"][agirlik.index].iloc[0] * agirlik).sum(1)
    return {"issizlik_degisim_son": iss.iloc[-1] - iss.iloc[0], "issizlik_degisim_en_kotu": iss.max() - iss.iloc[0],
            "hpi_degisim_son": hpi.iloc[-1] - 1, "hpi_degisim_en_kotu": hpi.min() - 1}


# ----------------------------------------------------------------- cikti
def ozet(egri, ad):
    s = {"senaryo": ad}
    for olay in ("batma", "erken"):
        for u in UFUKLAR:
            if u in egri.index:
                s[f"{olay}_{u}"] = 100 * egri.loc[u, olay]
    return s


def stil(ax, ondalik):
    ax.set_facecolor(ZEMIN)
    ax.grid(axis="y", color=IZGARA, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c3c2b7")
    ax.tick_params(colors=SOLUK, labelsize=8)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=ondalik))
    ax.set_xticks([0, 6, 12, 18, 24, 30, 36])
    ax.set_xlabel("Senaryo ayi", color=IKINCIL, fontsize=9)


def grafik(egriler, gercek, dosya, gercek_etiket):
    plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
    fig, eksenler = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=ZEMIN)
    for ax, (olay, baslik, ondalik) in zip(eksenler, [("batma", "Birikimli batma", 1),
                                                      ("erken", "Birikimli erken kapanis", 0)]):
        stil(ax, ondalik)
        for ad, e in egriler.items():
            ax.plot(e.index, e[olay], color=SIRA[ad], lw=2, label=f"Model: {ad}")
        ax.plot(gercek.index, gercek[olay], color=MUREKKEP, lw=2, ls="--", label=gercek_etiket)
        ax.set_title(baslik, color=MUREKKEP, fontsize=10)
    h, l = eksenler[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(l),
               frameon=False, fontsize=9, labelcolor=IKINCIL)
    fig.tight_layout()
    fig.savefig(SEKILLER / dosya, dpi=160, bbox_inches="tight", facecolor=ZEMIN)
    plt.close(fig)


def main():
    orneklem = int(sys.argv[1]) if len(sys.argv) > 1 else None
    m = model_yukle()
    SEKILLER.mkdir(parents=True, exist_ok=True)
    TABLOLAR.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 200)

    # --- 1) 2010 portfoyu: uc senaryo + gerceklesen (referans) ---
    T, B, S = "2010-01-01", 2005, 2009
    pf = portfoy_yukle(T, B, S, orneklem=orneklem)
    portfoy_kontrol(pf, T)
    print(f"portfoy {T}: {len(pf):,} kredi | kusak dagilimi (%): "
          + ", ".join(f"{y}: {100 * v:.0f}" for y, v in
                      pf["ceyrek"].str[:4].value_counts(normalize=True).sort_index().items()))
    egriler = {}
    for ad, par in SENARYOLAR.items():
        t0 = time.time()
        egriler[ad] = senaryo_calistir(pf, m, **par)
        print(f"  {ad}: {time.time() - t0:.0f} sn", flush=True)
    gercek = gerceklesen(T, B, S)
    tablo = pd.DataFrame([ozet(e, ad) for ad, e in egriler.items()]
                         + [ozet(gercek, "Gerceklesen 2010-2012 (referans)")])
    print("\nSenaryo tablosu, 2010 portfoyu (birikimli %):\n" + tablo.round(2).to_string(index=False))
    tablo.to_csv(TABLOLAR / "stres_senaryolar_2010.csv", index=False)
    grafik(egriler, gercek, "stres_senaryolar_2010.png", "Gerceklesen 2010-2012")

    # --- 2) Kriz karsilastirmasi: 2006-2007 kusaklari, Ocak 2008 ---
    T2, B2, S2 = "2008-01-01", 2006, 2007
    pf2 = portfoy_yukle(T2, B2, S2, orneklem=orneklem)
    portfoy_kontrol(pf2, T2)
    print(f"\nkriz portfoyu {T2}: {len(pf2):,} kredi")
    kriz = {ad: senaryo_calistir(pf2, m, **SENARYOLAR[ad]) for ad in ("Baz", "Siddetli")}
    gercek2 = gerceklesen(T2, B2, S2)
    tablo2 = pd.DataFrame([ozet(gercek2, "Gerceklesen 2008-2010 (kriz)")]
                          + [ozet(e, f"Model: {ad}") for ad, e in kriz.items()])
    mak = gerceklesen_makro(pf2, T2)
    print("Kriz karsilastirmasi, 2006-2007 kusaklari (birikimli %):\n" + tablo2.round(2).to_string(index=False))
    print("gerceklesen makro (portfoyun eyalet dagilimiyla, 36 ay): "
          f"issizlik {mak['issizlik_degisim_son']:+.1f} puan (en kotu {mak['issizlik_degisim_en_kotu']:+.1f}), "
          f"ev fiyati {100 * mak['hpi_degisim_son']:+.1f}% (en kotu {100 * mak['hpi_degisim_en_kotu']:+.1f}%)")
    tablo2.to_csv(TABLOLAR / "stres_kriz_karsilastirma.csv", index=False)
    grafik({"Baz": kriz["Baz"], "Siddetli": kriz["Siddetli"]}, gercek2,
           "stres_kriz_karsilastirma.png", "Gerceklesen 2008-2010")
    print(f"\nciktilar: {SEKILLER / 'stres_senaryolar_2010.png'}\n"
          f"          {SEKILLER / 'stres_kriz_karsilastirma.png'}\n          {TABLOLAR}")


if __name__ == "__main__":
    main()
