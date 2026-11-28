"""Okuma endpoint'leri. INCE: parametreleri dogrular, servisi cagirir, semaya cevirir.
Veritabanina dogrudan dokunmaz (servisler Depends ile gelir)."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api.domain import izgara
from api.domain.nesneler import Olay, SenaryoParametreleri
from api.schemas import yanitlar as s
from api.service.bagimliliklar import (eyalet_servisi, kusak_servisi, metrik_servisi, saglik_servisi,
                                       senaryo_servisi, vintage_servisi)
from api.service.servisler import (EyaletServisi, KusakServisi, MetrikServisi, SaglikServisi,
                                   SenaryoBulunamadi, SenaryoServisi, VintageServisi)

router = APIRouter()
CEYREK_DESENI = r"^20(0[5-9]|1[0-2])Q[1-4]$"


@router.get("/health", response_model=s.Saglik, tags=["sistem"], summary="Saglik kontrolu")
def saglik(servis: Annotated[SaglikServisi, Depends(saglik_servisi)]):
    return servis.durum()


@router.get("/vintages", response_model=list[s.VintageSerisi], tags=["kusaklar"],
            summary="Vintage (kusak) birikimli egrileri",
            description="Kusak ve yasa gore birikimli batma / erken kapanis oranlari. 'gercek' tum "
                        "kusaklar icin; 'lgbm' (kalibre LightGBM) sadece dogrulama ve test kusaklari icin.")
def vintages(
    servis: Annotated[VintageServisi, Depends(vintage_servisi)],
    ceyrek: Annotated[str | None, Query(pattern=CEYREK_DESENI, description="2005Q1-2012Q4",
                                        examples=["2009Q1"])] = None,
    olay: Annotated[Olay | None, Query(description="batti / erken_kapatti")] = None,
):
    return servis.seriler(ceyrek, olay.value if olay else None)


@router.get("/cohorts", response_model=list[s.KusakOzeti], tags=["kusaklar"],
            summary="Kusak ozetleri", description="Ceyrek basina kredi sayisi ve sonuc oranlari.")
def cohorts(servis: Annotated[KusakServisi, Depends(kusak_servisi)]):
    return servis.hepsi()


@router.get("/states", response_model=list[s.EyaletOzeti], tags=["kusaklar"],
            summary="Eyalet bazinda batma oranlari",
            description="Eyalet x kredinin verildigi yil. 30'dan az kredi iceren hucreler null (gizli).")
def states(
    servis: Annotated[EyaletServisi, Depends(eyalet_servisi)],
    yil: Annotated[int | None, Query(ge=2005, le=2012, description="Kredinin verildigi yil",
                                     examples=[2007])] = None,
):
    return servis.listele(yil)


@router.get("/model/metrics", response_model=list[s.ModelMetrigi], tags=["model"],
            summary="Model metrikleri",
            description="Uc model, kalibrasyon oncesi/sonrasi; dogrulama (2009) ve test (2010-2012). "
                        "Modeller dondurulmus (model-v1).")
def model_metrics(
    servis: Annotated[MetrikServisi, Depends(metrik_servisi)],
    bolum: Annotated[Literal["dogrulama", "test"] | None, Query(description="dogrulama / test")] = None,
):
    return servis.listele(bolum)


@router.get("/scenarios", response_model=s.SenaryoSonucu, tags=["stres"],
            summary="Stres senaryosu (onceden hesaplanmis izgara)",
            description="Izgara: issizlik {0,2,4,6} puan, ev fiyati {0,-10,-20,-30}%, faiz {-1,0,+1} puan; "
                        "gecis 12 ay, ufuk 36 ay. Degerler en yakin izgara noktasina yuvarlanir, esitlikte "
                        "kotu senaryo secilir. Aralik disi degerler 422.",
            responses={404: {"description": "Izgara noktasi henuz hesaplanmamis"}})
def scenarios(
    servis: Annotated[SenaryoServisi, Depends(senaryo_servisi)],
    issizlik: Annotated[float, Query(ge=min(izgara.ISSIZLIK), le=max(izgara.ISSIZLIK),
                                     description="Issizlik artisi (puan), 0-6", examples=[2])] = 0.0,
    ev_fiyati: Annotated[float, Query(ge=min(izgara.EV_FIYATI), le=max(izgara.EV_FIYATI),
                                      description="Ev fiyati degisimi (yuzde), -30-0", examples=[-10])] = 0.0,
    faiz: Annotated[float, Query(ge=min(izgara.FAIZ), le=max(izgara.FAIZ),
                                 description="Faiz degisimi (puan), -1-+1", examples=[0])] = 0.0,
):
    try:
        sonuc = servis.en_yakin_senaryo(SenaryoParametreleri(issizlik, ev_fiyati, faiz))
    except SenaryoBulunamadi as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return s.SenaryoSonucu(istenen=s.SenaryoParametreleri.model_validate(sonuc.istenen),
                           kullanilan=s.SenaryoParametreleri.model_validate(sonuc.kullanilan),
                           gecis=sonuc.gecis, ufuk=sonuc.ufuk, portfoy=izgara.PORTFOY_ACIKLAMA,
                           egri=[s.SenaryoAyi.model_validate(a) for a in sonuc.egri])
