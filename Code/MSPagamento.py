import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from rabbitmq_utils import RabbitMQHelper
import requests
app = Flask(__name__)

MSPagamentos = RabbitMQHelper(exchange="notificacoes")

pagamentos_pendentes = {}

EXTERNAL_PAYMENT_URL = "http://localhost:5003/pagamentos"

#COnsumir do evento leilao_vencedor
def callback_vencedor(ch, method, properties, body):

    dados = json.loads(body)
    print(f"[MSPagamento] Evento recebido: {method.routing_key} -> {dados}")

    id_leilao = dados["id_leilao"]
    id_usuario = dados["id_usuario"]
    valor = dados["valor"]

    # mapear pagamento pendente com o cliente > cada leilao tem um ID e um vencedor - pode ter muitooo mais cliente 
    pagamentos_pendentes[id_leilao] = id_usuario

    # REST para o pagamento externo
    try:
        payload = {
            # Para cada evento consumido, ele fará uma requisição REST ao sistema externo de pagamentos enviando os dados do pagamento 
            # (valor, moeda, informações do cliente) e, então, receberá um link de pagamento que será publicado em link_pagamento.
            "valor": valor,
            "moeda": "BRL",
            "id_usuario": id_usuario,
            "id_leilao": id_leilao
        }

        resposta = requests.post(EXTERNAL_PAYMENT_URL, json=payload, timeout=5)
        resposta.raise_for_status()
        link_pagamento = resposta.json().get("link_pagamento")

        # POST do link_pagamento
        evento = {
            "id_leilao": id_leilao,
            "id_usuario": id_usuario,
            "valor": valor,
            "link_pagamento": link_pagamento
        }

        MSPagamentos.publish(
            routing_key="link_pagamento",
            body=json.dumps(evento)
        )
        print(f"[MSPagamento] Publicado evento link_pagamento -> {evento}")

    except Exception as e:
        print(f"[ERRO pagamento externo] {e}")


#para Testar
@app.route("/pagamentos", methods=["GET"])
def listar_pagamentos():
    return jsonify({
        "mensagem": "MSPagamento está rodando corretamente 🚀",
        "pendentes": pagamentos_pendentes
    }), 200

@app.route("/pagamentos/iniciar", methods=["POST"])
def iniciar_pagamento():
    try:
        dados = request.get_json()
        id_leilao = dados.get("id_leilao")
        id_usuario = dados.get("comprador")
        valor = dados.get("valor")

        pagamentos_pendentes[id_leilao] = id_usuario

        payload = {
            "valor": valor,
            "moeda": "BRL",
            "id_usuario": id_usuario,
            "id_leilao": id_leilao
        }

        resposta = requests.post(EXTERNAL_PAYMENT_URL, json=payload, timeout=5)
        resposta.raise_for_status()
        link_pagamento = resposta.json().get("link_pagamento")

        evento = {
            "id_leilao": id_leilao,
            "id_usuario": id_usuario,
            "valor": valor,
            "link_pagamento": link_pagamento
        }

        MSPagamentos.publish(routing_key="link_pagamento", body=json.dumps(evento))
        print(f"[MSPagamento] Publicado evento link_pagamento -> {evento}")

        return jsonify({
            "status": "ok",
            "link_pagamento": link_pagamento
        }), 200

    except Exception as e:
        print(f"[ERRO /pagamentos/iniciar] {e}")
        return jsonify({"erro": str(e)}), 500

@app.route("/webhook", methods=["POST"])
def webhook():
    dados = request.get_json()
    id_leilao = dados.get("id_leilao")

    if id_leilao in pagamentos_pendentes:
        dados["id_usuario"] = pagamentos_pendentes[id_leilao]

    MSPagamentos.publish(
        routing_key="status_pagamento",
        body=json.dumps(dados)
    )

    return jsonify({"status": "ok"}), 200
    

def iniciar_consumo_pagamentos():
    q_pagamentos = MSPagamentos.declare_queue(queue='', exclusive=True).method.queue

    MSPagamentos.bind_queue('notificacoes', q_pagamentos, 'leilao_vencedor')

    MSPagamentos.receive(q_pagamentos, callback_vencedor)
    MSPagamentos.consume()


if __name__ == "__main__":
    threading.Thread(target=iniciar_consumo_pagamentos, daemon=True).start()
    
    print("Servidor Flask MS-Pagamento em http://localhost:5002")
    app.run(host="0.0.0.0", port=5002)