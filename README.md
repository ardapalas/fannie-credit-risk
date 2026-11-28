# Fannie Mae Konut Kredisi Risk Modeli

İKÜ Matematik-Bilgisayar bitirme projesi. Bir konut kredisinin batıp batmayacağını ve **ne zaman**
batacağını aylık bazda tahmin eden ayrık zamanlı hazard modeli; erken kapanış ayrı bir yarışan risk.
Nihai model: kalibre LightGBM (etiket `model-v1`, dondurulmuş).

> **Veri lisansı:** Fannie Mae Single-Family Loan Performance verisi paylaşılamaz. Bu repoda veri,
> model dosyaları ve kredi bazında hiçbir kayıt yoktur; sadece kod ve toplulaştırılmış sonuçlar
> (`reports/`) bulunur. Kodu çalıştırmak için veriyi Fannie Mae'den kendiniz indirmeniz gerekir.

## Kurulum

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # değerleri doldurun; .env asla commit edilmez
```

## Backend (FastAPI)

Backend sadece **toplulaştırılmış** veri sunar (vintage eğrileri, kuşak ve eyalet özetleri, model
metrikleri, önceden hesaplanmış stres senaryoları). 30'dan az kredi içeren hücreler gizlenir.

### 1. Veritabanı

PostgreSQL (Docker gerekli):

```powershell
docker compose up -d
```

API varsayılan olarak `.env`'deki `DATABASE_URL`'yi kullanır. Kullanıcı ve şifre `POSTGRES_*`
değerleriyle aynı olmalı (şifresiz örnek, `.env.example`'da):

```
POSTGRES_USER=kredi
POSTGRES_PASSWORD=SIFRE_BURAYA
POSTGRES_DB=kredi_riski
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://kredi:SIFRE_BURAYA@localhost:5432/kredi_riski
```

`DATABASE_URL` tanımlı değilse yerel geliştirme için `data/api.db` (SQLite) kullanılır.
Testler her zaman bellek içi SQLite kullanır.

### 2. Verileri veritabanına yazma

Model eğitilmez; dondurulmuş modeller ve kayıtlı sonuçlar okunur.

```powershell
python src/export/statik_export.py     # vintage_egri, kusak_ozet, eyalet_ozet, model_metrik (~1 dk)
python src/export/senaryo_izgara.py    # senaryo_sonuc: 48 senaryo (~2 saat)
```

Senaryo ızgarası uzun sürer; yarıda kalırsa aynı komutu tekrar çalıştırın, hesaplanmış senaryolar
atlanır.

Izgara SQLite'ta (`data/api.db`) hesaplandıysa Postgres'e kopyalayın (`DATABASE_URL` Postgres'i
göstermeli). Script tablo değerlerini de karşılaştırır; ızgara eksikse kopyalamaz:

```powershell
python src/export/postgrese_kopyala.py                # senaryo_sonuc kopyala + tüm tabloları karşılaştır
python src/export/postgrese_kopyala.py --karsilastir  # sadece karşılaştır, yazmaz
```

### 3. API'yi çalıştırma

```powershell
uvicorn api.main:app --reload
```

Swagger arayüzü: <http://localhost:8000/docs>

| Endpoint | Açıklama |
|---|---|
| `GET /health` | Sağlık kontrolü, hesaplanmış senaryo sayısı |
| `GET /vintages?ceyrek=&olay=` | Kuşak bazında birikimli batma / erken kapanış eğrileri (gerçek ve model) |
| `GET /cohorts` | Kuşak (çeyrek) özetleri |
| `GET /states?yil=` | Eyalet × yıl battı oranları (küçük hücreler gizli) |
| `GET /model/metrics?bolum=` | Doğrulama ve test metrikleri |
| `GET /scenarios?issizlik=&ev_fiyati=&faiz=` | Izgaradaki en yakın stres senaryosu; aralık dışı değer 422 |

### Docker ile çalıştırma

Veritabanı ve API birlikte konteynerde çalışır. `.env` dosyasında `POSTGRES_*` değerleri tanımlı
olmalı (bkz. `.env.example`); API'nin `DATABASE_URL`'si compose içinde bu değerlerden kurulur.

```powershell
docker compose up -d --build     # db + api; api, db sağlıklı olunca başlar
docker compose ps                # durum
docker compose logs -f api       # API logları
docker compose down              # durdur (veri "pgdata" volume'unda kalır)
```

API: <http://localhost:8000/docs>. Veritabanı konteynerde boşsa tabloları host'tan doldurun
(`.env`'deki `DATABASE_URL` `localhost`'u gösterir, compose 5432 portunu dışarı açar):

```powershell
python src/export/statik_export.py
python src/export/senaryo_izgara.py     # veya SQLite'tan: python src/export/postgrese_kopyala.py
```

- İmaja sadece `api/` ve `requirements-api.txt` girer (`.dockerignore` beyaz liste). Fannie verisi,
  `.env`, `models/`, notebook'lar ve raporlar imajda yoktur.
- `requirements-api.txt` sadece API'nin ve model yüklemenin ihtiyacı olan paketleri içerir (imaj
  ~740 MB; `requirements.txt` ile ~3 GB). Sürümler `requirements.txt` ile birebir aynıdır: dondurulmuş
  modeller aynı lightgbm / scikit-learn / pandas sürümleriyle yüklenmelidir.
- `models/` konteynere **salt okunur** volume olarak bağlanır (`/app/models`); modeller dondurulmuştur.
- Konteyner root olmayan `uygulama` kullanıcısıyla çalışır.

### Testler

```powershell
python -m pytest
```

Testler bellek içi SQLite ve sentetik veriyle çalışır; gerçek veri gerektirmez.

## Proje yapısı

- `src/data/` — veri hazırlama (Fannie Mae CSV → kredi-ay tablosu, FRED makro verisi)
- `src/model/` — modeller, kalibrasyon, değerlendirme, SHAP, stres testi
- `src/export/` — toplulaştırılmış sonuçları veritabanına yazan scriptler
- `api/` — FastAPI backend (`rest` → `service` → `integration` katmanları)
- `reports/` — toplulaştırılmış şekil ve tablolar
