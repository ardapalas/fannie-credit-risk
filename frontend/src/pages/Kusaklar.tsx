import { useState } from "react";
import { api } from "../api/endpoints";
import type { KusakOzeti } from "../api/types";
import { VeriDurumu } from "../components/Durum";
import { KusakCubukGrafigi } from "../components/KusakCubukGrafigi";
import { Lejant } from "../components/Lejant";
import { VintageGrafigi } from "../components/VintageGrafigi";
import { BOLUM_ADI } from "../bicim";
import { useApi } from "../hooks/useApi";
import { useRenkler } from "../tema/Tema";

// 3: dort renkli hicbir palet iki temada tum ciftlerde ayirt edilebilir degil (renkler.ts)
const EN_FAZLA = 3;
/** Her kusak eklendiginde bostaki ilk renk yuvasini alir ve kaldirilana kadar korur
 *  (renk kusagi izler, secim sirasini degil -> biri kaldirilinca digerlerinin rengi kaymaz). */
interface Secim {
  ceyrek: string;
  yuva: number;
}
const BASLANGIC: Secim[] = [
  { ceyrek: "2006Q4", yuva: 0 },
  { ceyrek: "2009Q1", yuva: 1 },
  { ceyrek: "2011Q1", yuva: 2 },
];

function secimiDegistir(secim: Secim[], c: string): Secim[] {
  if (secim.some((s) => s.ceyrek === c)) return secim.filter((s) => s.ceyrek !== c);
  let kalan = secim;
  if (kalan.length >= EN_FAZLA) kalan = kalan.slice(1); // en eski secim cikar, yuvasi bosalir
  const dolu = new Set(kalan.map((s) => s.yuva));
  const yuva = [...Array(EN_FAZLA).keys()].find((i) => !dolu.has(i)) ?? 0;
  return [...kalan, { ceyrek: c, yuva }];
}

export function Kusaklar() {
  const r = useRenkler();
  const kusaklar = useApi((s) => api.kusaklar(s), "kusaklar");
  const [secim, setSecim] = useState<Secim[]>(BASLANGIC);
  const secili = secim.map((s) => s.ceyrek);
  const renkler = Object.fromEntries(secim.map((s) => [s.ceyrek, r.kusak[s.yuva]]));
  const sec = (c: string) => setSecim((s) => secimiDegistir(s, c));

  const egriler = useApi(
    (sig) => Promise.all(secili.map((c) => api.vintagelar(c, undefined, sig))).then((x) => x.flat()),
    secili.join(","),
  );

  return (
    <>
      <div className="sayfa-basi">
        <h1>Kuşaklar</h1>
        <p>
          Kuşak: kredinin verildiği çeyrek. Kriz öncesi (2006–2007) kuşaklar belirgin şekilde daha çok battı.
          Birden fazla kuşağı seçip birikimli eğrilerini karşılaştırın.
        </p>
      </div>

      <section className="kart">
        <h2>Kuşak bazında battı oranı</h2>
        <VeriDurumu durum={kusaklar}>
          {(k) => <KusakCubukGrafigi kusaklar={k} secili={secili} sec={sec} />}
        </VeriDurumu>
      </section>

      <section className="kart">
        <h2>Birikimli eğriler</h2>
        <div className="cipler" style={{ marginBottom: "0.6rem" }}>
          {secim.map((s) => (
            <span className="cip" key={s.ceyrek}>
              <span className="isaret-kare" style={{ background: renkler[s.ceyrek] }} />
              {s.ceyrek}
              <button onClick={() => sec(s.ceyrek)} aria-label={`${s.ceyrek} kuşağını kaldır`}>
                ×
              </button>
            </span>
          ))}
          {kusaklar.veri && <KusakEkle kusaklar={kusaklar.veri} secili={secili} sec={sec} />}
          <span className="kucuk ikincil">En fazla {EN_FAZLA} kuşak.</span>
        </div>
        <Lejant
          ogeler={[
            { ad: "Gerçekleşen", renk: r.ikincil, tur: "cizgi" },
            { ad: "Kalibre LightGBM tahmini (yalnız doğrulama ve test kuşakları)", renk: r.ikincil, tur: "kesik" },
          ]}
        />
        {secili.length === 0 ? (
          <p className="ikincil">Karşılaştırmak için yukarıdan bir kuşak seçin.</p>
        ) : (
          <VeriDurumu durum={egriler} yukleniyorMetni="Eğriler yükleniyor…">
            {(seriler) => (
              <div className="izgara izgara-2">
                <VintageGrafigi olay="batti" seriler={seriler} renkler={renkler} />
                <VintageGrafigi olay="erken_kapatti" seriler={seriler} renkler={renkler} />
              </div>
            )}
          </VeriDurumu>
        )}
        <p className="kucuk ikincil">
          Yarışan riskler: her ay riskte olan kredilerde olay payı birikimli olarak toplanır. Riskte 30'dan az
          kredi kalan yaşlar gösterilmez (küçük hücre kuralı).
        </p>
      </section>
    </>
  );
}

function KusakEkle({ kusaklar, secili, sec }: { kusaklar: KusakOzeti[]; secili: string[]; sec: (c: string) => void }) {
  const bolumler = ["egitim", "dogrulama", "test"] as const;
  return (
    <select value="" onChange={(e) => e.target.value && sec(e.target.value)} aria-label="Kuşak ekle">
      <option value="">+ Kuşak ekle</option>
      {bolumler.map((b) => (
        <optgroup key={b} label={BOLUM_ADI[b]}>
          {kusaklar
            .filter((k) => k.bolum === b && !secili.includes(k.ceyrek))
            .map((k) => (
              <option key={k.ceyrek} value={k.ceyrek}>
                {k.ceyrek}
              </option>
            ))}
        </optgroup>
      ))}
    </select>
  );
}
