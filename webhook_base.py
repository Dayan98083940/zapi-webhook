from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os, openai, requests
from datetime import datetime

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")

ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"

CONTATO_FIXO = "(62) 3922-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

BLOQUEAR_NUMEROS = os.getenv("BLOQUEADOS", "").split(",")
ATENDIMENTO_MANUAL = {}

def gerar_saudacao():
    hora = datetime.now().hour
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

@app.route(f"/webhook/{WEBHOOK_URL_TOKEN}/receive", methods=["POST"])
def receber_mensagem():
    client_token = request.headers.get("Client-token")
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    mensagem = data.get("message", "").strip()
    numero = data.get("phone", "").strip()
    nome = data.get("name", "Cliente")

    if not mensagem or numero in BLOQUEAR_NUMEROS or "-group" in numero:
        return jsonify({"status": "ignorado"})

    tratamento = f"Sr(a). {nome.split()[0].capitalize()}" if nome else "Cliente"
    saudacao = gerar_saudacao()

    if mensagem.lower() in ["bom dia", "boa tarde", "boa noite"]:
        resposta = f"{saudacao}, {tratamento}! Como posso ajudar hoje?"
    elif datetime.now().hour >= 18 or datetime.now().hour < 8:
        resposta = (f"{saudacao}, {tratamento}. Nosso atendimento é das 8h às 18h. "
                    f"Ligue para {CONTATO_FIXO} ou agende pelo link {LINK_CALENDLY}.")
    else:
        resposta = gerar_resposta_gpt(mensagem, tratamento)

    enviar_resposta(numero, resposta)
    return jsonify({"status": "respondido", "para": numero})

def enviar_resposta(numero, resposta):
    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-token": EXPECTED_CLIENT_TOKEN
    }
    payload = {"phone": numero, "message": resposta}

    try:
        r = requests.post(url, json=payload, headers=headers)
        print(f"Resposta enviada para {numero}, status: {r.status_code}, retorno: {r.text}")
    except Exception as e:
        print(f"Erro envio Z-API: {e}")

def gerar_resposta_gpt(mensagem, tratamento):
    prompt = f"""
    Você é assistente jurídico da Teixeira Brito Advogados.
    
    Sua função:
    - Acolher, entender rapidamente e filtrar a necessidade.
    - Não explique a lei, mas busque mais informações se necessário.
    - Indique sempre opção de ligação direta ou agendamento.

    Mensagem cliente:
    {mensagem}
    """

    resposta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    ).choices[0].message["content"].strip()

    return f"{tratamento}, {resposta}\n\n📞 {CONTATO_FIXO} | 📅 {LINK_CALENDLY}"

@app.route("/")
def home():
    return "🟢 WhatsApp Concierge TB Ativo."

if __name__ == "__main__":
    app.run()
