from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Endpoint da sua instância Z-API com ID e Token já definidos
ZAPI_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1/token/61919ECA32B76ED6ABDAE637/send-text"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json

        # Captura o texto da mensagem e o telefone do cliente
        message = data["messages"][0]["text"]["body"].strip().lower()
        phone_id = data["messages"][0]["from"]
        numero = phone_id.split("@")[0]

        # Define a resposta com base no conteúdo da mensagem recebida
        if "contrato" in message:
            resposta = (
                "Entendido. Me encaminhe o contrato em PDF ou me diga os pontos principais "
                "que você deseja revisar. Farei a análise com base nas informações fornecidas."
            )
        elif "processo" in message:
            resposta = (
                "Por favor, envie o número do processo ou o arquivo que deseja que eu analise. "
                "Analisarei com atenção e te passo um retorno objetivo."
            )
        elif "ajuda" in message or "atendimento" in message:
            resposta = (
                "Estou à disposição para te orientar. Me conte de forma direta o que está acontecendo "
                "e vamos buscar a melhor solução juntos."
            )
        else:
            resposta = (
                "Recebi sua mensagem. Pode me explicar com mais clareza o que você precisa? "
                "Assim consigo te dar uma resposta mais precisa."
            )

        # Envio da resposta automática via Z-API
        payload = {
            "phone": numero,
            "message": resposta
        }

        headers = {
            "Content-Type": "application/json"
        }

        envio = requests.post(ZAPI_URL, json=payload, headers=headers)

        return jsonify({
            "status": "resposta enviada",
            "mensagem_recebida": message,
            "resposta_enviada": resposta,
            "retorno_zapi": envio.json()
        })

    except Exception as e:
        return jsonify({"erro": str(e)})

# Configuração de porta obrigatória para o Render detectar o serviço
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
