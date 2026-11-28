// Turkce sayi bicimleri (ondalik ayirac virgul).
const tr = (min: number, max = min) =>
  new Intl.NumberFormat("tr-TR", { minimumFractionDigits: min, maximumFractionDigits: max });

export const sayi = (v: number) => new Intl.NumberFormat("tr-TR").format(v);
export const ondalik = (v: number, basamak = 3) => tr(basamak).format(v);
/** 0,1234 -> "%12,3" */
export const yuzde = (v: number, basamak = 1) => `%${tr(basamak).format(v * 100)}`;
/** Puan farki: 0,0123 -> "+1,23 puan" */
export const puanFarki = (v: number, basamak = 2) =>
  `${v > 0 ? "+" : v < 0 ? "−" : "±"}${tr(basamak).format(Math.abs(v * 100))} puan`;
/** Eksen etiketi: 0,05 -> "%5" */
export const eksenYuzde = (v: number) => `%${tr(0, 1).format(v * 100)}`;

/** 0'dan max'a 1-2-5 adimli "yuvarlak" eksen isaretleri (en fazla ~6 isaret). Oran (0-1) cinsinden. */
export function guzelTikler(max: number, enFazla = 6): number[] {
  if (!(max > 0)) return [0];
  const kaba = max / (enFazla - 1);
  const us = 10 ** Math.floor(Math.log10(kaba));
  const adim = [1, 2, 2.5, 5, 10].map((k) => k * us).find((a) => a >= kaba) ?? 10 * us;
  const tikler: number[] = [];
  for (let t = 0; t < max + adim * 0.999; t += adim) tikler.push(Number(t.toFixed(10)));
  return tikler;
}

export const MODEL_ADI: Record<string, string> = {
  LightGBM: "LightGBM",
  "Sinir agi": "Sinir ağı",
  "Lojistik reg.": "Lojistik regresyon",
};
export const MODEL_SIRASI = ["LightGBM", "Sinir agi", "Lojistik reg."];

export const BOLUM_ADI = { egitim: "Eğitim (2005–2008)", dogrulama: "Doğrulama (2009)", test: "Test (2010–2012)" };
export const OLAY_ADI = { batti: "Batma", erken_kapatti: "Erken kapanış" };
