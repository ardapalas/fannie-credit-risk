"""Is mantigi. Repository'leri kullanir, domain nesneleri dondurur (HTTP'den habersiz)."""
from api.domain import izgara
from api.domain.nesneler import (EyaletOzeti, KusakOzeti, ModelMetrigi, SenaryoParametreleri,
                                 SenaryoSonucu, VintageSerisi)
from api.integration.db.repository import (EyaletDeposu, KusakDeposu, MetrikDeposu, SaglikDeposu,
                                           SenaryoDeposu, VintageDeposu)


class SenaryoBulunamadi(Exception):
    """Izgara noktasi gecerli ama veritabaninda henuz hesaplanmamis."""


class VintageServisi:
    def __init__(self, depo: VintageDeposu):
        self.depo = depo

    def seriler(self, ceyrek: str | None, olay: str | None) -> list[VintageSerisi]:
        return self.depo.seriler(ceyrek, olay)


class KusakServisi:
    def __init__(self, depo: KusakDeposu):
        self.depo = depo

    def hepsi(self) -> list[KusakOzeti]:
        return self.depo.hepsi()


class EyaletServisi:
    def __init__(self, depo: EyaletDeposu):
        self.depo = depo

    def listele(self, yil: int | None) -> list[EyaletOzeti]:
        return self.depo.listele(yil)


class MetrikServisi:
    def __init__(self, depo: MetrikDeposu):
        self.depo = depo

    def listele(self, bolum: str | None) -> list[ModelMetrigi]:
        return self.depo.listele(bolum)


class SenaryoServisi:
    def __init__(self, depo: SenaryoDeposu):
        self.depo = depo

    def en_yakin_senaryo(self, istenen: SenaryoParametreleri) -> SenaryoSonucu:
        """Izgaraya yuvarlar (aralik disi -> ValueError) ve onceden hesaplanmis egriyi dondurur."""
        kullanilan = izgara.izgaraya_yuvarla(istenen)
        egri = self.depo.egri(kullanilan, izgara.GECIS, izgara.UFUK)
        if not egri:
            raise SenaryoBulunamadi(f"senaryo henuz hesaplanmamis: {kullanilan}")
        return SenaryoSonucu(istenen, kullanilan, izgara.GECIS, izgara.UFUK, egri)


class SaglikServisi:
    def __init__(self, saglik: SaglikDeposu, senaryo: SenaryoDeposu):
        self.saglik, self.senaryo = saglik, senaryo

    def durum(self) -> dict:
        baglanti = self.saglik.baglanti_var_mi()
        return {"durum": "ok" if baglanti else "hata",
                "veritabani": baglanti,
                "senaryo_sayisi": self.senaryo.senaryo_sayisi() if baglanti else 0,
                "senaryo_izgara_boyutu": len(izgara.ISSIZLIK) * len(izgara.EV_FIYATI) * len(izgara.FAIZ)}
