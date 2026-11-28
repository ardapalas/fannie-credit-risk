// Tek HTTP istemcisi: adres VITE_API_URL'den, zaman asimi, anlasilir Turkce hata mesajlari.

export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const ZAMAN_ASIMI_MS = 15_000;

export class ApiHatasi extends Error {
  constructor(
    message: string,
    readonly tur: "baglanti" | "zaman_asimi" | "sunucu" | "istek",
    readonly durum?: number,
  ) {
    super(message);
    this.name = "ApiHatasi";
  }
}

type Parametreler = Record<string, string | number | undefined | null>;

export async function apiGet<T>(yol: string, parametreler?: Parametreler, signal?: AbortSignal): Promise<T> {
  const url = new URL(API_URL + yol);
  for (const [anahtar, deger] of Object.entries(parametreler ?? {})) {
    if (deger !== undefined && deger !== null && deger !== "") url.searchParams.set(anahtar, String(deger));
  }

  const zamanAsimi = AbortSignal.timeout(ZAMAN_ASIMI_MS);
  const birlesik = signal ? AbortSignal.any([signal, zamanAsimi]) : zamanAsimi;

  let yanit: Response;
  try {
    yanit = await fetch(url, { signal: birlesik, headers: { Accept: "application/json" } });
  } catch (e) {
    if (signal?.aborted) throw e; // bilesen kapandi: sessizce iptal
    if (zamanAsimi.aborted) {
      throw new ApiHatasi(`API ${ZAMAN_ASIMI_MS / 1000} saniye içinde yanıt vermedi (${API_URL}).`, "zaman_asimi");
    }
    // Nasil baslatilacagi arayuzde (HataKutusu) gosterilir; burada sadece ne oldugu
    throw new ApiHatasi(`Sunucu yanıt vermiyor: ${API_URL}`, "baglanti");
  }

  if (!yanit.ok) {
    let ayrinti = "";
    try {
      const govde = await yanit.json();
      ayrinti = typeof govde?.detail === "string" ? govde.detail : "";
    } catch {
      /* govde JSON degil */
    }
    const tur = yanit.status >= 500 ? "sunucu" : "istek";
    throw new ApiHatasi(`API hatası (${yanit.status})${ayrinti ? `: ${ayrinti}` : ""}`, tur, yanit.status);
  }
  return (await yanit.json()) as T;
}
