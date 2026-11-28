"""Is nesneleri. Hepsi toplulastirilmis; kredi bazinda bilgi tasimaz."""
from dataclasses import dataclass, field
from enum import Enum


class Olay(str, Enum):
    batti = "batti"
    erken_kapatti = "erken_kapatti"


class Bolum(str, Enum):
    egitim = "egitim"
    dogrulama = "dogrulama"
    test = "test"


@dataclass(frozen=True)
class EgriNoktasi:
    yas: int
    deger: float


@dataclass
class VintageSerisi:
    ceyrek: str
    bolum: str
    olay: str
    seri: str                       # gercek / lgbm
    noktalar: list[EgriNoktasi] = field(default_factory=list)


@dataclass(frozen=True)
class KusakOzeti:
    ceyrek: str
    bolum: str
    kredi_sayisi: int
    batti_orani: float
    erken_orani: float
    sansurlu_orani: float


@dataclass(frozen=True)
class EyaletOzeti:
    eyalet: str
    yil: int
    kredi_sayisi: int | None        # None: 30'dan az kredi (kucuk hucre, gizli)
    batti_orani: float | None

    @property
    def gizli(self) -> bool:
        return self.kredi_sayisi is None


@dataclass(frozen=True)
class ModelMetrigi:
    metrik: str
    model: str
    durum: str                      # once / sonra (kalibrasyon)
    bolum: str
    deger: float


@dataclass(frozen=True)
class SenaryoParametreleri:
    issizlik: float                 # puan
    ev_fiyati: float                # yuzde (-10 = %10 dusus)
    faiz: float                     # puan


@dataclass(frozen=True)
class SenaryoAyi:
    ay: int
    batma: float
    erken: float
    acik: float


@dataclass
class SenaryoSonucu:
    istenen: SenaryoParametreleri
    kullanilan: SenaryoParametreleri
    gecis: int
    ufuk: int
    egri: list[SenaryoAyi]
