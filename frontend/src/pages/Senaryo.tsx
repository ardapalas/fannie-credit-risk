import { useState } from "react";
import { api } from "../api/endpoints";
import type { SenaryoAyi, SenaryoParametreleri } from "../api/types";
import { VeriDurumu } from "../components/Durum";
import { SenaryoGrafigi } from "../components/SenaryoGrafigi";
import { puanFarki, yuzde } from "../bicim";
import { useApi } from "../hooks/useApi";

// API izgarasi (api/domain/izgara.py) ile AYNI: kaydiricilar sadece bu degerlerde durur,
// boylece API'nin en yakin noktaya yuvarlama kurali hic devreye girmez.
const IZGARA = {
  issizlik: { degerler: [0, 2, 4, 6], etiket: "İşsizlik artışı", birim: (v: number) => `+${v} puan` },
  ev_fiyati: { degerler: [0, -10, -20, -30], etiket: "Ev fiyatı değişimi", birim: (v: number) => (v === 0 ? "%0" : `−%${-v}`) },
  faiz: { degerler: [-1, 0, 1], etiket: "Faiz değişimi", birim: (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)} puan` },
} as const;
type Parametre = keyof typeof IZGARA;
const BAZ: SenaryoParametreleri = { issizlik: 0, ev_fiyati: 0, faiz: 0 };
const AYLAR = [12, 24, 36];

export function Senaryo() {
  const [p, setP] = useState<SenaryoParametreleri>({ issizlik: 2, ev_fiyati: -10, faiz: 0 });
  const anahtar = `${p.issizlik}|${p.ev_fiyati}|${p.faiz}`;
  const bazMi = anahtar === "0|0|0";

  const baz = useApi((s) => api.senaryo(BAZ, s), "baz");
  const secili = useApi((s) => api.senaryo(p, s), anahtar);
  // Hata/yukleniyor: ikisini birlikte ele al
  const ikisi = {
    veri: baz.veri && secili.veri ? { baz: baz.veri.egri, secili: secili.veri.egri } : undefined,
    yukleniyor: baz.yukleniyor || secili.yukleniyor,
    hata: baz.hata ?? secili.hata,
    tekrarDene: () => {
      baz.tekrarDene();
      secili.tekrarDene();
    },
  };

  return (
    <>
      <div className="sayfa-basi">
        <h1>Senaryo analizi</h1>
        <p>
          Makro şoklar altında portföyün 36 aylık birikimli batma ve erken kapanış oranları. Bu bir tahmin değil,
          “ya olursa” analizidir.
        </p>
      </div>

      <section className="kart">
        <div className="kaydiricilar">
          {(Object.keys(IZGARA) as Parametre[]).map((k) => (
            <Kaydirici key={k} ad={k} deger={p[k]} degistir={(v) => setP((o) => ({ ...o, [k]: v }))} />
          ))}
        </div>
      </section>

      <section className="kart" aria-busy={ikisi.yukleniyor}>
        <VeriDurumu durum={ikisi} yukleniyorMetni="Senaryo yükleniyor…">
          {(v) => (
            <>
              <div className="izgara izgara-2">
                <SenaryoGrafigi olay="batma" secili={v.secili} baz={v.baz} bazMi={bazMi} />
                <SenaryoGrafigi olay="erken" secili={v.secili} baz={v.baz} bazMi={bazMi} />
              </div>
              <SenaryoTablosu secili={v.secili} baz={v.baz} bazMi={bazMi} />
            </>
          )}
        </VeriDurumu>
      </section>

      <div className="not">
        <strong>Senaryo nedir?</strong> Portföy: Ocak 2010'da açık olan 2005–2009 kuşağı krediler (50.000
        kredilik örneklem). Makro koşullar Ocak 2010 seviyesinde sabit tutulur; seçilen şoklar (eyalet işsizliği,
        ev fiyatı → güncel LTV, piyasa faizi) ilk 12 ayda doğrusal uygulanır, sonra sabit kalır. Eğriler dondurulmuş
        kalibre LightGBM modeliyle önceden hesaplanmıştır. Şoklar tüm eyaletlere eşit uygulanır ve tek bir beklenen
        yol verir; güven aralığı yoktur.
      </div>
    </>
  );
}

function Kaydirici({ ad, deger, degistir }: { ad: Parametre; deger: number; degistir: (v: number) => void }) {
  const t = IZGARA[ad];
  const degerler = t.degerler as readonly number[];
  const i = degerler.indexOf(deger);
  const kimlik = `kaydirici-${ad}`;
  return (
    <div className="kaydirici">
      <label htmlFor={kimlik}>
        {t.etiket} <output htmlFor={kimlik}>{t.birim(deger)}</output>
      </label>
      <input
        id={kimlik}
        type="range"
        min={0}
        max={degerler.length - 1}
        step={1}
        value={i}
        aria-valuetext={t.birim(deger)}
        onChange={(e) => degistir(degerler[Number(e.target.value)])}
      />
      <div className="duraklar" aria-hidden="true">
        {degerler.map((d) => (
          <span key={d}>{t.birim(d)}</span>
        ))}
      </div>
    </div>
  );
}

function SenaryoTablosu({ secili, baz, bazMi }: { secili: SenaryoAyi[]; baz: SenaryoAyi[]; bazMi: boolean }) {
  const ay = (e: SenaryoAyi[], a: number) => e.find((x) => x.ay === a)!;
  const satirlar = [
    { ad: "Birikimli batma", k: "batma" as const },
    { ad: "Birikimli erken kapanış", k: "erken" as const },
  ];
  return (
    <div className="tablo-kap" style={{ marginTop: "1rem" }}>
      <table>
        <thead>
          <tr>
            <th>Seçili senaryo</th>
            {AYLAR.map((a) => (
              <th key={a}>{a}. ay</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {satirlar.map((s) => (
            <tr key={s.k}>
              <td>{s.ad}</td>
              {AYLAR.map((a) => {
                const v = ay(secili, a)[s.k];
                const fark = v - ay(baz, a)[s.k];
                return (
                  <td key={a} className="sayi">
                    {yuzde(v, 2)}
                    {!bazMi && <span className="kucuk ikincil"> ({puanFarki(fark)})</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {!bazMi && <p className="kucuk ikincil">Parantez içi: baz senaryoya (0 / 0 / 0) göre fark.</p>}
    </div>
  );
}
