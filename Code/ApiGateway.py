from flask import Flask, request, jsonify
import threading
import requests
import json
from rabbitmq_utils import RabbitMQHelper
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

interesses = {}
MSNotificacoes = RabbitMQHelper(exchange='notificacoes')


#Lance invalido, valido e vencedor + TO DO: leilao iniciado/finalizado
def callback_notificacoes(ch, method, properties, body):
    evento = method.routing_key
    dados = json.loads(body)
    id_leilao = dados.get("id_leilao")

    if not id_leilao or id_leilao not in interesses:
        print(f"[AVISO] ID do leilao nao encontrado", dados)
        return

    for cliente in interesses[id_leilao]:
        print(f"[NOTIFICAÇÃO] Enviando {evento} para cliente {cliente}: {dados}")


def iniciar_consumo_eventos():
    fila = MSNotificacoes.declare_queue(queue='', exclusive=True).method.queue
    
    #Valido invalido e vencedor 
    MSNotificacoes.bind_queue('notificacoes', fila, 'lance_validado')
    MSNotificacoes.bind_queue('notificacoes', fila, 'lance_invalidado')
    MSNotificacoes.bind_queue('notificacoes', fila, 'leilao_vencedor')

    MSNotificacoes.receive(fila, callback_notificacoes)
    MSNotificacoes.consume()


@app.route("/leiloes", methods=["GET"])
def listar_leiloes():
    """Encaminha GET /leiloes para o MS-Leilao."""
    try:
        r = requests.get("http://localhost:5000/leiloes")
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/leiloes/<int:id_leilao>", methods=["GET"])
def obter_leilao_por_id(id_leilao):
    """Encaminha GET /leiloes/<id> para o MS-Leilao."""
    try:
        ms_leilao_id = f"http://localhost:5000/leiloes/{id_leilao}"
        r = requests.get(ms_leilao_id)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/leiloes", methods=["POST"])
def criar_leilao():
    try:
        dados = request.get_json()
        r = requests.post("http://localhost:5000/leiloes", json=dados)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/lances", methods=["POST"])
def adicionar_lance():
    try:
        dados = request.get_json()
        r = requests.post("http://localhost:5001/lances", json=dados)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/interesse", methods=["POST"])
def registrar_interesse():
    dados = request.get_json()
    id_leilao = dados.get("id_leilao")
    id_cliente = dados.get("id_cliente")

    if not id_leilao or not id_cliente:
        return jsonify({"erro": "Campos obrigatorios: id_leilao, id_cliente"}), 400

    interesses.setdefault(id_leilao, set()).add(id_cliente)
    
    return jsonify({"status": "interesse_registrado"}), 201


@app.route("/interesse/<int:id_leilao>", methods=["GET"])
def ver_interessados(id_leilao):
    interessados = list(interesses.get(id_leilao, []))
    return jsonify({
        "id_leilao": id_leilao,
        "interessados": interessados,
        "total_interessados": len(interessados)
    }), 200


@app.route("/interesse/cancelar", methods=["POST"])
def cancelar_interesse():
    dados = request.get_json()
    id_leilao = dados.get("id_leilao")
    id_cliente = dados.get("id_cliente")

    if not id_leilao or not id_cliente:
        return jsonify({"erro": "Campos obrigatorios: id_leilao, id_cliente"}), 400

    if id_leilao in interesses:
        interesses[id_leilao].discard(id_cliente)

    return jsonify({"status": "interesse_cancelado"}), 200


@app.route("/", methods=["GET"])
def raiz():
    return jsonify({"mensagem": "API Gateway ativo"}), 200


if __name__ == "__main__":
    threading.Thread(target=iniciar_consumo_eventos, daemon=True).start()
    print("API Gateway Flask rodando em http://localhost:8080")
    app.run(host="0.0.0.0", port=8080)
