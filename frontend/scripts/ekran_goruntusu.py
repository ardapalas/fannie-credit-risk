"""Arayuzun ekran goruntuleri (gelistirme araci; requirements-dev.txt -> playwright).

Kullanim (once API ve `npm run dev` calisiyor olmali):
    python frontend/scripts/ekran_goruntusu.py CIKTI_DIZINI [--adres http://localhost:5173]

Her sayfa: acik/koyu tema x masaustu (1280) / telefon (390). Ek olarak "API kapali" durumu
(API istekleri tarayicida kesilerek, backend durdurulmadan). Tarayici konsol hatalarini raporlar.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SAYFALAR = {"genel": "/", "kusaklar": "/kusaklar", "harita": "/harita", "senaryo": "/senaryo"}
EKRANLAR = {"masaustu": {"width": 1280, "height": 900}, "telefon": {"width": 390, "height": 844}}
TEMALAR = {"acik": "acik", "koyu": "koyu"}


def main():
    cikti = Path(sys.argv[1])
    adres = sys.argv[sys.argv.index("--adres") + 1] if "--adres" in sys.argv else "http://localhost:5173"
    cikti.mkdir(parents=True, exist_ok=True)
    hatalar = []

    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        for tema in TEMALAR:
            for ekran_ad, boyut in EKRANLAR.items():
                baglam = tarayici.new_context(viewport=boyut, device_scale_factor=1)
                baglam.add_init_script(f"localStorage.setItem('kredi-riski-tema', '{tema}')")
                sayfa = baglam.new_page()
                sayfa.on("console", lambda m: m.type == "error" and hatalar.append(m.text))
                sayfa.on("pageerror", lambda e: hatalar.append(str(e)))
                for ad, yol in SAYFALAR.items():
                    sayfa.goto(adres + yol, wait_until="networkidle")
                    sayfa.wait_for_selector(".recharts-surface, .harita-kap svg, table", timeout=15_000)
                    sayfa.wait_for_timeout(400)
                    yol_png = cikti / f"{ad}_{tema}_{ekran_ad}.png"
                    sayfa.screenshot(path=str(yol_png), full_page=True)
                    print("kaydedildi:", yol_png.name)
                baglam.close()

        # API kapali durumu: API'ye giden istekler kesilir
        baglam = tarayici.new_context(viewport=EKRANLAR["masaustu"])
        baglam.add_init_script("localStorage.setItem('kredi-riski-tema', 'acik')")
        sayfa = baglam.new_page()
        sayfa.route("http://localhost:8000/**", lambda r: r.abort("connectionrefused"))
        sayfa.goto(adres + "/senaryo", wait_until="networkidle")
        sayfa.wait_for_selector(".hata-kutu", timeout=20_000)
        sayfa.screenshot(path=str(cikti / "api_kapali.png"), full_page=True)
        print("kaydedildi: api_kapali.png")
        # Desen kontrolu: gercek veride gizli hucreler sadece haritada cizilmeyen GU/VI'da.
        # Taralı desenin cizildigini gormek icin /states yanitini TARAYICIDA degistir (test amacli).
        def gizle(route):
            yanit = route.fetch()
            satirlar = yanit.json()
            for s in satirlar:
                if s["eyalet"] in ("WY", "MT", "ND", "VT"):
                    s.update(kredi_sayisi=None, batti_orani=None, gizli=True)
            route.fulfill(response=yanit, json=satirlar)

        for tema in TEMALAR:
            baglam = tarayici.new_context(viewport=EKRANLAR["masaustu"])
            baglam.add_init_script(f"localStorage.setItem('kredi-riski-tema', '{tema}')")
            sayfa = baglam.new_page()
            sayfa.route("http://localhost:8000/states*", gizle)
            sayfa.goto(adres + "/harita", wait_until="networkidle")
            sayfa.wait_for_selector(".harita-kap svg")
            sayfa.locator(".harita-kap").screenshot(path=str(cikti / f"desen_kontrolu_{tema}.png"))
            print(f"kaydedildi: desen_kontrolu_{tema}.png (test: WY, MT, ND, VT gizli isaretlendi)")
            baglam.close()
        tarayici.close()

    # Kesilen istekler bilerek hata uretir; onlar disindakiler sorun
    gercek = [h for h in hatalar if "ERR_CONNECTION_REFUSED" not in h and "Failed to load resource" not in h]
    print(f"\ntarayici konsol hatasi: {len(gercek)}")
    for h in gercek[:10]:
        print("  -", h[:200])


if __name__ == "__main__":
    main()
