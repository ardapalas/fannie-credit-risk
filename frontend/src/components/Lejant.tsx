// Grafiklerin HTML lejanti: kimlik hicbir zaman yalnizca renkle verilmez (her ogenin adi yazilir).
export interface LejantOgesi {
  ad: string;
  renk: string;
  tur?: "kare" | "cizgi" | "kesik";
  soluk?: boolean;
}

export function Lejant({ ogeler }: { ogeler: LejantOgesi[] }) {
  return (
    <div className="lejant">
      {ogeler.map((o) => (
        <span className="lejant-oge" key={o.ad}>
          {o.tur === "kare" || !o.tur ? (
            <span className="isaret-kare" style={{ background: o.renk }} />
          ) : (
            <span
              className={`isaret-cizgi ${o.tur === "kesik" ? "kesik" : ""}`}
              style={{ borderTopColor: o.renk, opacity: o.soluk ? 0.45 : 1 }}
            />
          )}
          {o.ad}
        </span>
      ))}
    </div>
  );
}
