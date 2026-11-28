import type { ReactNode } from "react";
import { ApiHatasi } from "../api/client";
import type { ApiDurumu } from "../hooks/useApi";

export function Yukleniyor({ metin = "Yükleniyor…" }: { metin?: string }) {
  return (
    <div className="durum" role="status" aria-live="polite">
      <span className="donen" aria-hidden="true" />
      {metin}
    </div>
  );
}

export function HataKutusu({ hata, tekrarDene }: { hata: Error; tekrarDene?: () => void }) {
  const baglanti = hata instanceof ApiHatasi && hata.tur === "baglanti";
  return (
    <div className="hata-kutu" role="alert">
      <strong>{baglanti ? "API'ye ulaşılamıyor" : "Veri alınamadı"}</strong>
      <p style={{ margin: "0.35rem 0 0.6rem" }}>{hata.message}</p>
      {baglanti && (
        <p className="kucuk ikincil">
          Backend'i başlatın: <code>docker compose up -d</code> — ya da yerelde{" "}
          <code>uvicorn api.main:app</code>.
        </p>
      )}
      {tekrarDene && (
        <button className="dugme" onClick={tekrarDene}>
          Tekrar dene
        </button>
      )}
    </div>
  );
}

/** Yukleniyor / hata / veri durumlarini tek yerden ele alir. */
export function VeriDurumu<T>({
  durum,
  children,
  yukleniyorMetni,
}: {
  durum: ApiDurumu<T>;
  children: (veri: T) => ReactNode;
  yukleniyorMetni?: string;
}) {
  if (durum.hata) return <HataKutusu hata={durum.hata} tekrarDene={durum.tekrarDene} />;
  if (durum.veri === undefined) return <Yukleniyor metin={yukleniyorMetni} />;
  return <>{children(durum.veri)}</>;
}
