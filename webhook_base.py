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
