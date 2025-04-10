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
        # Se a mensagem vier de grupo, usa o participantPhone
        phone = data.get("participantPhone") or data.get("phone", "")
        from_me = data.get("fromMe", False)
        text_message = data.get("text", {}).get("message")

        if not from_me and text_message and phone:
            resposta = analisar_mensagem(text_message)
            if resposta:
                enviar_resposta(phone, resposta)

    except Exception as e:
        print("Erro ao processar mensagem:", str(e))

    return "", 200

def analisar_mensagem(texto):
    texto = texto.lower()

    if "contrato" in texto:
        return "Recebi sua mensagem sobre contrato. Pode me enviar o PDF ou o conteúdo para análise."
    elif "processo" in texto:
        return "Recebi sua mensagem sobre processo. Por favor, envie o número do processo ou o arquivo em PDF."
    elif "analisar" in texto or "analisa" in texto:
        return "Claro! Envie o arquivo em PDF ou escreva o conteúdo que deseja que eu analise."
    elif "fazer um contrato" in texto or "quero um contrato" in texto:
        return "Perfeito. Me diga qual é o tipo de contrato que você precisa e os dados principais."
    elif "oi" in texto or "olá" in texto or "bom dia" in texto or "boa tarde" in texto or "boa noite" in texto:
        return "Olá! Sou o assistente jurídico do Dr. Dayan. Envie sua dúvida ou o material para análise."
    else:
        return "Recebi sua mensagem, mas ainda não consigo interpretar esse tipo de conteúdo. Envie um texto ou PDF."

def enviar_resposta(numero, mensagem):
    payload = {
        "phone": numero,
        "message": mensagem
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"[ENVIANDO] Para: {numero}")
        print("Mensagem:", mensagem)
        print("Status Z-API:", response.status_code)
        print("Retorno Z-API:", response.text)
    except Exception as e:
        print("❌ Erro ao enviar mensagem:", str(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
