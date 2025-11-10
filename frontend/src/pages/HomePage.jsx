import React, { useState, useEffect } from "react";
import api from "../services/APIService";

export default function HomePage() {
  const [leiloes, setLeiloes] = useState([]);
  const [descricao, setDescricao] = useState("");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [logs, setLogs] = useState([]);

  const addLog = (msg) => setLogs((prev) => [...prev, msg]);

  // Busca pelos Leiloes
  const carregaLeiloes = async () => {
    try {
      //GEt do leiloes 
      const response = await api.get("/leiloes");
      setLeiloes(response.data);
      //Historico de acoes
      addLog("Leilões carregados com sucesso");
    } catch (err) {
      addLog("Erro ao carregar leilões");
    }
  };

  // Criar um novo > POSTzinho
  const criarLeilao = async (e) => {
    e.preventDefault();
    //useful when: Clicking on a "Submit" button, prevent it from submitting a form.
    //https://www.w3schools.com/jsref/event_preventdefault.asp#:~:text=Description,it%20from%20submitting%20a%20form
    
    try {
      const novo = {
        descricao,
        data_hora_inicio: inicio,
        data_hora_fim: fim,
      };
      
      const response = await api.post("/leiloes", novo);

      addLog(`Leilao criado: ${response.data.descricao}`);

      // Criou e restar o form
      setDescricao("");
      setInicio("");
      setFim("");

      // Criou e recarrga para mostrar
      carregaLeiloes();
    } 
    
    catch (err) {
      addLog("Erro ao criar leilão");
    }
  };



useEffect(() => {
  const carregaLeiloes = async () => {
    const resposta = await api.get("/leiloes");
    setLeiloes(resposta.data);
  };

  carregaLeiloes();
}, []); 


  return (
    <div style={styles.container}>
      <h1>Trabalho de Sistemas Distribuídos</h1>
      <h2> Sistemas de Leilões Online</h2>
      <h3>Microsserviços, Middleware orientado a Mensagens, REST, SSE, Webhook</h3>
      <br></br>

      {/* Criar Leilão */}
      <section style={styles.section}>
        <h2>Criar Leilão</h2>
        <form onSubmit={criarLeilao}>
          <label> Descrição: </label>
          <input
            type="text"
            placeholder="Descrição do Leilão"
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            required
          />
           <br></br>
          <label> Início: </label>
          <input
            type="datetime-local"
            placeholder="Início do Leilão"
            value={inicio}
            onChange={(e) => setInicio(e.target.value)}
            required
          />
          <br></br> 
          <label> Fim: </label>
          <input
            type="datetime-local"
            placeholder="Fim do Leilão"
            value={fim}
            onChange={(e) => setFim(e.target.value)}
            required
          /><br></br>
          <br></br>
          <button type="submit">Criar</button>
        </form>
        <br></br>
      </section>

      {/* Listar Leilões */}
      <section style={styles.section}>
        <h2>Leilões Ativos</h2>
        <button onClick={carregaLeiloes}> Refresh</button>
        <ul>
          {leiloes.length === 0 && <li>Nenhum leilão ativo</li>}
          {leiloes.map((l) => (
            <li key={l.id_leilao}>
              <strong>{l.descricao}</strong>
              <br />
              Início: {new Date(l.data_hora_inicio).toLocaleString()} <br />
              Fim: {new Date(l.data_hora_fim).toLocaleString()} <br />
              ID: {l.id_leilao}
            </li>
          ))}
        </ul>
      </section>

      {/* Logs simples */}
      <section style={styles.section}>
        <h2>Logs de atividades</h2>
        <div style={styles.logs}>
          {logs.map((log, i) => (
            <p key={i}>{log}</p>
          ))}
        </div>
      </section>
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
    border: "1px solid #000000ff",
    borderRadius: "6px",
    background: "#f9f9f9",
  },
  logs: {
    background: "#eee",
    padding: "10px",
    borderRadius: "8px",
    marginTop: "10px",
    height: "120px",
    overflowY: "auto",
  },
};
