from flask import Flask, request, jsonify
from rabbitmq_utils import RabbitMQHelper
from datetime import datetime
import threading
import time
import json

app = Flask(__name__)

leiloes = []

@app.route("/leiloes", methods=["GET"])
def listar_leiloes():
    leiloes_serializaveis = [
        {
            "id_leilao": l["id_leilao"],
            "descricao": l["descricao"],
            "data_hora_inicio": l["data_hora_inicio"].isoformat(),
            "data_hora_fim": l["data_hora_fim"].isoformat()
        }
        for l in leiloes
    ]
    return jsonify(leiloes_serializaveis), 200


@app.route("/leiloes", methods=["POST"])
def criar_leilao():
    try:
        data = request.get_json()
        obrigatorios = ["descricao", "data_hora_inicio", "data_hora_fim"]

        # Verifica se os campos obrigatórios estão presentes
        if not data or not all(campo in data for campo in obrigatorios):
            return jsonify({"erro": "Campos obrigatórios faltando"}), 400

        # Gera o próximo ID automaticamente
        if leiloes:
            ultimo_id = max(l["id_leilao"] for l in leiloes)
            novo_id = ultimo_id + 1
        else:
            novo_id = 1

        novo_leilao = {
            "id_leilao": novo_id,
            "descricao": data["descricao"],
            "data_hora_inicio": datetime.fromisoformat(data["data_hora_inicio"]),
            "data_hora_fim": datetime.fromisoformat(data["data_hora_fim"]),
            "inicio_impresso": False,
            "fim_impresso": False
        }

        leiloes.append(novo_leilao)

        return jsonify({
            "mensagem": "Leilão adicionado com sucesso",
            "id_leilao": novo_id 
        }), 201

    except Exception as e:
        return jsonify({"erro": str(e)}), 400

@app.route("/leiloes/<int:id_leilao>", methods=["GET"])
def obter_info_leilao(id_leilao):
    leilao_id = next((l for l in leiloes if l["id_leilao"] == id_leilao), None)

    if leilao_id:
        leilao_serializavel = {
            "id_leilao": leilao_id["id_leilao"],
            "descricao": leilao_id["descricao"],
            "data_hora_inicio": leilao_id["data_hora_inicio"].isoformat(),
            "data_hora_fim": leilao_id["data_hora_fim"].isoformat()
        }
        return jsonify(leilao_serializavel), 200
    else:
        return jsonify({"erro": "Leilão não encontrado"}), 404
    
def monitorar_leiloes():
    MSLeilao = RabbitMQHelper(exchange='leiloes_status')

    while True:
        agora = datetime.now()
        for leilao in leiloes:
            leilao_serializavel = {
                "id_leilao": leilao["id_leilao"],
                "descricao": leilao["descricao"],
                "data_hora_inicio": leilao["data_hora_inicio"].isoformat(),
                "data_hora_fim": leilao["data_hora_fim"].isoformat()
            }
            print(leilao)

            try:
                if not leilao["inicio_impresso"] and agora >= leilao["data_hora_inicio"]:
                    MSLeilao.publish(
                        routing_key='leilao_iniciado',
                        body=json.dumps(leilao_serializavel)
                    )
                    leilao["inicio_impresso"] = True
                    print(f"Leilão {leilao['id_leilao']} iniciado e notificado.")

                if not leilao["fim_impresso"] and agora >= leilao["data_hora_fim"]:
                    MSLeilao.publish(
                        routing_key='leilao_finalizado',
                        body=json.dumps(leilao_serializavel)
                    )
                    leilao["fim_impresso"] = True
                    print(f"Leilão {leilao['id_leilao']} finalizado e notificado.")

            except Exception as e:
                print(f"Erro ao publicar no RabbitMQ: {e}")
                # Tenta reconectar se o canal estiver fechado
                time.sleep(2)
                try:
                    MSLeilao = RabbitMQHelper(exchange='leiloes_status')
                    print("Reconectado ao RabbitMQ com sucesso.")
                except Exception as erro_reconexao:
                    print(f"Falha ao reconectar ao RabbitMQ: {erro_reconexao}")

        time.sleep(1)

#pika.exceptions.StreamLostError: Stream connection lost

if __name__ == "__main__":
    threading.Thread(target=monitorar_leiloes, daemon=True).start()

    print("Servidor Flask MS-Leilao em http://localhost:5000")
    app.run(host="0.0.0.0", port=5000)
