"""FastAPI uygulamasi.

Calistirma (proje kok dizininden):
    uvicorn api.main:app --reload
Swagger: http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import ayarlari_al
from api.rest import okuma

ACIKLAMA = """
Fannie Mae konut kredisi risk modeli (bitirme projesi) icin okuma API'si.

* Sadece **toplulastirilmis** veri sunulur; kredi bazinda kayit yoktur (Fannie Mae lisansi).
  30'dan az kredi iceren hucreler gizlenir.
* Modeller dondurulmustur (**model-v1**): kalibre LightGBM, yarisan riskler (batma / erken kapanis).
* Stres senaryolari onceden hesaplanmis bir izgaradan okunur.
"""

app = FastAPI(title="Kredi Riski API", version="model-v1", description=ACIKLAMA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ayarlari_al().cors_origins,     # React gelistirme sunucusu (localhost)
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(okuma.router)
