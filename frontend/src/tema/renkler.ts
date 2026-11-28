// Grafik renkleri (Recharts / SVG icin; CSS degiskenleri SVG ozniteliklerinde guvenilir degil).
// Kaynak: dataviz referans paleti. Batma ve erken kapanis HER grafikte ayni renk; ikisi tonla
// birlikte ACIKLIKLA da ayrilir (renk korlugunde ve gri baskida ayirt edilsin).
// Gecerlilik: dataviz validate_palette.js ile acik (#fcfcfb) ve koyu (#1a1a19) zeminde kontrol edildi:
//  - batma/erken: tum kontroller PASS; OKLCH aciklik farki acik 0,13 / koyu 0,16
//  - kusak (3 renk, --pairs all): CVD dE acik 13,0 / koyu 9,9; normal gorus 27,5 / 26,5.
//    4 renkli hicbir kombinasyon iki temada --pairs all gecmedi -> en fazla 3 kusak.
//    Acikta pembe kontrasti 2,6:1 (WARN) -> cizgi sonlarinda kusak adi etiketi (zorunlu rahatlatma).
//  - bolum ve harita rampalari --ordinal PASS (harita: 7 sinifla gecen rampa yok -> 5 sinif).

export type TemaAdi = "acik" | "koyu";

export interface GrafikRenkleri {
  zemin: string;
  murekkep: string; // birincil metin
  ikincil: string;
  soluk: string; // eksen etiketleri
  izgara: string;
  eksen: string;
  batma: string;
  erken: string;
  /** Kusak karsilastirmasi (en fazla 3): sabit sira, dongu yok. Turuncu/kirmizi batma anlamina
   *  karismasin diye kullanilmadi; mavi-pembe-yesil iki temada tum ciftlerde gecen en guclu uclu. */
  kusak: [string, string, string];
  /** Egitim -> dogrulama -> test: ayni ton, artan koyuluk (sirali) */
  bolum: Record<"egitim" | "dogrulama" | "test", string>;
  /** Harita: tek tonlu sirali rampa, dusuk -> yuksek battı orani */
  harita: string[];
  haritaYok: string; // veri yok (eyalet listede degil)
  tarama: string; // yetersiz veri deseni
}

export const RENKLER: Record<TemaAdi, GrafikRenkleri> = {
  acik: {
    zemin: "#fcfcfb",
    murekkep: "#0b0b0b",
    ikincil: "#52514e",
    soluk: "#898781",
    izgara: "#e1e0d9",
    eksen: "#c3c2b7",
    batma: "#a8401a", // koyu turuncu (L 0,51)
    erken: "#4a8fe0", // acik mavi (L 0,64)
    kusak: ["#2a78d6", "#e87ba4", "#008300"],
    bolum: { egitim: "#86b6ef", dogrulama: "#2a78d6", test: "#184f95" },
    harita: ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"],
    haritaYok: "#f0efec",
    tarama: "#898781",
  },
  koyu: {
    zemin: "#1a1a19",
    murekkep: "#f0efec",
    ikincil: "#c3c2b7",
    soluk: "#898781",
    izgara: "#2c2c2a",
    eksen: "#383835",
    batma: "#e8733f", // acik turuncu (L 0,68)
    erken: "#256abf", // orta mavi (L 0,53)
    kusak: ["#3987e5", "#d55181", "#0ca30c"],
    bolum: { egitim: "#256abf", dogrulama: "#5598e7", test: "#b7d3f6" },
    harita: ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"],
    haritaYok: "#262624",
    tarama: "#898781",
  },
};
