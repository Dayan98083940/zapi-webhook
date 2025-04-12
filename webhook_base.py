from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import requests

app = Flask(__name__)
load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")  # Ex: 5562998083940
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"

# ✅ Header obrigatório para Z-API
HEADERS = {
    "Content-Type": "application/json",
    "Client-Token": ZAPI_TOKEN
}

# Carrega respostas automáticas
try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as file:
        blocos = json.load(file)
except Exception as e:
    print(f"Erro ao carregar blocos_respostas.json: {e}")
    blocos = []

@app.route("/", methods=["GET"])
def status():
    return jsonify({"status": "ativo", "message": "Webhook jurídico online"}), 200

@app.route("/webhook", methods=["POST"])
def receber():
    try:
        data = request.json or {}
        print("📩 JSON recebido:", data)

        mensagem = (
            data.get("message") or
            data.get("text", {}).get("message") or
            data.get("text", {}).get("body") or
            data.get("image", {}).get("caption") or
            data.get("document", {}).get("caption") or
            ""
        ).strip().lower()

        if not mensagem:
            return jsonify({"response": None})

        telefone = data.get("senderPhone") or data.get("phone", "")
        nome = data.get("senderName", "")
        grupo = data.get("groupName", "")
        is_group = data.get("isGroup", False)

        # Ignora mensagens sem remetente ou número da instância
        if not telefone or telefone == NUMERO_INSTANCIA:
            return jsonify({"response": None})

        # ✅ Só responde em grupo se o número da instância for mencionado
        if is_group and NUMERO_INSTANCIA not in mensagem:
            return jsonify({"response": None})

        # ✅ Analisa mensagem por palavras-chave nos blocos
        for bloco in blocos:
            for termo in bloco.get("keywords", []):
                if termo in mensagem:
                    resposta = bloco.get("response")
                    if resposta:
                        enviar_zapi(telefone, resposta)
                        return jsonify({"response": resposta})

        return jsonify({"response": None})
    except Exception as e:
        print(f"❌ Erro ao processar webhook: {e}")
        return jsonify({"error": "Erro interno"}), 500

def enviar_zapi(phone, message):
    payload = {
        "phone": phone,
        "message": message
    }
    try:
        resposta = requests.post(ZAPI_URL, json=payload, headers=HEADERS)
        print(f"✅ Enviado para {phone} | Status: {resposta.status_code} | Resposta: {resposta.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem Z-API: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
