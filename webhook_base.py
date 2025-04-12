from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import requests

# Inicialização
app = Flask(__name__)
load_dotenv()

# Configurações via .env
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"

# Listas de bloqueio removidas
bloqueados = []
grupos_bloqueados = []

# Carregamento das respostas
try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as f:
        respostas_automaticas = json.load(f)
except Exception as e:
    print(f"❌ Erro ao carregar blocos_respostas.json: {e}")
    respostas_automaticas = []

# Função para detectar assuntos profissionais
def detectar_assunto(texto):
    palavras_chave = [
        "contrato", "holding", "divórcio", "herança", "inventário",
        "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"
    ]
    return "profissional" if any(p in texto.lower() for p in palavras_chave) else "particular"

# Função para buscar bloco de resposta
def buscar_resposta(msg):
    msg_lower = msg.lower()
    for bloco in respostas_automaticas:
        for termo in bloco.get("keywords", []):
            if termo in msg_lower:
                return bloco.get("response")
    return None

# Envio via Z-API com cabeçalho obrigatório
def enviar_resposta_zapi(telefone, texto):
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    payload = {"phone": telefone, "message": texto}
    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"✅ Enviado para {telefone} | {r.status_code} | {r.text}")
    except Exception as e:
        print(f"❌ Falha ao enviar mensagem: {e}")

# Rota para status
@app.route("/", methods=["GET"])
def status():
    return jsonify({"status": "ativo", "descricao": "Webhook jurídico"}), 200

# Rota principal para Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json or {}
        mensagem = (
            data.get("message", "") or
            data.get("text", {}).get("message", "") or
            data.get("text", {}).get("body", "") or
            data.get("image", {}).get("caption", "") or
            data.get("document", {}).get("caption", "") or ""
        ).strip()

        if not mensagem:
            return jsonify({"response": None})

        telefone = data.get("senderPhone") or data.get("phone", "")
        if telefone == NUMERO_INSTANCIA:
            return jsonify({"response": None})

        # Normaliza número da esposa se necessário
        if telefone == "556298393940":
            telefone = "5562998393940"

        tipo_assunto = detectar_assunto(mensagem)

        if tipo_assunto == "profissional":
            resposta = buscar_resposta(mensagem)
            if resposta:
                enviar_resposta_zapi(telefone, resposta)
                return jsonify({"response": resposta})

        return jsonify({"response": None})
    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return jsonify({"error": "Erro interno"}), 500

# Inicialização do servidor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
