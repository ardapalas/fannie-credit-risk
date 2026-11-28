import { useState } from "react";
import { api } from "../api/endpoints";
import type { EyaletOzeti } from "../api/types";
import { VeriDurumu } from "../components/Durum";
import { EyaletHaritasi, SINIF_ETIKETI } from "../components/EyaletHaritasi";
import { HARITA_DISI } from "../components/eyaletKodlari";
import { sayi, yuzde } from "../bicim";
import { useApi } from "../hooks/useApi";
import { useRenkler } from "../tema/Tema";

const YILLAR = [2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012];

export function Harita() {
  const r = useRenkler();
  const [yil, setYil] = useState(2007);
  // Tum yillar bir kez cekilir: yil degisimi aninda, renk skalasi yillar arasinda sabit
  const eyaletler = useApi((s) => api.eyaletler(undefined, s), "eyaletler");

  return (
    <>
      <div className="sayfa-basi">
        <h1>Eyalet haritası</h1>
        <p>
          Seçilen yılda verilen kredilerin gözlem sonuna kadar batma oranı. Renk skalası bütün yıllar için
          aynıdır; 30'dan az kredi içeren hücreler gizlenir ve taralı gösterilir.
        </p>
      </div>

      <section className="kart">
        <div className="cipler" role="group" aria-label="Kredinin verildiği yıl" style={{ marginBottom: "0.75rem" }}>
          {YILLAR.map((y) => (
            <button key={y} className="dugme" aria-pressed={y === yil} onClick={() => setYil(y)}>
              {y}
            </button>
          ))}
        </div>

        <div className="lejant" aria-label="Renk açıklaması">
          {SINIF_ETIKETI.map((e, i) => (
            <span className="lejant-oge" key={e}>
              <span className="isaret-kare" style={{ background: r.harita[i], border: `1px solid ${r.eksen}` }} />
              {e}
            </span>
          ))}
          <span className="lejant-oge">
            <span
              className="isaret-kare"
              style={{
                background: `repeating-linear-gradient(45deg, ${r.tarama} 0 2px, ${r.zemin} 2px 5px)`,
                border: `1px solid ${r.eksen}`,
              }}
            />
            Yetersiz veri (gizli)
          </span>
          <span className="lejant-oge">
            <span className="isaret-kare" style={{ background: r.haritaYok, border: `1px solid ${r.eksen}` }} />
            Veri yok
          </span>
        </div>

        <VeriDurumu durum={eyaletler}>
          {(hepsi) => {
            const satirlar = hepsi.filter((s) => s.yil === yil);
            return (
              <>
                <EyaletHaritasi satirlar={satirlar} yil={yil} />
                <div className="izgara izgara-2" style={{ marginTop: "1rem" }}>
                  <EnYuksek satirlar={satirlar} />
                  <HaritaDisi satirlar={satirlar} />
                </div>
              </>
            );
          }}
        </VeriDurumu>
      </section>
    </>
  );
}

function deger(s?: EyaletOzeti) {
  if (!s) return { oran: "veri yok", sayi: "—" };
  if (s.gizli) return { oran: "yetersiz veri", sayi: "< 30" };
  return { oran: yuzde(s.batti_orani!, 1), sayi: sayi(s.kredi_sayisi!) };
}

function EnYuksek({ satirlar }: { satirlar: EyaletOzeti[] }) {
  const ilk = satirlar
    .filter((s) => !s.gizli && !(s.eyalet in HARITA_DISI))
    .sort((a, b) => b.batti_orani! - a.batti_orani!)
    .slice(0, 5);
  return (
    <div>
      <h3>En yüksek battı oranı</h3>
      <div className="tablo-kap">
        <table>
          <thead>
            <tr><th>Eyalet</th><th>Battı oranı</th><th>Kredi</th></tr>
          </thead>
          <tbody>
            {ilk.map((s) => (
              <tr key={s.eyalet}>
                <td>{s.eyalet}</td>
                <td className="sayi">{deger(s).oran}</td>
                <td className="sayi">{deger(s).sayi}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HaritaDisi({ satirlar }: { satirlar: EyaletOzeti[] }) {
  const bul = (k: string) => satirlar.find((s) => s.eyalet === k);
  return (
    <div>
      <h3>Haritada görünmeyen / çok küçük kalan bölgeler</h3>
      <div className="tablo-kap">
        <table>
          <thead>
            <tr><th>Bölge</th><th>Battı oranı</th><th>Kredi</th></tr>
          </thead>
          <tbody>
            {Object.entries(HARITA_DISI).map(([k, ad]) => (
              <tr key={k}>
                <td>{ad} ({k})</td>
                <td className="sayi">{deger(bul(k)).oran}</td>
                <td className="sayi">{deger(bul(k)).sayi}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
