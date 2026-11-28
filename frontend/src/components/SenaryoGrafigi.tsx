import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SenaryoAyi } from "../api/types";
import { eksenYuzde, guzelTikler, yuzde } from "../bicim";
import { useRenkler } from "../tema/Tema";
import { Lejant } from "./Lejant";

interface Props {
  olay: "batma" | "erken";
  secili: SenaryoAyi[];
  baz: SenaryoAyi[];
  bazMi: boolean;
}

/** Secili senaryo (kalin) ve her zaman soluk baz senaryo; olay rengi tum uygulamada ayni. */
export function SenaryoGrafigi({ olay, secili, baz, bazMi }: Props) {
  const r = useRenkler();
  const renk = olay === "batma" ? r.batma : r.erken;
  const baslik = olay === "batma" ? "Birikimli batma" : "Birikimli erken kapanış";
  const veri = secili.map((a, i) => ({ ay: a.ay, secili: a[olay], baz: baz[i]?.[olay] }));
  const tikler = guzelTikler(Math.max(...veri.map((v) => Math.max(v.secili, v.baz ?? 0))));

  return (
    <div>
      <h3 className="panel-basligi">
        <span className="isaret-kare" style={{ background: renk }} aria-hidden="true" />
        {baslik}
      </h3>
      <Lejant
        ogeler={[
          { ad: "Seçili senaryo", renk, tur: "cizgi" },
          ...(bazMi ? [] : [{ ad: "Baz (0 / 0 / 0)", renk, tur: "kesik" as const, soluk: true }]),
        ]}
      />
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={veri} margin={{ top: 8, right: 12, bottom: 18, left: 0 }}>
          <CartesianGrid vertical={false} stroke={r.izgara} />
          <XAxis
            dataKey="ay"
            type="number"
            domain={[1, 36]}
            ticks={[1, 6, 12, 18, 24, 30, 36]}
            tick={{ fill: r.soluk, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: r.eksen }}
            label={{ value: "Senaryo ayı (1 = Ocak 2010)", position: "insideBottom", offset: -12, fill: r.ikincil, fontSize: 12 }}
          />
          <YAxis
            ticks={tikler}
            domain={[0, tikler[tikler.length - 1]]}
            tickFormatter={eksenYuzde}
            tick={{ fill: r.soluk, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip
            contentStyle={{ background: r.zemin, border: `1px solid ${r.eksen}`, borderRadius: 6, color: r.murekkep }}
            labelFormatter={(a) => `${a}. ay`}
            formatter={(v: number, ad: string) => [yuzde(v, 2), ad === "secili" ? "Seçili senaryo" : "Baz"]}
          />
          {!bazMi && (
            <Line dataKey="baz" stroke={renk} strokeOpacity={0.4} strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
          )}
          <Line dataKey="secili" stroke={renk} strokeWidth={2.75} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
