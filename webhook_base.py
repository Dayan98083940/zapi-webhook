from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import openai
import requests

load_dotenv()

app = Flask(__name__)

# Variáveis de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Dados de bloqueio
bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

# Respostas automáticas
with open("blocos_respostas.json", "r", encoding="utf-8") as file:
    respostas_automaticas = json.load(file)

def detectar_assunto(msg):
    profissionais = ["contrato", "holding", "divórcio", "herança", "inventário", "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"]
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
Você é um assistente jurídico que trabalha para o escritório Teixeira.Brito Advogados.

Mensagem recebida: {mensagem}

Responda de forma clara, técnica e cordial.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico experiente."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Erro ao gerar resposta com OpenAI:", str(e))
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
        print(f"✅ Mensagem enviada - Status: {r.status_code} - Resposta: {r.text}")
    except Exception as e:
        print("Erro ao enviar para Z-API:", str(e))

@app.route("/webhook", methods=["POST"])
def responder():
    data = request.json
    nome = data.get("senderName")
    grupo = data.get("groupName")
    mensagem = data.get("message")
    historico = data.get("messageCount")
    telefone = data.get("senderPhone")

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
        else:
            return jsonify({"response": "Recebemos sua mensagem. Em breve nossa equipe entrará em contato."})

    return jsonify({"response": None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
