"""Servis saglayicilari (FastAPI Depends). Router'lar bunlari kullanir; boylece rest katmani
integration katmanini (oturum, repository) hic gormez: rest -> service -> integration."""
from fastapi import Depends
from sqlalchemy.orm import Session

from api.integration.db.repository import (EyaletDeposu, KusakDeposu, MetrikDeposu, SaglikDeposu,
                                           SenaryoDeposu, VintageDeposu)
from api.integration.db.session import oturum_al
from api.service.servisler import (EyaletServisi, KusakServisi, MetrikServisi, SaglikServisi,
                                   SenaryoServisi, VintageServisi)


def vintage_servisi(o: Session = Depends(oturum_al)) -> VintageServisi:
    return VintageServisi(VintageDeposu(o))


def kusak_servisi(o: Session = Depends(oturum_al)) -> KusakServisi:
    return KusakServisi(KusakDeposu(o))


def eyalet_servisi(o: Session = Depends(oturum_al)) -> EyaletServisi:
    return EyaletServisi(EyaletDeposu(o))


def metrik_servisi(o: Session = Depends(oturum_al)) -> MetrikServisi:
    return MetrikServisi(MetrikDeposu(o))


def senaryo_servisi(o: Session = Depends(oturum_al)) -> SenaryoServisi:
    return SenaryoServisi(SenaryoDeposu(o))


def saglik_servisi(o: Session = Depends(oturum_al)) -> SaglikServisi:
    return SaglikServisi(SaglikDeposu(o), SenaryoDeposu(o))
