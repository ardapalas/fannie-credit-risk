"""Stres senaryo izgarasini onceden hesaplar ve veritabanina (senaryo_sonuc) yazar.

Kullanim (proje kok dizininden; uzun surer, arka planda calistirin):
    python src/export/senaryo_izgara.py

- Portfoy: Ocak 2010, 2005-2009 kusaklari, orneklem 50.000 kredi (tohum 42) -- stres.py ile ayni.
- Izgara: issizlik {0,2,4,6} puan x ev fiyati {0,-10,-20,-30}% x faiz {-1,0,+1} puan;
  gecis 12 ay, ufuk 36 ay -> 48 senaryo x 36 ay.
- Her senaryo bitince kendi transaction'inda yazilir. Yeniden baslatilirsa veritabaninda
  zaten olan senaryolar ATLANIR (kaldigi yerden devam).
- Modeller dondurulmus: sadece models/ altindaki dosyalar OKUNUR (stres.model_yukle).
- Yazilan veri toplulastirilmis portfoy egrisidir; kredi bazinda bilgi yok.
"""
import itertools
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(KOK), str(KOK / "src" / "model")]

from sqlalchemy import select  # noqa: E402

from api.integration.db.models import SenaryoSonuc, Taban  # noqa: E402
from api.integration.db.session import OturumYap, motor  # noqa: E402
from stres import model_yukle, portfoy_kontrol, portfoy_yukle, senaryo_calistir  # noqa: E402

PORTFOY_TARIH, BAS_YIL, SON_YIL = "2010-01-01", 2005, 2009
ORNEKLEM, TOHUM = 50_000, 42
ISSIZLIK = (0.0, 2.0, 4.0, 6.0)
EV_FIYATI = (0.0, -10.0, -20.0, -30.0)      # yuzde
FAIZ = (-1.0, 0.0, 1.0)
GECIS, UFUK = 12, 36
# Kontrol noktalari once: baz, ilimli, siddetliye en yakin (5/-25 izgarada yok -> 6/-30)
ONCELIKLI = [(0.0, 0.0, 0.0), (2.0, -10.0, 0.0), (6.0, -30.0, 0.0), (4.0, -20.0, 0.0)]


def izgara():
    hepsi = list(itertools.product(ISSIZLIK, EV_FIYATI, FAIZ))
    return ONCELIKLI + [s for s in hepsi if s not in ONCELIKLI]


def main():
    Taban.metadata.create_all(motor, tables=[SenaryoSonuc.__table__])
    with OturumYap() as o:
        var = set(o.execute(select(SenaryoSonuc.issizlik, SenaryoSonuc.ev_fiyati, SenaryoSonuc.faiz)
                            .where(SenaryoSonuc.gecis == GECIS, SenaryoSonuc.ufuk == UFUK)
                            .distinct()).all())
    kalan = [s for s in izgara() if s not in var]
    print(f"izgara: {len(izgara())} senaryo | veritabaninda: {len(var)} | hesaplanacak: {len(kalan)}",
          flush=True)
    if not kalan:
        return

    m = model_yukle()
    pf = portfoy_yukle(PORTFOY_TARIH, BAS_YIL, SON_YIL, orneklem=ORNEKLEM, tohum=TOHUM)
    portfoy_kontrol(pf, PORTFOY_TARIH)
    print(f"portfoy: {len(pf):,} kredi", flush=True)

    t_bas = time.time()
    for i, (iss, ev, faiz) in enumerate(kalan, 1):
        t0 = time.time()
        egri = senaryo_calistir(pf, m, issizlik_artis=iss, ev_fiyati_degisim=ev / 100,
                                faiz_degisim=faiz, ufuk=UFUK, gecis_ay=GECIS)
        satirlar = [SenaryoSonuc(issizlik=iss, ev_fiyati=ev, faiz=faiz, gecis=GECIS, ufuk=UFUK, ay=int(ay),
                                 batma=float(r.batma), erken=float(r.erken), acik=float(r.acik))
                    for ay, r in egri.iterrows()]
        with OturumYap.begin() as o:          # senaryo basina tek transaction
            o.add_all(satirlar)
        sure = time.time() - t0
        ort = (time.time() - t_bas) / i
        print(f"[{i}/{len(kalan)}] issizlik {iss:+.0f} ev {ev:+.0f}% faiz {faiz:+.0f}: "
              f"batma36 %{100 * egri.loc[UFUK, 'batma']:.2f} erken36 %{100 * egri.loc[UFUK, 'erken']:.1f} "
              f"| {sure:.0f} sn | kalan ~{ort * (len(kalan) - i) / 60:.0f} dk", flush=True)


if __name__ == "__main__":
    main()
