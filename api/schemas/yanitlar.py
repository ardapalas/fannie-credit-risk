"""Pydantic yanit semalari (Swagger /docs icin aciklama ve orneklerle)."""
from pydantic import BaseModel, ConfigDict, Field


class Sema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EgriNoktasi(Sema):
    yas: int = Field(description="Kredi yasi (ay)", examples=[36])
    deger: float = Field(description="Birikimli oran (0-1)", examples=[0.0152])


class VintageSerisi(Sema):
    ceyrek: str = Field(description="Kusak: kredinin verildigi ceyrek", examples=["2009Q1"])
    bolum: str = Field(description="egitim / dogrulama / test", examples=["dogrulama"])
    olay: str = Field(description="batti / erken_kapatti", examples=["batti"])
    seri: str = Field(description="gercek: gerceklesen; lgbm: kalibre LightGBM tahmini "
                                  "(sadece dogrulama ve test kusaklari)", examples=["gercek"])
    noktalar: list[EgriNoktasi] = Field(description="Riskte 30'dan az kredi kalan yaslar dahil edilmez")


class KusakOzeti(Sema):
    ceyrek: str = Field(examples=["2007Q1"])
    bolum: str = Field(examples=["egitim"])
    kredi_sayisi: int = Field(description="Kusaktaki kredi sayisi (%5 orneklem)", examples=[12650])
    batti_orani: float = Field(description="Gozlem sonuna kadar batan kredilerin payi", examples=[0.163])
    erken_orani: float = Field(description="Erken kapatilan kredilerin payi", examples=[0.791])
    sansurlu_orani: float = Field(description="Gozlem sonunda hala acik (sansurlu) kredilerin payi",
                                  examples=[0.046])


class EyaletOzeti(Sema):
    eyalet: str = Field(examples=["CA"])
    yil: int = Field(description="Kredinin verildigi yil", examples=[2007])
    kredi_sayisi: int | None = Field(description="30'dan az kredi varsa null (kucuk hucre kurali)",
                                     examples=[4321])
    batti_orani: float | None = Field(description="30'dan az kredi varsa null", examples=[0.21])
    gizli: bool = Field(description="Kucuk hucre kurali nedeniyle gizlendi mi", examples=[False])


class ModelMetrigi(Sema):
    metrik: str = Field(description="log_loss, batma_auc, batma_gini, batma_t/g, erken_auc, erken_gini, "
                                    "erken_t/g, batma_yakala_5/10/20", examples=["batma_auc"])
    model: str = Field(examples=["LightGBM"])
    durum: str = Field(description="Kalibrasyon oncesi (once) / sonrasi (sonra)", examples=["sonra"])
    bolum: str = Field(examples=["test"])
    deger: float = Field(examples=[0.8396])


class SenaryoParametreleri(Sema):
    issizlik: float = Field(description="Issizlik artisi (puan)", examples=[2.0])
    ev_fiyati: float = Field(description="Ev fiyati degisimi (yuzde; -10 = %10 dusus)", examples=[-10.0])
    faiz: float = Field(description="30 yillik faiz degisimi (puan)", examples=[0.0])


class SenaryoAyi(Sema):
    ay: int = Field(description="Senaryo ayi (1 = Ocak 2010)", examples=[36])
    batma: float = Field(description="Birikimli batma orani", examples=[0.0908])
    erken: float = Field(description="Birikimli erken kapanis orani", examples=[0.2287])
    acik: float = Field(description="Hala acik kredilerin payi", examples=[0.68])


class SenaryoSonucu(Sema):
    istenen: SenaryoParametreleri = Field(description="Istekte gelen degerler")
    kullanilan: SenaryoParametreleri = Field(description="Izgarada kullanilan en yakin nokta "
                                                         "(esitlikte kotu senaryo)")
    gecis: int = Field(description="Sokun dogrusal olarak tamamlandigi ay", examples=[12])
    ufuk: int = Field(examples=[36])
    portfoy: str = Field(examples=["Ocak 2010'da acik 2005-2009 kusaklari; 50.000 kredilik orneklem (tohum 42)"])
    egri: list[SenaryoAyi]


class Saglik(Sema):
    durum: str = Field(examples=["ok"])
    veritabani: bool = Field(description="Veritabani baglantisi calisiyor mu", examples=[True])
    senaryo_sayisi: int = Field(description="Veritabaninda hesaplanmis senaryo sayisi", examples=[48])
    senaryo_izgara_boyutu: int = Field(examples=[48])
