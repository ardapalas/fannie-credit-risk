import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Yerlesim } from "./components/Yerlesim";
import { GenelBakis } from "./pages/GenelBakis";
import { Harita } from "./pages/Harita";
import { Kusaklar } from "./pages/Kusaklar";
import { Senaryo } from "./pages/Senaryo";
import { TemaSaglayici } from "./tema/Tema";

export function App() {
  return (
    <TemaSaglayici>
      <BrowserRouter>
        <Routes>
          <Route element={<Yerlesim />}>
            <Route index element={<GenelBakis />} />
            <Route path="kusaklar" element={<Kusaklar />} />
            <Route path="harita" element={<Harita />} />
            <Route path="senaryo" element={<Senaryo />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TemaSaglayici>
  );
}
