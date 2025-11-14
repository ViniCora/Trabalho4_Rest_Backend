import json
import queue
import threading
import time
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests
from rabbitmq_utils import RabbitMQHelper

app = Flask(__name__)
CORS(app, supports_credentials=True)

interesses = {}
conexoes_sse = {}
lock = threading.Lock()

MSNotificacoes = RabbitMQHelper(exchange="notificacoes")

def enviar_evento_sse(usuario, payload):
    try:
        with lock:
            fila = conexoes_sse.get(usuario)
        if fila:
            fila.put(json.dumps(payload))
    except Exception as e:
        print(f"Erro ao enviar para {usuario}: {e}")


def montar_mensagem_evento(evento, dados, usuario_destino):
    tipo = evento
    id_leilao = dados.get("id_leilao")
    valor = dados.get("valor")
    id_usuario = dados.get("id_usuario")
    vencedor = dados.get("vencedor")
    valor_vencedor = dados.get("valor_vencedor")

    if tipo == "lance_validado":
        if id_usuario == usuario_destino:
            return f"Seu lance de R${valor:.2f} foi validado no leilão {id_leilao}."
        else:
            return f"O leilão {id_leilao} recebeu um novo lance de R${valor:.2f}."

    elif tipo == "lance_invalidado":
        motivo = dados.get("motivo")
        if id_usuario == usuario_destino:
            if motivo == "leilao_finalizado":
                return f"O leilão {id_leilao} já foi finalizado. Não é possível enviar novos lances."
            elif motivo == "fora_do_periodo":
                return f"O leilão {id_leilao} não está no período ativo."
            elif motivo == "valor_menor_ou_igual":
                return f"Seu lance de R${valor:.2f} foi negado, pois é inferior ao último valor no leilão {id_leilao}."
            else:
                return f"Seu lance no leilão {id_leilao} foi rejeitado (motivo: {motivo})."
        else:
            return None

    elif tipo == "leilao_iniciado":
        return f"O leilão {id_leilao} foi iniciado!"

    elif tipo == "leilao_finalizado":
        if vencedor and valor_vencedor:
            return f"O leilão {id_leilao} foi finalizado. Ganhador: {vencedor}, com o valor de R${valor_vencedor:.2f}."
        return f"O leilão {id_leilao} foi finalizado."

    elif tipo == "leilao_vencedor":
        if id_usuario == usuario_destino:
            return f"Parabéns! Você venceu o leilão {id_leilao} com o valor de R${valor:.2f}."
        else:
            return f"O leilão {id_leilao} teve um vencedor: {id_usuario} (R${valor:.2f})."

    elif tipo == "link_pagamento":
        if id_usuario == usuario_destino:
            link = dados.get("link_pagamento")
            return f"Seu pagamento está pronto! Acesse o link: {link}"
        else:
            return None
        
    elif tipo == "status_pagamento":
        if id_usuario == usuario_destino:
            status = dados.get("status")
            if status == "aprovado":
                return f"Pagamento aprovado! Obrigado por participar do leilão {id_leilao}."
            else:
                return f"Pagamento recusado ou não concluído no leilão {id_leilao}."
        else:
            return None

    else:
        return f"Evento {tipo} no leilão {id_leilao}."


def callback_notificacoes(ch, method, properties, body):
    evento = method.routing_key
    try:
        dados = json.loads(body)
    except Exception:
        dados = {"raw": body.decode()}

    id_leilao_raw = dados.get("id_leilao", "")
    id_leilao = str(id_leilao_raw) if id_leilao_raw is not None else ""


    with lock:
        print(f"Interesses atuais: {interesses}")

    if not id_leilao:
        print(f"[AVISO] Evento sem id_leilao: {evento} -> {dados}")
        return

    with lock:
        interessados = set()
        interessados |= interesses.get(id_leilao, set())
        interessados |= interesses.get(str(id_leilao_raw), set())

    if not interessados:
        return

    for user in list(interessados):
        mensagem = montar_mensagem_evento(evento, dados, user)
        if not mensagem:
            continue

        payload = {
            "tipo": evento,
            "mensagem": mensagem,
            "dados": dados,
            "timestamp": time.time(),
            "id_leilao": dados.get("id_leilao")
        }
        enviar_evento_sse(user, payload)


