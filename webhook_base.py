from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Variáveis de ambiente/configuração
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID", "3DF715E26F0310B41D118E66062CE0C1")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN", "32EF0706F060E25B5CE884CC")
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("JSON recebido:", data)

    try:
        phone = data.get("participantPhone") or data.get("phone", "")
        from_me = data.get("fromMe", False)
        text_message = data.get("text", {}).get("message")

        if not from_me and text_message and phone:
            if "contrato" in text_message.lower():
                resposta = "Recebi sua mensagem sobre contrato. Pode me enviar o PDF ou o conteúdo para análise."
            else:
                resposta = "Recebi sua mensagem, mas ainda não consigo interpretar esse tipo de conteúdo. Envie um texto ou PDF."

            enviar_resposta(phone, resposta)

    except Exception as e:
        print("Erro ao processar mensagem:", str(e))

    return "", 200

def enviar_resposta(numero, mensagem):
    payload = {
        "phone": numero,
        "message": mensagem
    }

    headers = {
        "Content-Type": "application/json"
    }

    url = ZAPI_URL  # Já inclui o token embutido

    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"[ENVIANDO] Para: {numero}")
        print("Mensagem:", mensagem)
        print("Status Z-API:", response.status_code)
        print("Retorno Z-API:", response.text)
    except Exception as e:
        print("❌ Erro ao enviar mensagem:", str(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
