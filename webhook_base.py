from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import openai
import requests

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Variáveis de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Contatos e grupos bloqueados
bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

# Blocos de resposta automática
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
        print("📩 JSON recebido:", data)

        # Tentativas múltiplas para extrair o texto
        mensagem = data.get("message", "").strip() \
            or data.get("text", {}).get("body", "") \
            or data.get("text", {}).get("message", "") \
            or ""

        telefone = data.get("senderPhone") or data.get("phone") or ""
        nome = data.get("senderName", "")
        grupo = data.get("groupName", "")
        historico = data.get("messageCount", 0)

        # Temporário: continuar mesmo com dados incompletos (para debug)
        if not mensagem or not telefone:
            print("⚠️ Dados ausentes (mensagem ou telefone). Prosseguindo para debug...")

        if nome in bloqueados or grupo in grupos_bloqueados:
            print("⛔ Contato ou grupo bloqueado:", nome or grupo)
            return jsonify({"response": None})

        if historico > 1:
            print("🔁 Mensagem ignorada (já possui histórico).")
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
        print("❌ Erro no webhook:", str(e))
        return jsonify({"error": "Erro interno"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
