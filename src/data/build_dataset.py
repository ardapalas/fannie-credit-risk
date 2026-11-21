"""Kredi-ay tablosunu ve modele hazir egitim setini kurar.

Adimlar:
    1. kredi_ay.parquet   -> her kredinin her ayi bir satir, olay ayinda y etiketi
                             (y: 0 = devam, 1 = batti, 2 = erken kapatti)
    2. egitim_seti.parquet -> orneklenmis kredi-ay satirlari + kredi ozellikleri
                              + makro degiskenler + egitim/dogrulama/test bolumu

Kullanim (proje kok dizininden):
    python src/build_dataset.py

Gerekli dosyalar (data/processed/ altinda):
    *_raw.parquet, tum_krediler.parquet, makro.parquet
"""
from pathlib import Path

import duckdb

KOK = Path(__file__).resolve().parents[2]   # src/data/build_dataset.py -> proje koku
ISLENMIS = KOK / "data" / "processed"
RAW = (ISLENMIS / "*_raw.parquet").as_posix()
KREDI = (ISLENMIS / "tum_krediler.parquet").as_posix()
MAKRO = (ISLENMIS / "makro.parquet").as_posix()
KREDI_AY = (ISLENMIS / "kredi_ay.parquet").as_posix()
EGITIM = (ISLENMIS / "egitim_seti.parquet").as_posix()

ORNEK_YUZDE = 5                     # "bir sey olmadi" satirlarinin yuzde kaci alinacak
AGIRLIK = 100 / ORNEK_YUZDE         # secilen her y=0 satiri bu kadar satiri temsil eder

# Modele girdi olarak verilmeyecek kredi tablosu sutunlari
SONUC_SUTUNLARI = "kredi_id, ilk_90_ay, son_ay, zb_kod, batma_ay, olay, olay_ay"


def kredi_ay_olustur(con):
    """Aylik ham satirlardan olay ayina kadar olan kredi-ay iskeletini kurar.

    ONEMLI: Kredi yasi her satirin kendi loan_age alanindan ALINMAZ.
    Fannie'de kredinin kapandigi aydaki son kayitta loan_age bos geliyor;
    bu bosluk "bu ay kapanis var" bilgisini modele sizdiriyordu.
    Bunun yerine kredinin baslangic ayini (ay - loan_age, dolu satirlardan)
    bulup her satirin yasini o aydan hesapliyoruz.

    Yedek: ham veride tek satiri olan (ilk raporlandigi ay kapanan) kredilerde
    loan_age hep bos -> baslangic ayi origination_date + 1 ay alinir (kredilerin
    cogunda loan_age'den bulunan baslangic, origination_date'ten tam 1 ay sonra;
    ayni yas tanimi korunsun diye). Ikisi de yoksa kredi atilir.

    Yas = -1 satirlari atilir (Fannie loan_age = -1: ilk odeme donemindan onceki ay,
    risk altinda bir ay degil; hepsi y=0). Olay satirlari (y > 0) ASLA atilmaz:
    negatif yasli bir olay satiri cikarsa ozet() kontrol tablosunda gorunur.
    """
    con.execute(f"""
        COPY (
            WITH r AS (
                SELECT loan_identifier AS kredi_id,
                       strptime(monthly_reporting_period, '%m%Y')::DATE AS ay,
                       TRY_CAST(loan_age AS INT) AS loan_age,
                       TRY_STRPTIME(origination_date, '%m%Y')::DATE AS orig_ay
                FROM read_parquet('{RAW}')
            ),
            r2 AS (
                SELECT *,
                       COALESCE(
                           MIN((ay - to_months(loan_age))::DATE) OVER (PARTITION BY kredi_id),
                           (MIN(orig_ay) OVER (PARTITION BY kredi_id) + INTERVAL 1 MONTH)::DATE
                       ) AS baslangic_ay
                FROM r
            ),
            r3 AS (
                SELECT r2.kredi_id, r2.ay,
                       datediff('month', r2.baslangic_ay, r2.ay) AS yas,
                       CASE WHEN r2.ay = k.olay_ay::DATE AND k.olay = 'batti' THEN 1
                            WHEN r2.ay = k.olay_ay::DATE AND k.olay = 'erken_kapatti' THEN 2
                            ELSE 0 END AS y
                FROM r2
                JOIN read_parquet('{KREDI}') k ON r2.kredi_id = k.kredi_id
                WHERE r2.ay <= k.olay_ay::DATE
                  AND r2.baslangic_ay IS NOT NULL      -- baslangici bulunamayan kredi atilir
            )
            SELECT * FROM r3
            WHERE yas >= 0 OR y > 0                    -- yas -1 (y=0) satirlari atilir
        ) TO '{KREDI_AY}' (FORMAT parquet)
    """)


