import { useCallback, useEffect, useState } from "react";

export interface ApiDurumu<T> {
  veri: T | undefined;
  yukleniyor: boolean;
  hata: Error | undefined;
  tekrarDene: () => void;
}

/**
 * Bir API cagrisini yukleniyor / hata / veri durumlariyla calistirir.
 * `anahtar` degisince yeniden ceker; bilesen kapaninca istek iptal edilir.
 */
export function useApi<T>(getir: (signal: AbortSignal) => Promise<T>, anahtar: string): ApiDurumu<T> {
  const [veri, setVeri] = useState<T>();
  const [hata, setHata] = useState<Error>();
  const [yukleniyor, setYukleniyor] = useState(true);
  const [deneme, setDeneme] = useState(0);

  useEffect(() => {
    const iptal = new AbortController();
    setYukleniyor(true);
    setHata(undefined);
    getir(iptal.signal)
      .then((v) => {
        if (!iptal.signal.aborted) setVeri(v);
      })
      .catch((e: unknown) => {
        if (!iptal.signal.aborted) setHata(e instanceof Error ? e : new Error(String(e)));
      })
      .finally(() => {
        if (!iptal.signal.aborted) setYukleniyor(false);
      });
    return () => iptal.abort();
    // getir her render'da yeni olabilir; yeniden cekmeyi `anahtar` belirler
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anahtar, deneme]);

  const tekrarDene = useCallback(() => setDeneme((d) => d + 1), []);
  return { veri, yukleniyor, hata, tekrarDene };
}