def iniciar_consumo_eventos():
    fila = MSNotificacoes.declare_queue(queue='', exclusive=True).method.queue
    MSNotificacoes.bind_queue("notificacoes", fila, "lance_validado")
    MSNotificacoes.bind_queue("notificacoes", fila, "lance_invalidado")
    MSNotificacoes.bind_queue("notificacoes", fila, "leilao_vencedor")
    MSNotificacoes.bind_queue("notificacoes", fila, "link_pagamento")
    MSNotificacoes.bind_queue("notificacoes", fila, "status_pagamento")
    print("[RABBITMQ] Iniciando consumo de eventos...")
    MSNotificacoes.receive(fila, callback_notificacoes)
    MSNotificacoes.consume()


@app.route("/leiloes", methods=["POST"])
def criar_leilao():
    try:
        dados = request.get_json()
        r = requests.post("http://localhost:5000/leiloes", json=dados, timeout=3)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        print(f"[ERRO /leiloes POST] {e}")
        return jsonify({"erro": str(e)}), 500


@app.route("/leiloes", methods=["GET"])
def listar_leiloes():
    usuario = request.args.get("usuario")
    try:
        r_leiloes = requests.get("http://localhost:5000/leiloes", timeout=3)
        r_lances = requests.get("http://localhost:5001/lances/ultimos", timeout=3)

        if r_leiloes.status_code != 200:
            return jsonify({"erro": "Falha ao obter leilões"}), 500

        ultimos_lances = r_lances.json() if r_lances.status_code == 200 else {}
        leiloes = r_leiloes.json()

        for leilao in leiloes:
            id_str = str(leilao["id_leilao"])
            leilao["ultimo_lance"] = ultimos_lances.get(id_str)
            with lock:
                leilao["interessado"] = usuario in interesses.get(id_str, set()) if usuario else False

        return jsonify(leiloes)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/lances", methods=["POST"])
def encaminhar_lance():
    try:
        dados = request.get_json()
        r = requests.post("http://localhost:5001/lances", json=dados, timeout=3)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/interesse", methods=["POST"])
def registrar_interesse():
    data = request.get_json()
    id_leilao = str(data.get("id_leilao"))
    usuario = data.get("id_usuario") or data.get("usuario") or data.get("channel")
    if not id_leilao or not usuario:
        return jsonify({"erro": "Campos obrigatórios: id_leilao, id_usuario"}), 400

    with lock:
        interesses.setdefault(id_leilao, set()).add(usuario)

    return jsonify({"status": "interesse_registrado"})


@app.route("/interesse/<usuario>/<int:id_leilao>", methods=["DELETE"])
def cancelar_interesse(usuario, id_leilao):
    id_str = str(id_leilao)
    with lock:
        if id_str in interesses and usuario in interesses[id_str]:
            interesses[id_str].discard(usuario)
    return jsonify({"status": "interesse_cancelado"})


@app.route("/sse/<usuario>")
def sse(usuario):
    def gerar_eventos():
        fila = queue.Queue()
        conexoes_sse[usuario] = fila
        print(f"SSE Conectado: {usuario}")
        try:
            while True:
                evento = fila.get()
                yield f"data: {evento}\n\n".encode("utf-8")
        except GeneratorExit:
            print(f"SSE Desconectado: {usuario}")
            conexoes_sse.pop(usuario, None)

    return Response(gerar_eventos(), mimetype="text/event-stream")

@app.route("/pagamentos/iniciar", methods=["POST"])
def iniciar_pagamento():
    try:
        dados = request.get_json()
        resposta = requests.post("http://localhost:5002/pagamentos/iniciar", json=dados)
        return jsonify(resposta.json()), resposta.status_code
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    threading.Thread(target=iniciar_consumo_eventos, daemon=True).start()
    print("Gateway rodando em http://localhost:8080")
    app.run(host="0.0.0.0", port=8080, threaded=True)
