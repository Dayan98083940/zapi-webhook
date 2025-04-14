from flask import Flask, request, jsonify
import os
import openai
import requests
from datetime import datetime, date

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")

ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"

CONTATO_DIRETO = "+55(62)99808-3940"
CONTATO_FIXO = "(62) 3922-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

BLOQUEAR_NUMEROS = os.getenv("BLOQUEADOS", "").split(",")
CONVERSAS = {}
ATENDIMENTO_MANUAL = {}

GATILHOS_RESPOSTA = [
    "quero", "gostaria", "preciso", "dúvida", "processo",
    "como faço", "o que fazer", "procedimento",
    "orientação", "ajuda", "tem como", "posso", "informação"
]

SAUDACOES = ["bom dia", "boa tarde", "boa noite"]

def gerar_saudacao():
    hora = datetime.now().hour
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

def deve_responder(mensagem, numero):
    if numero in BLOQUEAR_NUMEROS or "-group" in numero:
        return False
    if numero in ATENDIMENTO_MANUAL and ATENDIMENTO_MANUAL[numero] == str(date.today()):
        print(f"⛔ Atendimento manual ativo hoje para: {numero}")
        return False
    mensagem = mensagem.lower()
    return any(g in mensagem for g in GATILHOS_RESPOSTA) or mensagem in SAUDACOES

def formata_tratamento(nome):
    if "advogado" in nome.lower() or "advogada" in nome.lower():
        return f"Dr(a). {nome.split()[0].capitalize()}"
    return f"Sr(a). {nome.split()[0].capitalize()}" if nome else "Cliente"

@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    try:
        data = request.json
        mensagem = data.get("message", "").strip()
        numero = data.get("phone", "").strip()
        nome = data.get("name", "").strip() or "Cliente"

        if not mensagem:
            print(f"📥 Mensagem vazia recebida de {numero} — ignorada.")
            return jsonify({"status": "ignorado", "motivo": "mensagem vazia"})

        if not deve_responder(mensagem, numero):
            print(f"📥 Sem gatilho na mensagem de {numero}: {mensagem}")
            return jsonify({"status": "ignorado", "motivo": "sem gatilho"})

        resposta = gerar_resposta_gpt(mensagem, nome, numero)
        CONVERSAS.setdefault(numero, []).extend([f"Cliente: {mensagem}", f"Assistente: {resposta}"])
        enviar_resposta_via_zapi(numero, resposta)

        return jsonify({"status": "respondido", "para": numero, "mensagem": resposta})

    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

def enviar_resposta_via_zapi(telefone, mensagem):
    if "-group" in telefone or not telefone or not mensagem.strip():
        print(f"🚫 Mensagem bloqueada (grupo ou vazia) para {telefone}.")
        return

    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-token": EXPECTED_CLIENT_TOKEN
    }
    payload = {"phone": telefone, "message": mensagem}
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Enviado para {telefone}, status: {response.status_code}, retorno: {response.text}")
    except Exception as e:
        print(f"❌ Falha ao enviar via Z-API: {repr(e)}")

def gerar_resposta_gpt(mensagem, nome_cliente, numero):
    saudacao = gerar_saudacao()
    tratamento = formata_tratamento(nome_cliente)

    if mensagem.lower() in SAUDACOES:
        return f"{saudacao}, {tratamento}! Como posso ajudar hoje?\n\n📞 {CONTATO_FIXO} | 📅 {LINK_CALENDLY}"

    fora_do_horario = datetime.now().hour < 8 or datetime.now().hour >= 18
    if fora_do_horario:
        return f"{saudacao}, {tratamento}. Nosso atendimento é das 08h às 18h. Para urgências, ligue para {CONTATO_FIXO} ou agende aqui: {LINK_CALENDLY}"

    prompt = f"""
    Você é assistente da Teixeira Brito Advogados. Sua tarefa é apenas:
    - Identificar rapidamente o que o cliente precisa.
    - Perguntar objetivamente se ele prefere atendimento pelo Dr. Dayan ou pela equipe geral.
    - Não dê respostas jurídicas nem explique leis.

    Mensagem recebida: {mensagem}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        corpo = response.choices[0].message["content"].strip()
    except Exception as e:
        corpo = "Não consegui gerar uma resposta neste momento. Por favor, ligue diretamente para nosso escritório."

    return f"{saudacao}, {tratamento}.\n\n{corpo}\n\n📞 {CONTATO_FIXO} | 📅 {LINK_CALENDLY}"

@app.route("/atendimento-manual", methods=["POST"])
def registrar_atendimento_manual():
    data = request.json
    numero = data.get("numero", "").strip()
    if numero:
        ATENDIMENTO_MANUAL[numero] = str(date.today())
        return jsonify({"status": "registrado", "numero": numero})
    return jsonify({"erro": "Número inválido."}), 400

@app.route("/conversas/<numero>", methods=["GET"])
def mostrar_conversa(numero):
    return jsonify(CONVERSAS.get(numero, ["Sem histórico."]))

@app.route("/")
def home():
    return "🟢 Whats TB rodando — Atendimento automático Teixeira Brito"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
