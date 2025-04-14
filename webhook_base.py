from flask import Flask, request, jsonify
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os, openai, requests
from datetime import datetime, date

load_dotenv()

app = Flask(__name__)

# Configurações de API
openai.api_key = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")

ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"

# Contatos e links
CONTATO_FIXO = "(62) 3922-3940"
CONTATO_DIRETO = "+55(62)99808-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# Controles de bloqueio e atendimento manual
BLOQUEAR_NUMEROS = os.getenv("BLOQUEADOS", "").split(",")
ATENDIMENTO_MANUAL = {}

# Lista de saudações possíveis
SAUDACOES = ["bom dia", "boa tarde", "boa noite", "oi", "olá"]

def gerar_saudacao():
    hora = datetime.now().hour
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

def deve_responder(mensagem, numero):
    if numero in BLOQUEAR_NUMEROS or "-group" in numero:
        return False
    if ATENDIMENTO_MANUAL.get(numero) == str(date.today()):
        return False
    return bool(mensagem.strip())

def formata_tratamento(nome):
    return f"Sr(a). {nome.split()[0].capitalize()}" if nome else "Cliente"

@app.route(f"/webhook/{WEBHOOK_URL_TOKEN}/receive", methods=["POST"])
def receber_mensagem():
    client_token = request.headers.get("Client-token")
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    mensagem = data.get("message", "").strip()
    numero = data.get("phone", "").strip()
    nome = data.get("name", "").strip() or "Cliente"

    if not deve_responder(mensagem, numero):
        return jsonify({"status": "ignorado"})

    tratamento = formata_tratamento(nome)
    saudacao = gerar_saudacao()

    if mensagem.lower() in SAUDACOES:
        resposta = f"{saudacao}, {tratamento}! Como posso ajudar hoje?"
    elif datetime.now().hour >= 18 or datetime.now().hour < 8:
        resposta = (f"{saudacao}, {tratamento}. Nosso atendimento é das 8h às 18h. "
                    f"Ligue para {CONTATO_FIXO} ou agende pelo link {LINK_CALENDLY}.")
    else:
        resposta = gerar_resposta_gpt(mensagem, tratamento)

    enviar_resposta(numero, resposta)
    return jsonify({"status": "respondido", "para": numero})

def enviar_resposta(numero, resposta):
    if not numero or "-group" in numero:
        return
    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-token": EXPECTED_CLIENT_TOKEN
    }
    payload = {"phone": numero, "message": resposta}

    try:
        r = requests.post(url, json=payload, headers=headers)
        print(f"📤 Enviado para {numero}, status: {r.status_code}, retorno: {r.text}")
    except Exception as e:
        print(f"❌ Erro envio Z-API: {e}")

def gerar_resposta_gpt(mensagem, tratamento):
    prompt = f"""
    Você é um assistente jurídico da Teixeira Brito Advogados.

    Seu papel:
    - Acolher o cliente, identificar necessidade específica rapidamente.
    - NÃO explique leis, procedimentos detalhados, nem dê consultoria.
    - Sempre pergunte se deseja ligar diretamente ou agendar atendimento.

    Mensagem do cliente: {mensagem}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    texto_resposta = response.choices[0].message["content"].strip()

    return (f"{tratamento}, {texto_resposta}\n\n"
            f"📞 Ligue: {CONTATO_FIXO} ou {CONTATO_DIRETO}\n"
            f"📅 Agende: {LINK_CALENDLY}")

@app.route("/atendimento-manual", methods=["POST"])
def registrar_atendimento_manual():
    data = request.json
    numero = data.get("numero", "").strip()
    if numero:
        ATENDIMENTO_MANUAL[numero] = str(date.today())
        return jsonify({"status": "registrado", "numero": numero})
    return jsonify({"erro": "Número inválido."}), 400

@app.route("/conversas/<numero>", methods=["GET"])
def historico_conversa(numero):
    return jsonify({"status": "indisponível"})

@app.route("/")
def home():
    return "🟢 WhatsApp Concierge TB Ativo."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
