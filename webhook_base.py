from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Endpoint da sua instância Z-API
ZAPI_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1/token/61919ECA32B76ED6ABDAE637/send-text"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json

        # Extrai mensagem e número do cliente
        message = data["messages"][0]["text"]["body"].lower()
        phone_id = data["messages"][0]["from"]  # Exemplo: 5511999999999@c.us
        numero = phone_id.split("@")[0]

        # Define resposta com base no conteúdo da mensagem
        if "contrato" in message:
            resposta = "Claro! Envie o contrato que você deseja analisar."
        elif "processo" in message:
            resposta = "Perfeito. Me envie o número do processo ou o arquivo PDF."
        elif "ajuda" in message or "atendimento" in message:
            resposta = "Estou aqui para te ajudar. Pode me explicar o que você precisa?"
        else:
            resposta = "Recebido! Me conte mais sobre o que você está precisando."

        # Prepara payload e headers para envio via Z-API
        payload = {
            "phone": numero,
            "message": resposta
        }

        headers = {
            "Content-Type": "application/json"
        }

        # Envia mensagem via Z-API
        response = requests.post(ZAPI_URL, json=payload, headers=headers)

        return jsonify({
            "status": "mensagem enviada",
            "mensagem_recebida": message,
            "resposta_enviada": resposta,
            "retorno_zapi": response.json()
        })

    except Exception as e:
        return jsonify({"erro": str(e)})
