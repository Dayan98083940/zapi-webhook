from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import openai
import requests

app = Flask(__name__)
load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as file:
        respostas_automaticas = json.load(file)
except Exception as e:
    print("❌ Erro ao carregar blocos_respostas.json:", str(e))
    respostas_automaticas = []

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
Você é o Dr. Dayan, advogado responsável pelo escritório Teixeira.Brito Advogados.

Mensagem recebida:
"{mensagem}"

Responda com clareza, profissionalismo e empatia. Seja direto como um advogado confiável e experiente.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é o Dr. Dayan, advogado especialista em direito civil e empresarial."},
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

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "message": "Webhook jurídico ativo"}), 200

@app.route("/webhook", methods=["POST"])
def responder():
    try:
        data = request.json or {}
        print("📩 JSON recebido:", data)

        mensagem = data.get("message", "").strip() \
            or data.get("text", {}).get("message", "") \
            or data.get("text", {}).get("body", "") \
            or data.get("image", {}).get("caption", "") \
            or data.get("document", {}).get("caption", "") \
            or ""

        if not mensagem:
            print("⚠️ Mensagem ausente.")
            return jsonify({"response": None})

        # Corrigido: identificação correta do número para envio
        telefone = ""
        if data.get("isGroup", False) and data.get("participantPhone"):
            telefone = data["participantPhone"]
        else:
            telefone = data.get("senderPhone") or data.get("phone", "")

        nome = data.get("senderName", "")
        grupo = data.get("groupName", "")

        if not telefone:
            print("⚠️ Telefone ausente.")
            return jsonify({"response": None})

        if telefone == NUMERO_INSTANCIA:
            print("⛔ Ignorado: número da instância.")
            return jsonify({"response": None})

        if nome in bloqueados or grupo in grupos_bloqueados:
            print(f"⛔ Ignorado: contato ou grupo bloqueado ({nome or grupo})")
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
