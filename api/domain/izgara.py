"""Onceden hesaplanmis stres senaryo izgarasi ve en yakin noktaya yuvarlama kurali.

Izgara src/export/senaryo_izgara.py ile AYNI olmali.
Kural: deger izgara araligindaysa en yakin izgara noktasina yuvarlanir; esitlikte KOTU senaryo
secilir (issizlik: yuksek, ev fiyati: dusuk, faiz: yuksek -- stres testlerinde faiz artisi
olumsuz kabul edilir). Aralik disindaki degerler kabul edilmez (API 422 dondurur).
"""
from api.domain.nesneler import SenaryoParametreleri

ISSIZLIK = (0.0, 2.0, 4.0, 6.0)
EV_FIYATI = (-30.0, -20.0, -10.0, 0.0)
FAIZ = (-1.0, 0.0, 1.0)
GECIS, UFUK = 12, 36
PORTFOY_ACIKLAMA = "Ocak 2010'da acik 2005-2009 kusaklari; 50.000 kredilik orneklem (tohum 42)"


def en_yakin(deger: float, noktalar: tuple[float, ...], kotu_yuksek: bool) -> float:
    """En yakin izgara noktasi. Esitlikte kotu yon: kotu_yuksek ise buyuk, degilse kucuk deger."""
    if not min(noktalar) <= deger <= max(noktalar):
        raise ValueError(f"{deger} izgara araliginin disinda [{min(noktalar)}, {max(noktalar)}]")
    en_kucuk_uzaklik = min(abs(deger - n) for n in noktalar)
    adaylar = [n for n in noktalar if abs(abs(deger - n) - en_kucuk_uzaklik) < 1e-9]
    return max(adaylar) if kotu_yuksek else min(adaylar)


def izgaraya_yuvarla(p: SenaryoParametreleri) -> SenaryoParametreleri:
    return SenaryoParametreleri(
        issizlik=en_yakin(p.issizlik, ISSIZLIK, kotu_yuksek=True),
        ev_fiyati=en_yakin(p.ev_fiyati, EV_FIYATI, kotu_yuksek=False),
        faiz=en_yakin(p.faiz, FAIZ, kotu_yuksek=True),
    )
