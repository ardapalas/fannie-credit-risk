import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { KusakOzeti } from "../api/types";
import { BOLUM_ADI, eksenYuzde, sayi, yuzde } from "../bicim";
import { useRenkler } from "../tema/Tema";
import { Lejant } from "./Lejant";

interface Props {
  kusaklar: KusakOzeti[];
  secili: string[];
  sec: (ceyrek: string) => void;
}

export function KusakCubukGrafigi({ kusaklar, secili, sec }: Props) {
  const r = useRenkler();
  return (
    <>
      <Lejant
        ogeler={(["egitim", "dogrulama", "test"] as const).map((b) => ({ ad: BOLUM_ADI[b], renk: r.bolum[b] }))}
      />
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={kusaklar} margin={{ top: 8, right: 8, bottom: 4, left: 0 }} barCategoryGap={2}>
          <CartesianGrid vertical={false} stroke={r.izgara} />
          <XAxis
            dataKey="ceyrek"
            interval={0}
            tickFormatter={(c: string) => (c.endsWith("Q1") ? c.slice(0, 4) : "")}
            tick={{ fill: r.soluk, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: r.eksen }}
          />
          <YAxis
            tickFormatter={eksenYuzde}
            tick={{ fill: r.soluk, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={44}
          />
          <Tooltip
            cursor={{ fill: r.izgara, opacity: 0.5 }}
            contentStyle={{ background: r.zemin, border: `1px solid ${r.eksen}`, borderRadius: 6, color: r.murekkep }}
            labelStyle={{ color: r.murekkep, fontWeight: 600 }}
            formatter={(v: number, _ad, oge) => [
              `${yuzde(v, 1)} · ${sayi((oge.payload as KusakOzeti).kredi_sayisi)} kredi`,
              "Battı oranı",
            ]}
          />
          <Bar
            dataKey="batti_orani"
            radius={[4, 4, 0, 0]}
            cursor="pointer"
            isAnimationActive={false}
            onClick={(d: { payload?: KusakOzeti }) => d.payload && sec(d.payload.ceyrek)}
          >
            {kusaklar.map((k) => (
              <Cell
                key={k.ceyrek}
                fill={r.bolum[k.bolum]}
                stroke={secili.includes(k.ceyrek) ? r.murekkep : r.zemin}
                strokeWidth={secili.includes(k.ceyrek) ? 2 : 1}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="kucuk ikincil">
        Gözlem sonuna (Şubat 2020) kadar batan kredilerin payı. Son kuşaklar daha kısa süre izlendiği için
        oranları doğal olarak düşüktür. Bir çubuğa tıklayarak kuşağı karşılaştırmaya ekleyin.
      </p>
    </>
  );
}
