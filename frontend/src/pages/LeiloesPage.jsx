import { useEffect, useState } from "react";
import api from '../services/APIService';

export default function LeiloesPage() {
  const [leiloes, setLeiloes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const carregarLeiloes = async () => {
      try {
        const response = await api.get("/leiloes");
        setLeiloes(response.data);
      } catch (error) {
        console.error("Erro ao carregar leilões:", error);
      } finally {
        setLoading(false);
      }
    };

    carregarLeiloes();
  }, []);

  if (loading) return <p>Carregando leilões...</p>;
  return (
    <div style={{ padding: "2rem" }}>
      <h1>Leilões Ativos</h1>
      {leiloes.length === 0 ? (
        <p>Nenhum leilão encontrado.</p>
      ) : (
        <ul>
          {/* CORREÇÕES AQUI: */}
          {leiloes.map((leilao) => (
            // 1. A 'key' do React precisa ser um valor único.
            //    Usamos 'id_leilao' que vem da API.
            <li key={leilao.id_leilao}>
              <strong>{leilao.descricao}</strong>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
