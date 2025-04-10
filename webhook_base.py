from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Endpoint da sua instância Z-API
ZAPI_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1/token/61919ECA32B76ED6ABDAE637/send-text"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json

        # Extrai a mensagem e o número do cliente
        message = data["messages"][0]["text"]["body"].strip().lower()
        phone_id = data["messages"][0]["from"]
        numero = phone_id.split("@")[0]

        # Define a resposta conforme a mensagem recebida
        if message in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
            resposta = (
                "Olá! Seja bem-vindo ao Teixeira.Brito Advogados.\n"
                "Sou o assistente virtual do Dr. Dayan e posso te ajudar com:\n\n"
                "1️⃣ Análise de contrato\n"
                "2️⃣ Análise de processo\n"
                "3️⃣ Atendimento com advogado\n"
                "4️⃣ Outro assunto\n\n"
                "Digite o número da opção desejada para continuarmos."
            )
        elif message == "1" or "contrato" in message:
            resposta = (
                "Perfeito. Encaminhe o contrato em PDF ou descreva os pontos principais que deseja revisar. "
                "Retornarei com uma análise técnica e objetiva."
            )
        elif message == "2" or "processo" in message:
            resposta = (
                "Ok. Me envie o número do processo ou o arquivo em anexo. "
                "Farei a análise e retorno com os pontos relevantes."
            )
        elif message == "3":
            resposta = (
                "Certo. Você pode agendar um atendimento direto com o Dr. Dayan através do link abaixo:\n\n"
                "📅 https://calendly.com/daan-advgoias\n\n"
                "Escolha o melhor dia e horário disponíveis."
            )
        elif message == "4" or "outro" in message:
            resposta = (
                "Claro. Me conte mais detalhes sobre o que você precisa. "
                "Estou aqui para entender e direcionar da melhor forma."
            )
        else:
            resposta = (
                "Recebi sua mensagem. Me explique com clareza o que precisa, "
                "e te respondo com precisão e agilidade."
            )

        # Prepara o envio via Z-API
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

# Define a porta de execução para o Render detectar corretamente
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
