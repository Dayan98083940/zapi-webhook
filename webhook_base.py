from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import openai
import requests

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Variáveis de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Lista de bloqueios
bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

# Carrega blocos de respostas
try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as file:
        respostas_automaticas = json.load(file)
except Exception as e:
    print("❌ Erro ao carregar blocos_respostas.json:", str(e))
    respostas_automaticas = []

def detectar_assunto(msg):
    profissionais = [
        "contrato", "holding", "divórcio", "herança", "inventário",
        "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"
    ]
    msg = msg.lower()
    for termo in profissionais:
        if termo in msg:
            return "profissional"
    return "particular"

def responder_com_bloco(msg):
    for bloco in respostas_automaticas:
        for termo in bloco.get("keywords", []):
            if termo in msg.lower():
                return bloco["response"]
    return None

def gerar_resposta_gpt(mensagem):
    try:
        prompt = f"""
Você é um assistente jurídico do escritório Teixeira.Brito Advogados.

Mensagem recebida do cliente: {mensagem}

Responda de forma clara, empática e objetiva, como um profissional jurídico confiável.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico profissional."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Erro ao gerar resposta GPT:", str(e))
        return None

def enviar_zapi(phone, message):
    payload = {
        "phone": phone,
        "message": message
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"✅ Enviado para {phone} | Status: {r.status_code} | Resposta: {r.text}")
    except Exception as e:
        print("❌ Erro ao enviar via Z-API:", str(e))

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "online", "message": "Webhook jurídico ativo"}), 200

@app.route("/webhook", methods=["POST"])
def responder():
    try:
        data = request.json or {}
        nome = data.get("senderName", "")
        grupo = data.get("groupName", "")
        mensagem = data.get("message", "")
        historico = data.get("messageCount", 0)
        telefone = data.get("senderPhone", "")

        # Segurança
        if not mensagem or not telefone:
            return jsonify({"error": "Mensagem ou telefone ausente"}), 400

        if nome in bloqueados or grupo in grupos_bloqueados:
            return jsonify({"response": None})

        if historico > 1:
            return jsonify({"response": None})

        tipo = detectar_assunto(mensagem)

        if tipo == "profissional":
            resposta = responder_com_bloco(mensagem)
            if not resposta:
                resposta = gerar_resposta_gpt(mensagem)

            if resposta:
                enviar_zapi(telefone, resposta)
                return jsonify({"response": resposta})

        return jsonify({"response": None})

    except Exception as e:
        print("❌ Erro no processamento do webhook:", str(e))
        return jsonify({"error": "Erro interno"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
