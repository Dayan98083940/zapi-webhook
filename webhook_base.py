from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import openai
import requests
from datetime import datetime

app = Flask(__name__)
load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Lista vazia de bloqueio (controle manual)
bloqueados = []
grupos_bloqueados = []

# Carregar respostas automáticas
try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as file:
        respostas_automaticas = json.load(file)
except Exception as e:
    print("❌ Erro ao carregar blocos_respostas.json:", str(e))
    respostas_automaticas = []

# === Funções de Apoio ===
def formatar_numero(numero_raw):
    numero = ''.join(filter(str.isdigit, numero_raw))
    if len(numero) == 12 and numero.startswith("55") and numero[4] != '9':
        numero = numero[:4] + '9' + numero[4:]
    return numero

def detectar_assunto(msg):
    termos = ["contrato", "holding", "divórcio", "herança", "inventário", 
              "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"]
    msg = msg.lower()
    return "profissional" if any(t in msg for t in termos) else "particular"

def responder_com_bloco(msg):
    for bloco in respostas_automaticas:
        for termo in bloco.get("keywords", []):
            if termo in msg.lower():
                return bloco["response"]
    return None

def gerar_resposta_gpt(mensagem):
    try:
        prompt = f"""
Você é o Dr. Dayan, advogado do escritório Teixeira.Brito. Mensagem recebida: "{mensagem}"
Responda com clareza e empatia, sem jargões jurídicos. Se a dúvida não estiver clara, peça mais informações.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado especialista em direito civil e empresarial. Linguagem clara e objetiva."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Erro GPT:", str(e))
        return None

def enviar_zapi(phone, message):
    numero_formatado = formatar_numero(phone)
    payload = {
        "phone": numero_formatado,
        "message": message
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"✅ Enviado para {numero_formatado} | Status: {r.status_code} | Resposta: {r.text}")
    except Exception as e:
        print("❌ Erro ao enviar pela Z-API:", str(e))

# === Endpoints ===
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "message": "Webhook jurídico ativo"}), 200

@app.route("/webhook", methods=["POST"])
def responder():
    try:
        data = request.json or {}
        print("📩 JSON recebido:", data)

        mensagem = (
            data.get("message", "") or
            data.get("text", {}).get("message", "") or
            data.get("text", {}).get("body", "") or
            data.get("image", {}).get("caption", "") or
            data.get("document", {}).get("caption", "")
        ).strip()

        if not mensagem:
            print("⚠️ Mensagem ausente.")
            return jsonify({"response": None})

        is_group = data.get("isGroup", False)
        telefone = data.get("participantPhone") if is_group else data.get("senderPhone") or data.get("phone", "")
        nome = data.get("senderName", "")
        grupo = data.get("groupName", "")

        if not telefone or telefone == NUMERO_INSTANCIA:
            return jsonify({"response": None})

        if nome in bloqueados or grupo in grupos_bloqueados:
            print(f"⛔ Ignorado: bloqueado ({nome or grupo})")
            return jsonify({"response": None})

        if is_group and NUMERO_INSTANCIA not in mensagem:
            print("👥 Ignorado: grupo sem menção direta ao número.")
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
