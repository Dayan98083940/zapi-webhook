from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import openai
import requests

# Inicializa Flask app
app = Flask(__name__)

# Carrega variáveis do .env
load_dotenv()

# Variáveis de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")

# Z-API endpoint
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"

# OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Bloqueios de nomes e grupos
bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

# Carrega blocos de respostas
try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as file:
        respostas_automaticas = json.load(file)
except Exception as e:
    print("❌ Erro ao carregar blocos_respostas.json:", str(e))
    respostas_automaticas = []

# Verifica se o assunto é profissional
def detectar_assunto(msg):
    termos = ["contrato", "holding", "divórcio", "herança", "inventário",
              "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"]
    msg = msg.lower()
    return "profissional" if any(t in msg for t in termos) else "particular"

# Responde com base no bloco
def responder_com_bloco(msg):
    for bloco in respostas_automaticas:
        for termo in bloco.get("keywords", []):
            if termo in msg.lower():
                return bloco["response"]
    return None

# Gera resposta com IA (OpenAI)
def gerar_resposta_gpt(mensagem):
    try:
        prompt = f"""
Você é um assistente jurídico do escritório Teixeira.Brito Advogados.

Mensagem recebida do cliente:
{mensagem}

Responda como um advogado experiente, confiável e objetivo.
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
        print("❌ Erro GPT:", str(e))
        return None

# Envia mensagem pela Z-API
def enviar_zapi(phone, message):
    payload = {"phone": phone, "message": message}
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"✅ Enviado para {phone} | Status: {r.status_code} | Resposta: {r.text}")
    except Exception as e:
        print("❌ Erro Z-API:", str(e))

# Endpoint de saúde da API
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Webhook jurídico ativo"}), 200

# Endpoint principal do webhook
@app.route("/webhook", methods=["POST"])
def responder():
    try:
        data = request.json or {}
        print("📩 JSON recebido:", data)

        # Captura segura da mensagem
        mensagem = data.get("message", "").strip() \
            or data.get("text", {}).get("body", "") \
            or data.get("text", {}).get("message", "") \
            or data.get("image", {}).get("caption", "") \
            or ""

        # Identificação do número de quem enviou
        telefone = data.get("participantPhone") or data.get("senderPhone") or data.get("phone") or ""
        nome = data.get("senderName", "")
        grupo = data.get("groupName", "")
        historico = data.get("messageCount", 0)

        # Ignora se campos principais ausentes
        if not mensagem or not telefone:
            print("⚠️ Mensagem ou telefone ausente.")
            return jsonify({"response": None})

        # Ignora se for o número da instância
        if telefone == NUMERO_INSTANCIA:
            print("⛔ Ignorado: número da instância.")
            return jsonify({"response": None})

        # Bloqueios por nome ou grupo
        if nome in bloqueados or grupo in grupos_bloqueados:
            print(f"⛔ Ignorado: bloqueado ({nome or grupo})")
            return jsonify({"response": None})

        # Ignora mensagens com histórico anterior
        if historico > 1:
            print("🔁 Ignorado: histórico > 1")
            return jsonify({"response": None})

        tipo = detectar_assunto(mensagem)

        if tipo == "profissional":
            resposta = responder_com_bloco(mensagem) or gerar_resposta_gpt(mensagem)
            if resposta:
                enviar_zapi(telefone, resposta)
                return jsonify({"response": resposta})

        return jsonify({"response": None})

    except Exception as e:
        print("❌ Erro geral:", str(e))
        return jsonify({"error": "Erro interno"}), 500

# Executa localmente
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
