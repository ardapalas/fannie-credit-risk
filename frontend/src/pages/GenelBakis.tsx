import { api } from "../api/endpoints";
import { VeriDurumu } from "../components/Durum";
import { MetrikTablosu } from "../components/MetrikTablosu";
import { StatKart } from "../components/StatKart";
import { ondalik, sayi, yuzde } from "../bicim";
import { useApi } from "../hooks/useApi";

export function GenelBakis() {
  const kusaklar = useApi((s) => api.kusaklar(s), "kusaklar");
  const metrikler = useApi((s) => api.metrikler(undefined, s), "metrikler");

  const testMetrik = (ad: string) =>
    metrikler.veri?.find((m) => m.metrik === ad && m.model === "LightGBM" && m.bolum === "test" && m.durum === "sonra")
      ?.deger;
  const auc = testMetrik("batma_auc");
  const yakala = testMetrik("batma_yakala_10");

  return (
    <>
      <div className="sayfa-basi">
        <h1>Genel bakış</h1>
        <p>
          Bir konut kredisinin batıp batmayacağını ve ne zaman batacağını aylık bazda tahmin eden, erken
          kapanışı ayrı bir yarışan risk olarak ele alan ayrık zamanlı hazard modeli.
        </p>
      </div>

      <VeriDurumu durum={kusaklar}>
        {(k) => (
          <div className="izgara izgara-4" style={{ marginBottom: "1rem" }}>
            <StatKart
              etiket="Kredi"
              deger={sayi(k.reduce((t, x) => t + x.kredi_sayisi, 0))}
              not="Her çeyrekten kredilerin %5'i"
            />
            <StatKart etiket="Kuşak" deger={sayi(k.length)} not="2005Q1 – 2012Q4 (çeyrek)" />
            <StatKart
              etiket="Test batma AUC"
              deger={auc === undefined ? "—" : ondalik(auc, 3)}
              not="LightGBM, 2010–2012 kredileri"
            />
            <StatKart
              etiket="En riskli %10'un yakaladığı batma"
              deger={yakala === undefined ? "—" : yuzde(yakala, 0)}
              not="Test; rastgele seçimde %10 olurdu"
            />
          </div>
        )}
      </VeriDurumu>

      <section className="kart">
        <h2>Model karşılaştırması</h2>
        <p className="ikincil kucuk">
          Üç model, aynı özellikler ve ağırlıklarla. Doğrulama: 2009 kredileri; test: 2010–2012 kredileri (bir
          kez açıldı, modeller dondurulmuş).
        </p>
        <VeriDurumu durum={metrikler}>{(m) => <MetrikTablosu metrikler={m} />}</VeriDurumu>
      </section>

      <div className="not" style={{ marginTop: "1rem" }}>
        <strong>Araştırma prototipi.</strong> Model 2005–2012 yıllarında verilen Fannie Mae kredileriyle
        eğitildi ve değerlendirildi (gözlem Şubat 2020'de kesiliyor). Sonuçlar bu dönemin koşullarını yansıtır;
        bugünkü krediler için doğrudan kullanılamaz.
      </div>
    </>
  );
}
