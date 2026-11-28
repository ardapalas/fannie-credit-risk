import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Olay, VintageSerisi } from "../api/types";
import { eksenYuzde, guzelTikler, OLAY_ADI, yuzde } from "../bicim";
import { useRenkler } from "../tema/Tema";

interface Props {
  olay: Olay;
  seriler: VintageSerisi[]; // secili kusaklarin tum serileri
  renkler: Record<string, string>; // kusak -> sabit renk (kusagi izler)
}

/** Bir olay icin secili kusaklarin birikimli egrileri. Renk = kusak; duz = gercek, kesikli = LightGBM. */
export function VintageGrafigi({ olay, seriler, renkler }: Props) {
  const r = useRenkler();
  const ilgili = seriler.filter((s) => s.olay === olay);

  // yas -> { "2009Q1|gercek": deger, ... }
  const tablo = new Map<number, Record<string, number>>();
  for (const s of ilgili) {
    for (const n of s.noktalar) {
      const satir = tablo.get(n.yas) ?? { yas: n.yas };
      satir[`${s.ceyrek}|${s.seri}`] = n.deger;
      tablo.set(n.yas, satir);
    }
  }
  const veri = [...tablo.values()].sort((a, b) => a.yas - b.yas);
  const renk = (c: string) => renkler[c] ?? r.ikincil;
  const tikler = guzelTikler(Math.max(0, ...ilgili.flatMap((s) => s.noktalar.map((n) => n.deger))));

  // Dogrudan etiket: gercek egrinin son noktasina kusak adi (kimlik yalnizca renge kalmasin;
  // acik temada bir kusak renginin kontrasti 3:1'in altinda). Metin rengi metin murekkebi.
  const sonYas = (c: string) => {
    const s = ilgili.find((x) => x.ceyrek === c && x.seri === "gercek");
    return s?.noktalar[s.noktalar.length - 1]?.yas;
  };
  const etiket = (c: string) =>
    function Etiket(p: { x?: number; y?: number; index?: number }) {
      if (p.x === undefined || p.y === undefined || p.index === undefined) return <g />;
      if (veri[p.index]?.yas !== sonYas(c)) return <g />;
      return (
        <text x={p.x - 4} y={p.y - 6} textAnchor="end" fontSize={11} fill={r.murekkep} stroke={r.zemin}
          strokeWidth={3} paintOrder="stroke">
          {c}
        </text>
      );
    };

  return (
    <div>
      <h3 className="panel-basligi">
        <span className="isaret-kare" style={{ background: olay === "batti" ? r.batma : r.erken }} aria-hidden="true" />
        Birikimli {OLAY_ADI[olay].toLowerCase()}
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={veri} margin={{ top: 20, right: 12, bottom: 18, left: 0 }}>
          <CartesianGrid vertical={false} stroke={r.izgara} />
          <XAxis
            dataKey="yas"
            type="number"
            domain={[0, "dataMax"]}
            ticks={[0, 24, 48, 72, 96, 120, 144]}
            tick={{ fill: r.soluk, fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: r.eksen }}
            label={{ value: "Kredi yaşı (ay)", position: "insideBottom", offset: -12, fill: r.ikincil, fontSize: 12 }}
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
            labelFormatter={(y) => `${y}. ay`}
            formatter={(v: number, ad: string) => {
              const [c, seri] = ad.split("|");
              return [yuzde(v, 2), `${c} ${seri === "lgbm" ? "(LightGBM)" : "(gerçek)"}`];
            }}
          />
          {ilgili.map((s) => (
            <Line
              key={`${s.ceyrek}|${s.seri}`}
              dataKey={`${s.ceyrek}|${s.seri}`}
              stroke={renk(s.ceyrek)}
              strokeWidth={2}
              strokeDasharray={s.seri === "lgbm" ? "6 4" : undefined}
              dot={false}
              connectNulls
              isAnimationActive={false}
              label={s.seri === "gercek" ? etiket(s.ceyrek) : undefined}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
