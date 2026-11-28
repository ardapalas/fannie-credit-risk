import { NavLink, Outlet } from "react-router-dom";
import { useTema } from "../tema/Tema";

const SAYFALAR = [
  { yol: "/", ad: "Genel bakış" },
  { yol: "/kusaklar", ad: "Kuşaklar" },
  { yol: "/harita", ad: "Eyalet haritası" },
  { yol: "/senaryo", ad: "Senaryo analizi" },
];

export function Yerlesim() {
  const { tema, degistir } = useTema();
  return (
    <>
      <header className="ust">
        <div className="ust-ic">
          <NavLink to="/" className="marka">
            Kredi Riski <span>· Fannie Mae 2005–2012</span>
          </NavLink>
          <nav className="menu" aria-label="Sayfalar">
            {SAYFALAR.map((s) => (
              <NavLink key={s.yol} to={s.yol} end className={({ isActive }) => (isActive ? "aktif" : "")}>
                {s.ad}
              </NavLink>
            ))}
          </nav>
          <button className="dugme" onClick={degistir} aria-label="Temayı değiştir">
            {tema === "koyu" ? "☀ Açık tema" : "☾ Koyu tema"}
          </button>
        </div>
      </header>
      <main className="icerik">
        <Outlet />
      </main>
      <footer className="alt">
        Araştırma prototipi (İKÜ bitirme projesi). Model 2005–2012 Fannie Mae verisiyle eğitildi; gösterilen
        değerler toplulaştırılmıştır, tekil kredi bilgisi içermez. Kredi kararı için kullanılamaz.
      </footer>
    </>
  );
}
