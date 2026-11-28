import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { RENKLER, type GrafikRenkleri, type TemaAdi } from "./renkler";

type Tercih = TemaAdi | "sistem";
const ANAHTAR = "kredi-riski-tema";

interface TemaBaglami {
  tema: TemaAdi; // cozulmus tema
  tercih: Tercih;
  degistir: () => void;
}

const Baglam = createContext<TemaBaglami | null>(null);

function kayitliTercih(): Tercih {
  try {
    const v = localStorage.getItem(ANAHTAR);
    return v === "acik" || v === "koyu" ? v : "sistem";
  } catch {
    return "sistem"; // gizli pencere / engellenmis depolama
  }
}

function sistemTemasi(): TemaAdi {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "koyu" : "acik";
}

export function TemaSaglayici({ children }: { children: ReactNode }) {
  const [tercih, setTercih] = useState<Tercih>(kayitliTercih);
  const [sistem, setSistem] = useState<TemaAdi>(sistemTemasi);

  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return;
    const dinle = () => setSistem(mq.matches ? "koyu" : "acik");
    mq.addEventListener("change", dinle);
    return () => mq.removeEventListener("change", dinle);
  }, []);

  const tema: TemaAdi = tercih === "sistem" ? sistem : tercih;

  useEffect(() => {
    document.documentElement.dataset.theme = tema === "koyu" ? "dark" : "light";
  }, [tema]);

  const deger = useMemo<TemaBaglami>(
    () => ({
      tema,
      tercih,
      degistir: () => {
        const yeni: TemaAdi = tema === "koyu" ? "acik" : "koyu";
        setTercih(yeni);
        try {
          localStorage.setItem(ANAHTAR, yeni);
        } catch {
          /* depolama yoksa sadece bu oturumda gecerli */
        }
      },
    }),
    [tema, tercih],
  );

  return <Baglam.Provider value={deger}>{children}</Baglam.Provider>;
}

export function useTema(): TemaBaglami {
  const b = useContext(Baglam);
  if (!b) throw new Error("useTema TemaSaglayici icinde kullanilmali");
  return b;
}

export function useRenkler(): GrafikRenkleri {
  return RENKLER[useTema().tema];
}
