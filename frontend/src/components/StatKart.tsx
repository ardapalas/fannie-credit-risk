export function StatKart({ etiket, deger, not }: { etiket: string; deger: string; not?: string }) {
  return (
    <div className="kart">
      <div className="stat-etiket">{etiket}</div>
      <div className="stat-deger sayi">{deger}</div>
      {not && <div className="stat-not">{not}</div>}
    </div>
  );
}
