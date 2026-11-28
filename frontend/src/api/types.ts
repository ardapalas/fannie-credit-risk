// API yanit tipleri: api/schemas/yanitlar.py ile birebir ayni (alan adlari API'deki gibi).
// Hepsi toplulastirilmis veri; kredi bazinda bilgi yok.

export type Olay = "batti" | "erken_kapatti";
export type Bolum = "egitim" | "dogrulama" | "test";
export type Seri = "gercek" | "lgbm";

export interface Saglik {
  durum: string;
  veritabani: boolean;
  senaryo_sayisi: number;
  senaryo_izgara_boyutu: number;
}

export interface EgriNoktasi {
  yas: number; // ay
  deger: number; // birikimli oran, 0-1
}

export interface VintageSerisi {
  ceyrek: string;
  bolum: Bolum;
  olay: Olay;
  seri: Seri;
  noktalar: EgriNoktasi[];
}

export interface KusakOzeti {
  ceyrek: string;
  bolum: Bolum;
  kredi_sayisi: number;
  batti_orani: number;
  erken_orani: number;
  sansurlu_orani: number;
}

export interface EyaletOzeti {
  eyalet: string; // posta kodu (CA, TX ...)
  yil: number;
  kredi_sayisi: number | null; // null: 30'dan az kredi (gizli)
  batti_orani: number | null;
  gizli: boolean;
}

export type MetrikAdi =
  | "log_loss"
  | "batma_auc"
  | "batma_gini"
  | "batma_t/g"
  | "erken_auc"
  | "erken_gini"
  | "erken_t/g"
  | "batma_yakala_5"
  | "batma_yakala_10"
  | "batma_yakala_20";

export interface ModelMetrigi {
  metrik: MetrikAdi;
  model: string; // "LightGBM" | "Sinir agi" | "Lojistik reg."
  durum: "once" | "sonra"; // kalibrasyon oncesi / sonrasi
  bolum: "dogrulama" | "test";
  deger: number;
}

export interface SenaryoParametreleri {
  issizlik: number; // puan
  ev_fiyati: number; // yuzde (-10 = %10 dusus)
  faiz: number; // puan
}

export interface SenaryoAyi {
  ay: number;
  batma: number;
  erken: number;
  acik: number;
}

export interface SenaryoSonucu {
  istenen: SenaryoParametreleri;
  kullanilan: SenaryoParametreleri;
  gecis: number;
  ufuk: number;
  portfoy: string;
  egri: SenaryoAyi[];
}
