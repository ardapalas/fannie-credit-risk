"""SQLAlchemy tablolari -- veritabani semasinin TEK kaynagi (export scriptleri de bunu kullanir).

LISANS: buraya sadece TOPLULASTIRILMIS veri girer. Kredi bazinda satir, kredi_id veya tekil
kredi bilgisi YOK. Kucuk hucreler (30'dan az kredi) export sirasinda atilir veya null yazilir.
"""
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Taban(DeclarativeBase):
    pass


class VintageEgri(Taban):
    """Kusak (ceyrek) x yas birikimli oranlar. seri: 'gercek' veya 'lgbm' (kalibre LightGBM,
    sadece dogrulama/test kusaklari). Riskte 30'dan az kredi kalan yas noktalari yok."""
    __tablename__ = "vintage_egri"
    ceyrek: Mapped[str] = mapped_column(String(6), primary_key=True)
    olay: Mapped[str] = mapped_column(String(16), primary_key=True)      # batti / erken_kapatti
    seri: Mapped[str] = mapped_column(String(8), primary_key=True)       # gercek / lgbm
    yas: Mapped[int] = mapped_column(Integer, primary_key=True)
    bolum: Mapped[str] = mapped_column(String(10))                       # egitim / dogrulama / test
    deger: Mapped[float] = mapped_column(Float)


class KusakOzet(Taban):
    __tablename__ = "kusak_ozet"
    ceyrek: Mapped[str] = mapped_column(String(6), primary_key=True)
    bolum: Mapped[str] = mapped_column(String(10))
    kredi_sayisi: Mapped[int] = mapped_column(Integer)
    batti_orani: Mapped[float] = mapped_column(Float)
    erken_orani: Mapped[float] = mapped_column(Float)
    sansurlu_orani: Mapped[float] = mapped_column(Float)


class EyaletOzet(Taban):
    """Eyalet x kredinin verildigi yil. 30'dan az kredi: kredi_sayisi ve batti_orani NULL."""
    __tablename__ = "eyalet_ozet"
    eyalet: Mapped[str] = mapped_column(String(2), primary_key=True)
    yil: Mapped[int] = mapped_column(Integer, primary_key=True)
    kredi_sayisi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    batti_orani: Mapped[float | None] = mapped_column(Float, nullable=True)


class ModelMetrik(Taban):
    __tablename__ = "model_metrik"
    metrik: Mapped[str] = mapped_column(String(24), primary_key=True)
    model: Mapped[str] = mapped_column(String(24), primary_key=True)
    durum: Mapped[str] = mapped_column(String(8), primary_key=True)      # once / sonra (kalibrasyon)
    bolum: Mapped[str] = mapped_column(String(10), primary_key=True)     # dogrulama / test
    deger: Mapped[float] = mapped_column(Float)


class SenaryoSonuc(Taban):
    """Onceden hesaplanmis stres izgarasi: Ocak 2010 portfoyu, 50 bin kredilik orneklem.
    issizlik: puan, ev_fiyati: yuzde (-10 = %10 dusus), faiz: puan; gecis ve ay: ay."""
    __tablename__ = "senaryo_sonuc"
    issizlik: Mapped[float] = mapped_column(Float, primary_key=True)
    ev_fiyati: Mapped[float] = mapped_column(Float, primary_key=True)
    faiz: Mapped[float] = mapped_column(Float, primary_key=True)
    gecis: Mapped[int] = mapped_column(Integer, primary_key=True)
    ufuk: Mapped[int] = mapped_column(Integer, primary_key=True)
    ay: Mapped[int] = mapped_column(Integer, primary_key=True)
    batma: Mapped[float] = mapped_column(Float)
    erken: Mapped[float] = mapped_column(Float)
    acik: Mapped[float] = mapped_column(Float)
