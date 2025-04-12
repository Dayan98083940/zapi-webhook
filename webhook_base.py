from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import json
import requests
import openai

load_dotenv()

app = Flask(__name__)

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")
NUMERO_ESPOSA = "+5562998393940"

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Carrega os blocos de resposta
try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as f:
        blocos_resposta = json.load(f)
except Exception as e:
    print("Erro ao carregar blocos_respostas.json:", e)
    blocos_resposta = []

def detectar_assunto(mensagem):
    palavras_chave = [
        "contrato", "holding", "divórcio", "herança", "inventário",
        "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"
    ]
    mensagem = mensagem.lower()
    return "profissional" if any(p in mensagem for p in palavras_chave) else "particular"

def responder_com_bloco(mensagem):
    for bloco in blocos_resposta:
        for termo in bloco.get("keywords", []):
            if termo.lower() in mensagem.lower():
                return bloco["response"]
    return None

def gerar_resposta_gpt(mensagem):
    try:
        prompt = f"""
Você é o Dr. Dayan, advogado responsável pelo escritório Teixeira.Brito Advogados.

Mensagem recebida:
"{mensagem}"

Responda de forma clara, com linguagem simples e humanizada. Se não entender a solicitação, peça esclarecimentos e ofereça opção de agendamento para atendimento direto.
"""
        resposta = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado experiente e humanizado."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.4
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("Erro GPT:", str(e))
        return None

def enviar_zapi(numero, mensagem):
    payload = {"phone": numero, "message": mensagem}
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"✅ Enviado para {numero} | Resposta: {r.text}")
    except Exception as e:
        print("Erro ao enviar pela Z-API:", str(e))

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mensagem": "Webhook em execução."})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    mensagem = (
        data.get("message", "") or
        data.get("text", {}).get("message", "") or
        data.get("text", {}).get("body", "") or
        data.get("image", {}).get("caption", "") or
        data.get("document", {}).get("caption", "")
    ).strip()

    if not mensagem:
        return jsonify({"response": None})

    telefone = data.get("senderPhone") or data.get("phone", "")
    nome = data.get("senderName", "")

    if telefone == NUMERO_INSTANCIA:
        return jsonify({"response": None})

    tipo = detectar_assunto(mensagem)
    if tipo == "profissional":
        resposta = responder_com_bloco(mensagem) or gerar_resposta_gpt(mensagem)
        if resposta:
            enviar_zapi(telefone, resposta)
            # Resposta extra para sua esposa se for ela
            if telefone.endswith("98393940"):
                enviar_zapi(NUMERO_ESPOSA, "Oi, amor! Já vi sua mensagem e vou te responder pessoalmente em breve ❤️")
            return jsonify({"response": resposta})

    return jsonify({"response": None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
