from flask import Flask, request, jsonify
import threading, time, requests

app = Flask(__name__)

@app.route("/pagamentos", methods=["POST"])
def criar_pagamento():
    dados = request.get_json()
    link = f"https://SistemaPagamento.com/pagar/Leilao={dados['id_leilao']}_&_User={dados['id_usuario']}"
    
    def enviar_webhook():
        time.sleep(15)
        payload = {
            "id_leilao": dados["id_leilao"],
            "id_usuario": dados["id_usuario"],
            "valor": dados["valor"],
            "status": "aprovado"
        }
        requests.post("http://localhost:5002/webhook", json=payload)
        print(f"Webhook enviado -> {payload}")

    threading.Thread(target=enviar_webhook).start()

    return jsonify({"link_pagamento": link}), 200

if __name__ == "__main__":
    app.run(port=5003)