def egitim_seti_olustur(con):
    """Orneklenmis kredi-ay satirlarina ozellikleri ve makro degiskenleri ekler."""
    con.execute(f"""
        COPY (
            WITH ornek AS (
                -- Olay satirlarinin hepsi + y=0 satirlarinin ORNEK_YUZDE'si
                -- hash ile secildigi icin her calistirmada ayni satirlar gelir
                SELECT * FROM read_parquet('{KREDI_AY}')
                WHERE y > 0 OR hash(kredi_id || CAST(ay AS VARCHAR)) % 100 < {ORNEK_YUZDE}
            ),
            makro AS (
                SELECT * REPLACE (ay::DATE AS ay) FROM read_parquet('{MAKRO}')
            ),
            ulusal AS (
                SELECT DISTINCT ay, faiz_30y, issizlik_abd FROM makro
            )
            SELECT
                o.kredi_id, o.ay, o.yas, o.y,
                CAST(CASE WHEN o.y = 0 THEN {AGIRLIK} ELSE 1 END AS DOUBLE) AS agirlik,
                CASE WHEN left(k.ceyrek, 4) <= '2008' THEN 'egitim'
                     WHEN left(k.ceyrek, 4) = '2009' THEN 'dogrulama'
                     ELSE 'test' END AS bolum,
                k.* EXCLUDE ({SONUC_SUTUNLARI}),

                -- O ayki ekonomik kosullar (eyalet verisi yoksa ulusal deger)
                u.faiz_30y,
                u.issizlik_abd,
                COALESCE(m.issizlik_eyalet, u.issizlik_abd) AS issizlik_eyalet,

                -- Turetilmis degiskenler
                k.original_interest_rate - u.faiz_30y AS faiz_farki,
                k.original_loan_to_value_ratio_ltv
                    * COALESCE(m0.hpi_eyalet / m.hpi_eyalet, 1) AS guncel_ltv,
                COALESCE(m.issizlik_eyalet - m0.issizlik_eyalet, 0) AS issizlik_degisim

            FROM ornek o
            JOIN read_parquet('{KREDI}') k ON o.kredi_id = k.kredi_id
            LEFT JOIN ulusal u ON u.ay = o.ay
            LEFT JOIN makro m ON m.ay = o.ay AND m.property_state = k.property_state
            -- Kredinin verildigi aydaki eyalet degerleri (guncel LTV ve degisim icin)
            LEFT JOIN makro m0
                   ON m0.ay = (o.ay - to_months(o.yas))::DATE
                  AND m0.property_state = k.property_state
        ) TO '{EGITIM}' (FORMAT parquet)
    """)


def ozet(con):
    print(con.sql(f"""
        SELECT bolum, y, COUNT(*) AS satir, SUM(agirlik) AS temsil_edilen
        FROM read_parquet('{EGITIM}') GROUP BY ALL ORDER BY bolum, y
    """))
    print(con.sql(f"""
        SELECT ROUND(AVG((guncel_ltv IS NULL)::INT), 4) AS guncel_ltv_bos,
               ROUND(AVG((faiz_farki IS NULL)::INT), 4) AS faiz_farki_bos,
               ROUND(MAX(guncel_ltv), 1) AS max_guncel_ltv
        FROM read_parquet('{EGITIM}')
    """))
    # Sizinti kontrolu: bu oranlar y degerleri arasinda benzer olmali.
    # Bir y degerinde 1'e yakin cikarsa o satirlarda bir bilgi sizintisi var demektir.
    print(con.sql(f"""
        SELECT y,
               ROUND(AVG((yas IS NULL)::INT), 3) AS yas_bos,
               ROUND(AVG((yas < 0)::INT), 3) AS yas_negatif,
               ROUND(AVG((issizlik_degisim = 0)::INT), 3) AS issizlik_degisim_sifir,
               ROUND(AVG((guncel_ltv = original_loan_to_value_ratio_ltv)::INT), 3) AS guncel_ltv_ayni
        FROM read_parquet('{EGITIM}') GROUP BY y ORDER BY y
    """))


def main():
    con = duckdb.connect()
    con.execute("SET memory_limit='6GB'")

    if not Path(KREDI_AY).exists():
        print("kredi_ay.parquet olusturuluyor...")
        kredi_ay_olustur(con)
    else:
        print("kredi_ay.parquet zaten var, atlaniyor.")

    print("egitim_seti.parquet olusturuluyor...")
    egitim_seti_olustur(con)
    ozet(con)


if __name__ == "__main__":
    main()