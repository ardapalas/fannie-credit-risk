// API endpoint'leri: tum fetch islemleri buradan gecer.
import { apiGet } from "./client";
import type {
  EyaletOzeti,
  KusakOzeti,
  ModelMetrigi,
  Olay,
  Saglik,
  SenaryoParametreleri,
  SenaryoSonucu,
  VintageSerisi,
} from "./types";

export const api = {
  saglik: (signal?: AbortSignal) => apiGet<Saglik>("/health", undefined, signal),

  kusaklar: (signal?: AbortSignal) => apiGet<KusakOzeti[]>("/cohorts", undefined, signal),

  vintagelar: (ceyrek: string, olay?: Olay, signal?: AbortSignal) =>
    apiGet<VintageSerisi[]>("/vintages", { ceyrek, olay }, signal),

  /** yil verilmezse tum yillar (431 hucre) */
  eyaletler: (yil?: number, signal?: AbortSignal) => apiGet<EyaletOzeti[]>("/states", { yil }, signal),

  metrikler: (bolum?: "dogrulama" | "test", signal?: AbortSignal) =>
    apiGet<ModelMetrigi[]>("/model/metrics", { bolum }, signal),

  senaryo: (p: SenaryoParametreleri, signal?: AbortSignal) =>
    apiGet<SenaryoSonucu>("/scenarios", { issizlik: p.issizlik, ev_fiyati: p.ev_fiyati, faiz: p.faiz }, signal),
};
