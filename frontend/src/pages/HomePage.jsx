import React, { useState, useEffect, useRef } from "react";
import api from "../services/APIService";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

export default function HomePage() {
  const [usuario, setUsuario] = useState("");
  const [leiloes, setLeiloes] = useState([]);
  const [descricao, setDescricao] = useState("");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const inicializou = useRef(false);

  const showToast = (mensagem, tipo = "info") => {
    const config = { position: "bottom-right", autoClose: 4000 };
    switch (tipo) {
      case "success":
        toast.success(mensagem, config);
        break;
      case "error":
        toast.error(mensagem, config);
        break;
      case "warning":
        toast.warn(mensagem, config);
        break;
      default:
        toast.info(mensagem, config);
    }
  };

  const carregaLeiloes = async () => {
    try {
      const response = await api.get(`/leiloes?usuario=${usuario}`);
      setLeiloes(response.data);
    } catch {
      showToast("Erro ao carregar leilões", "error");
    }
  };

  const criarLeilao = async (e) => {
    e.preventDefault();
    try {
      const novo = {
        descricao,
        data_hora_inicio: inicio,
        data_hora_fim: fim,
      };
      await api.post("/leiloes", novo);
      setDescricao("");
      setInicio("");
      setFim("");
      carregaLeiloes();
    } catch {
      showToast("Erro ao criar leilão", "error");
    }
  };

  const darLance = async (leilaoId) => {
    const valorStr = prompt("Digite o valor do seu lance:");
    if (!valorStr) return;
    const valor = parseFloat(valorStr);
    if (isNaN(valor)) return alert("Valor inválido!");

    try {
      await api.post("/lances", {
        id_leilao: leilaoId,
        id_usuario: usuario,
        valor,
      });
      carregaLeiloes();
    } catch {
      showToast("Erro ao enviar lance", "error");
    }
  };

  const registrarInteresse = async (id_leilao) => {
    try {
      await api.post("/interesse", { id_leilao, id_usuario: usuario });
      showToast(`Você demonstrou interesse no leilão ${id_leilao}`, "info");
      carregaLeiloes();
    } catch {
      showToast("Erro ao registrar interesse", "error");
    }
  };

  const cancelarInteresse = async (id_leilao) => {
    try {
      await api.delete(`/interesse/${usuario}/${id_leilao}`);
      showToast(`Interesse cancelado no leilão ${id_leilao}`, "warning");
      carregaLeiloes();
    } catch {
      showToast("Erro ao cancelar interesse", "error");
    }
  };

  useEffect(() => {
    if (inicializou.current) return;
    inicializou.current = true;

    const nome = prompt("Digite seu nome para entrar no sistema:");
    if (nome && nome.trim() !== "") {
      setUsuario(nome.trim());
      showToast(`Bem-vindo, ${nome.trim()}! 👋`, "success");
    } else {
      setUsuario("Usuário Anônimo");
      showToast("Entrou como usuário anônimo", "info");
    }
  }, []);

  useEffect(() => {
    if (!usuario) return;

    carregaLeiloes();

    const eventSource = new EventSource(`http://localhost:8080/sse/${usuario}`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const msg = data.mensagem || `Evento SSE: ${data.tipo}`;

        // Toast conforme tipo de evento
        if (data.tipo === "lance_validado")
          showToast(`✅ Lance validado: ${msg}`, "success");
        else if (data.tipo === "lance_invalidado")
          showToast(`❌ Lance inválido: ${msg}`, "error");

        else if (data.tipo === "leilao_vencedor") {
          showToast(`🏆 ${msg}`, "success");

          setTimeout(async () => {
            const confirmar = window.confirm(
              "Você ganhou o leilão! Deseja pagar agora?"
            );
            // no momento só fecha e não volta/faz nada
            if (!confirmar) return;

            try {
              // Chama o microserviço de pagamento
              const resp = await api.post("/pagamentos/iniciar", {
              id_leilao: data.id_leilao || "leilao-desconhecido",
              comprador: usuario,
              valor: data.valor || 0,
            });

              const { link_pagamento } = resp.data;
              window.open(link_pagamento, "_blank");
              showToast("Abrindo página de pagamento...", "info");
            } catch (err) {
              console.error(err);
              showToast("Erro ao iniciar pagamento", "error");
            }
          }, 1500);
        } else showToast(msg, "info");

        if (["lance_validado", "leilao_vencedor"].includes(data.tipo)) {
          carregaLeiloes();
        }
      } catch {
        showToast("Mensagem SSE recebida", "info");
      }
    };

    eventSource.onerror = () => {
      showToast("⚠️ Erro na conexão SSE", "error");
      eventSource.close();
    };

    return () => eventSource.close();
  }, [usuario]);

  return (
    <div style={styles.container}>
      <h1>Sistema de Leilões Online</h1>
      <h4>Bem-vindo, {usuario}!</h4>

      <section style={styles.section}>
        <h2>Criar Leilão</h2>
        <form onSubmit={criarLeilao}>
          <input
            type="text"
            placeholder="Descrição"
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            required
          />
          <input
            type="datetime-local"
            value={inicio}
            onChange={(e) => setInicio(e.target.value)}
            required
          />
          <input
            type="datetime-local"
            value={fim}
            onChange={(e) => setFim(e.target.value)}
            required
          />
          <button type="submit">Criar</button>
        </form>
      </section>

      <section style={styles.section}>
        <h2>Leilões Ativos</h2>
        <button onClick={carregaLeiloes}>Atualizar</button>
        <ul>
          {leiloes.length === 0 && <li>Nenhum leilão ativo</li>}
          {leiloes.map((l) => (
            <li key={l.id_leilao} style={styles.card}>
              <strong>{l.descricao}</strong>
              <br />
              Início: {new Date(l.data_hora_inicio).toLocaleString()} <br />
              Fim: {new Date(l.data_hora_fim).toLocaleString()} <br />
              ID: {l.id_leilao} <br />
              {l.ultimo_lance ? (
                <p>
                  💰 Último lance: R${l.ultimo_lance.valor} por{" "}
                  <b>{l.ultimo_lance.id_usuario}</b>
                </p>
              ) : (
                <p>Sem lances ainda</p>
              )}
              <button onClick={() => darLance(l.id_leilao)}>Dar Lance</button>
              {l.interessado ? (
                <button
                  onClick={() => cancelarInteresse(l.id_leilao)}
                  style={{ marginLeft: 10, background: "#f55", color: "#fff" }}
                >
                  Cancelar interesse
                </button>
              ) : (
                <button
                  onClick={() => registrarInteresse(l.id_leilao)}
                  style={{ marginLeft: 10, background: "#5a5", color: "#fff" }}
                >
                  Registrar interesse
                </button>
              )}
            </li>
          ))}
        </ul>
      </section>

      <ToastContainer />
    </div>
  );
}

const styles = {
  container: {
    maxWidth: "700px",
    margin: "0 auto",
    fontFamily: "Arial, sans-serif",
    padding: "20px",
  },
  section: {
    marginTop: "30px",
    padding: "15px",
    border: "1px solid #000",
    borderRadius: "6px",
    background: "#f9f9f9",
  },
  card: {
    border: "1px solid #ccc",
    borderRadius: "8px",
    padding: "10px",
    margin: "10px 0",
    background: "#fff",
  },
};
