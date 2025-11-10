import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/HomePage";
import Leiloes from "./pages/LeiloesPage";
import Lances from "./pages/LancesPage.jsx";
import Interesses from "./pages/InteressesPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/leiloes" element={<Leiloes />} />
        <Route path="/lances" element={<Lances />} />
        <Route path="/interesses" element={<Interesses />} />
      </Routes>
    </Router>
  );
}

export default App;
