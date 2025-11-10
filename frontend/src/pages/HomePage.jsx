import React from "react";
import { useNavigate } from "react-router-dom";

function Home() {
  const navigate = useNavigate();

  return (
    <div style={{ textAlign: "center", marginTop: "80px" }}>
      <h1>🏠 Sistema de Leilões</h1>
      <p>Escolha uma opção abaixo:</p>

      <div style={{ display: "flex", justifyContent: "center", gap: "20px", marginTop: "30px" }}>
        <button onClick={() => navigate("/leiloes")}>Leilões</button>
        <button onClick={() => navigate("/lances")}>Lances</button>
        <button onClick={() => navigate("/interesses")}>Interesses</button>
      </div>
    </div>
  );
}

export default Home;
