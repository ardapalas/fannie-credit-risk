"""Veritabani okuma (repository'ler). ORM satirlarini domain nesnelerine cevirir.
Sadece okur; yazma export scriptlerinin isi."""
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from api.domain.nesneler import (EgriNoktasi, EyaletOzeti, KusakOzeti, ModelMetrigi, SenaryoAyi,
                                 SenaryoParametreleri, VintageSerisi)
from api.integration.db.models import EyaletOzet, KusakOzet, ModelMetrik, SenaryoSonuc, VintageEgri


class VintageDeposu:
    def __init__(self, oturum: Session):
        self.oturum = oturum

    def seriler(self, ceyrek: str | None, olay: str | None) -> list[VintageSerisi]:
        q = select(VintageEgri).order_by(VintageEgri.ceyrek, VintageEgri.olay, VintageEgri.seri,
                                         VintageEgri.yas)
        if ceyrek:
            q = q.where(VintageEgri.ceyrek == ceyrek)
        if olay:
            q = q.where(VintageEgri.olay == olay)
        seriler: dict[tuple, VintageSerisi] = {}
        for r in self.oturum.scalars(q):
            anahtar = (r.ceyrek, r.olay, r.seri)
            if anahtar not in seriler:
                seriler[anahtar] = VintageSerisi(r.ceyrek, r.bolum, r.olay, r.seri)
            seriler[anahtar].noktalar.append(EgriNoktasi(r.yas, r.deger))
        return list(seriler.values())


class KusakDeposu:
    def __init__(self, oturum: Session):
        self.oturum = oturum

    def hepsi(self) -> list[KusakOzeti]:
        return [KusakOzeti(r.ceyrek, r.bolum, r.kredi_sayisi, r.batti_orani, r.erken_orani,
                           r.sansurlu_orani)
                for r in self.oturum.scalars(select(KusakOzet).order_by(KusakOzet.ceyrek))]


class EyaletDeposu:
    def __init__(self, oturum: Session):
        self.oturum = oturum

    def listele(self, yil: int | None) -> list[EyaletOzeti]:
        q = select(EyaletOzet).order_by(EyaletOzet.yil, EyaletOzet.eyalet)
        if yil is not None:
            q = q.where(EyaletOzet.yil == yil)
        return [EyaletOzeti(r.eyalet, r.yil, r.kredi_sayisi, r.batti_orani) for r in self.oturum.scalars(q)]


class MetrikDeposu:
    def __init__(self, oturum: Session):
        self.oturum = oturum

    def listele(self, bolum: str | None) -> list[ModelMetrigi]:
        q = select(ModelMetrik).order_by(ModelMetrik.metrik, ModelMetrik.model, ModelMetrik.durum,
                                         ModelMetrik.bolum)
        if bolum:
            q = q.where(ModelMetrik.bolum == bolum)
        return [ModelMetrigi(r.metrik, r.model, r.durum, r.bolum, r.deger) for r in self.oturum.scalars(q)]


class SenaryoDeposu:
    def __init__(self, oturum: Session):
        self.oturum = oturum

    def egri(self, p: SenaryoParametreleri, gecis: int, ufuk: int) -> list[SenaryoAyi]:
        q = (select(SenaryoSonuc)
             .where(SenaryoSonuc.issizlik == p.issizlik, SenaryoSonuc.ev_fiyati == p.ev_fiyati,
                    SenaryoSonuc.faiz == p.faiz, SenaryoSonuc.gecis == gecis, SenaryoSonuc.ufuk == ufuk)
             .order_by(SenaryoSonuc.ay))
        return [SenaryoAyi(r.ay, r.batma, r.erken, r.acik) for r in self.oturum.scalars(q)]

    def senaryo_sayisi(self) -> int:
        return len(self.oturum.execute(
            select(SenaryoSonuc.issizlik, SenaryoSonuc.ev_fiyati, SenaryoSonuc.faiz,
                   SenaryoSonuc.gecis, SenaryoSonuc.ufuk).distinct()).all())


class SaglikDeposu:
    def __init__(self, oturum: Session):
        self.oturum = oturum

    def baglanti_var_mi(self) -> bool:
        try:
            self.oturum.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
