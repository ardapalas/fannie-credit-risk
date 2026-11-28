import { useState } from "react";
import type { MetrikAdi, ModelMetrigi } from "../api/types";
import { MODEL_ADI, MODEL_SIRASI, ondalik, yuzde } from "../bicim";

const METRIKLER: { ad: MetrikAdi; etiket: string; yon: "yuksek" | "dusuk" | "bir"; bicim: (v: number) => string }[] = [
  { ad: "batma_auc", etiket: "Batma AUC", yon: "yuksek", bicim: (v) => ondalik(v, 3) },
  { ad: "batma_gini", etiket: "Batma Gini", yon: "yuksek", bicim: (v) => ondalik(v, 3) },
  { ad: "batma_yakala_5", etiket: "En riskli %5'in yakaladığı batma", yon: "yuksek", bicim: (v) => yuzde(v, 1) },
  { ad: "batma_yakala_10", etiket: "En riskli %10'un yakaladığı batma", yon: "yuksek", bicim: (v) => yuzde(v, 1) },
  { ad: "batma_yakala_20", etiket: "En riskli %20'nin yakaladığı batma", yon: "yuksek", bicim: (v) => yuzde(v, 1) },
  { ad: "batma_t/g", etiket: "Batma tahmin / gerçek", yon: "bir", bicim: (v) => ondalik(v, 2) },
  { ad: "erken_auc", etiket: "Erken kapanış AUC", yon: "yuksek", bicim: (v) => ondalik(v, 3) },
  { ad: "erken_gini", etiket: "Erken kapanış Gini", yon: "yuksek", bicim: (v) => ondalik(v, 3) },
  { ad: "erken_t/g", etiket: "Erken kapanış tahmin / gerçek", yon: "bir", bicim: (v) => ondalik(v, 2) },
  { ad: "log_loss", etiket: "Log loss", yon: "dusuk", bicim: (v) => ondalik(v, 4) },
];
const BOLUMLER = [
  { ad: "dogrulama", etiket: "Doğrulama" },
  { ad: "test", etiket: "Test" },
] as const;

export function MetrikTablosu({ metrikler }: { metrikler: ModelMetrigi[] }) {
  const [durum, setDurum] = useState<"once" | "sonra">("sonra");
  const bul = (m: MetrikAdi, model: string, bolum: string) =>
    metrikler.find((x) => x.metrik === m && x.model === model && x.bolum === bolum && x.durum === durum)?.deger;

  /** O bolumde en iyi model(ler). Gosterilen degerde esitlik varsa HEPSI en iyi sayilir
   *  (or. kalibre dogrulamada uc modelin t/g'si 1,00: birini kalin yapmak yaniltirdi). */
  const enIyiler = (m: (typeof METRIKLER)[number], bolum: string): string[] => {
    const adaylar = MODEL_SIRASI.map((model) => ({ model, v: bul(m.ad, model, bolum) })).filter(
      (a): a is { model: string; v: number } => a.v !== undefined,
    );
    if (adaylar.length === 0) return [];
    const puan = (v: number) => (m.yon === "yuksek" ? -v : m.yon === "dusuk" ? v : Math.abs(v - 1));
    const enIyiPuan = Math.min(...adaylar.map((a) => puan(a.v)));
    const enIyiMetin = m.bicim(adaylar.find((a) => puan(a.v) === enIyiPuan)!.v);
    const esitler = adaylar.filter((a) => m.bicim(a.v) === enIyiMetin);
    return esitler.length === adaylar.length ? [] : esitler.map((a) => a.model); // hepsi esitse kimse
  };

  return (
    <>
      <div className="cipler" style={{ marginBottom: "0.75rem" }} role="group" aria-label="Kalibrasyon">
        <button className="dugme" aria-pressed={durum === "sonra"} onClick={() => setDurum("sonra")}>
          Kalibrasyon sonrası
        </button>
        <button className="dugme" aria-pressed={durum === "once"} onClick={() => setDurum("once")}>
          Kalibrasyon öncesi
        </button>
      </div>
      <div className="tablo-kap">
        <table>
          <thead>
            <tr className="grup">
              <th rowSpan={2}>Metrik</th>
              {MODEL_SIRASI.map((model) => (
                <th key={model} colSpan={2} style={{ textAlign: "center" }}>
                  {MODEL_ADI[model]}
                </th>
              ))}
            </tr>
            <tr>
              {MODEL_SIRASI.flatMap((model) => BOLUMLER.map((b) => <th key={model + b.ad}>{b.etiket}</th>))}
            </tr>
          </thead>
          <tbody>
            {METRIKLER.map((m) => {
              const iyi = Object.fromEntries(BOLUMLER.map((b) => [b.ad, enIyiler(m, b.ad)]));
              return (
                <tr key={m.ad}>
                  <td>{m.etiket}</td>
                  {MODEL_SIRASI.flatMap((model) =>
                    BOLUMLER.map((b) => {
                      const v = bul(m.ad, model, b.ad);
                      return (
                        <td key={model + b.ad} className={`sayi ${iyi[b.ad].includes(model) ? "en-iyi" : ""}`}>
                          {v === undefined ? "—" : m.bicim(v)}
                        </td>
                      );
                    }),
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="kucuk ikincil" style={{ marginTop: "0.6rem" }}>
        Kalın: her bölümde o metrikte en iyi model (AUC/Gini/yakalama yüksek, log loss düşük, tahmin/gerçek
        1'e yakın); eşitlikte hepsi kalın, üç model eşitse hiçbiri. Kalibrasyon 2009 kredilerinde öğrenildi; doğrulamadaki kalibre değerler örneklem içidir,
        gerçek sınav test (2010–2012). Yakalama oranları kredi-ay düzeyindedir.
      </p>
    </>
  );
}
