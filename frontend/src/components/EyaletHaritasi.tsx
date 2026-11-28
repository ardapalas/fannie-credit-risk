import { useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import abd from "us-atlas/states-10m.json"; // harita verisi npm paketinden (dis URL yok)
import type { EyaletOzeti } from "../api/types";
import { sayi, yuzde } from "../bicim";
import { useRenkler } from "../tema/Tema";
import { POSTA } from "./eyaletKodlari";

/** Tum yillar icin SABIT esikler: yil degisince renk anlami degismez.
 *  5 sinif: 7 sinifla iki temada da --ordinal gecen bir rampa yok (renkler.ts). */
export const ESIKLER = [0.02, 0.05, 0.1, 0.2];
export const SINIF_ETIKETI = ["< %2", "%2–5", "%5–10", "%10–20", "≥ %20"];
export const sinif = (oran: number) => ESIKLER.filter((e) => oran >= e).length;

interface Aktif {
  ad: string;
  oge?: EyaletOzeti;
}

export function EyaletHaritasi({ satirlar, yil }: { satirlar: EyaletOzeti[]; yil: number }) {
  const r = useRenkler();
  const [aktif, setAktif] = useState<Aktif>();
  const veri = new Map(satirlar.map((s) => [s.eyalet, s]));

  const dolgu = (oge?: EyaletOzeti) => {
    if (!oge) return r.haritaYok;
    if (oge.gizli || oge.batti_orani === null) return "url(#yetersiz-veri)";
    return r.harita[sinif(oge.batti_orani)];
  };

  return (
    <>
      <div className="harita-kap">
        <ComposableMap projection="geoAlbersUsa" width={975} height={610} projectionConfig={{ scale: 1280 }}>
          <defs>
            <pattern id="yetersiz-veri" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="7" height="7" fill={r.zemin} />
              <line x1="0" y1="0" x2="0" y2="7" stroke={r.tarama} strokeWidth="2" />
            </pattern>
          </defs>
          <Geographies geography={abd}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const posta = POSTA[String(geo.id)];
                const oge = posta ? veri.get(posta) : undefined;
                const ad = `${geo.properties.name}${posta ? ` (${posta})` : ""}`;
                const sec = () => setAktif({ ad, oge });
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    className="harita-eyalet"
                    fill={dolgu(oge)}
                    stroke={r.zemin}
                    strokeWidth={0.75}
                    tabIndex={0}
                    aria-label={ad}
                    onMouseEnter={sec}
                    onFocus={sec}
                    onClick={sec}
                    style={{
                      default: { outline: "none" },
                      hover: { outline: "none", stroke: r.murekkep, strokeWidth: 1.5 },
                      pressed: { outline: "none" },
                    }}
                  />
                );
              })
            }
          </Geographies>
        </ComposableMap>
      </div>
      <div className="harita-bilgi" aria-live="polite">
        {aktif ? (
          <>
            <strong>{aktif.ad}</strong> · {yil} kredileri:{" "}
            {!aktif.oge
              ? "veri yok"
              : aktif.oge.gizli
                ? "yetersiz veri (30'dan az kredi, gizlendi)"
                : `battı oranı ${yuzde(aktif.oge.batti_orani!, 1)} · ${sayi(aktif.oge.kredi_sayisi!)} kredi`}
          </>
        ) : (
          <span className="ikincil">Ayrıntı için bir eyaletin üzerine gelin veya dokunun.</span>
        )}
      </div>
    </>
  );
}
