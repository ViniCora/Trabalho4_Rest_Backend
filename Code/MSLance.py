import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from rabbitmq_utils import RabbitMQHelper

app = Flask(__name__)

leiloes_ativos = {}
lances = {}

MSLance = RabbitMQHelper(exchange='leiloes_status')
MSNotificacao = RabbitMQHelper(exchange='notificacoes')


def callback_leilao(ch, method, properties, body):
    """Recebe eventos de leilão: iniciado e finalizado."""
    evento = method.routing_key
    dados = json.loads(body)

    if evento == 'leilao_iniciado':
        inicio = datetime.fromisoformat(dados["data_hora_inicio"])
        fim = datetime.fromisoformat(dados["data_hora_fim"])
        leiloes_ativos[dados["id_leilao"]] = {"inicio": inicio, "fim": fim}
        print(f"[LEILAO ATIVO] {dados['id_leilao']} entre {inicio} e {fim}")

    elif evento == 'leilao_finalizado':
        id_leilao = dados["id_leilao"]
        vencedor = lances.get(id_leilao)
        if vencedor:
            mensagem = {
                "id_leilao": id_leilao,
                "id_usuario": vencedor["id_usuario"],
                "valor": vencedor["valor"]
            }
            MSNotificacao.publish(
                routing_key='leilao_vencedor',
                body=json.dumps(mensagem)
            )
            print(f"[VENCEDOR] Leilão {id_leilao} -> {mensagem}")
        else:
            print(f"[FINALIZADO SEM LANCES] {id_leilao}")
        leiloes_ativos.pop(id_leilao, None)


def adicionar_lance(lance):
    """Registra um novo lance, se for válido."""
    id_leilao = lance["id_leilao"]
    id_usuario = lance["id_usuario"]
    valor = float(lance["valor"])
    agora = datetime.now()

    #Validar se está ativo - validacao 1
    if id_leilao not in leiloes_ativos:
        print(f"[INVALIDO] Leilão {id_leilao} não está ativo.")
        publicar_lance_invalido(lance, motivo="leilao_inativo")
        return False

    periodo = leiloes_ativos[id_leilao]
    if not (periodo["inicio"] <= agora <= periodo["fim"]):
        print(f"[INVALIDO] Fora do período ativo do leilão {id_leilao}")
        publicar_lance_invalido(lance, motivo="fora_do_periodo")
        return False

    #Validar se o valor é maior que o atual - validacao 2
    atual = lances.get(id_leilao)
    if atual and valor <= atual["valor"]:
        print(f"[INVALIDO] Lance {valor} <= atual ({atual['valor']})")
        publicar_lance_invalido(lance, motivo="valor_menor_ou_igual")
        return False

    #Se passou pelas validações, registra o lance
    lances[id_leilao] = {"id_usuario": id_usuario, "valor": valor}
    print(f"[VALIDO] Novo lance {valor} registrado para {id_leilao}")
    publicar_lance_validado(lance)
    return True


def publicar_lance_validado(lance):
    MSNotificacao.publish(routing_key='lance_validado', body=json.dumps(lance))


def publicar_lance_invalido(lance, motivo="desconhecido"):
    mensagem = {**lance, "motivo": motivo}
    MSNotificacao.publish(routing_key='lance_invalidado', body=json.dumps(mensagem))


@app.route("/lances", methods=["POST"])
def endpoint_lances():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"erro": "JSON inválido"}), 400

        campos = ["id_leilao", "id_usuario", "valor"]
        if not all(c in data for c in campos):
            return jsonify({"erro": "Campos obrigatórios: id_leilao, id_usuario, valor"}), 400

        valido = adicionar_lance(data)
        status = 201 if valido else 400
        resposta = {
            "status": "aceito" if valido else "rejeitado",
            "lance": data
        }
        return jsonify(resposta), status

    except Exception as e:
        return jsonify({"erro": str(e)}), 400


@app.route("/", methods=["GET"])
def raiz():
    return jsonify({"mensagem": "MS-Lance ativo"}), 200


def iniciar_consumo_rabbit():
    MSLance.declare_exchange('lances')
    q_leilao = MSLance.declare_queue(queue='', exclusive=True).method.queue

    MSLance.bind_queue('leiloes_status', q_leilao, 'leilao_iniciado')
    MSLance.bind_queue('leiloes_status', q_leilao, 'leilao_finalizado')

    MSLance.receive(q_leilao, callback_leilao)
    print("MS Lance aguardando eventos de leilão...")
    MSLance.consume()


if __name__ == "__main__":
    threading.Thread(target=iniciar_consumo_rabbit, daemon=True).start()

    print("Servidor Flask MS-Lance em http://localhost:5001")
    app.run(host="0.0.0.0", port=5001)
