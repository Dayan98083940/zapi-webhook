from flask import Flask, request, jsonify
import os
import json
import openai
import requests
from datetime import datetime, date

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")
EXPECTED_CLIENT_TOKEN = "F124e80fa9ba94101a6eb723b5a20d2b3S"

ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"

CONTATO_DIRETO = "+55(62)99808-3940"
CONTATO_FIXO = "(62) 3922-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# === CONTROLES ===
BLOQUEAR_NUMEROS = os.getenv("BLOQUEADOS", "").split(",")
CONVERSAS = {}
ATENDIMENTO_MANUAL = {}  # {"556299999999": "2024-04-14"}

GATILHOS_RESPOSTA = [
    "quero", "gostaria", "preciso", "tenho uma dúvida",
    "como faço", "o que fazer", "qual o procedimento",
    "poderia me orientar", "ajuda", "tem como", "posso"
]

# === FUNÇÕES ===
def gerar_saudacao():
    hora = datetime.now().hour
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

def deve_responder(mensagem, numero):
    if numero in BLOQUEAR_NUMEROS or "-group" in numero:
        return False
    if numero in ATENDIMENTO_MANUAL and ATENDIMENTO_MANUAL[numero] == str(date.today()):
        print(f"⛔ {numero} está em atendimento manual hoje.")
        return False
    return any(g in mensagem.lower() for g in GATILHOS_RESPOSTA)

def formata_tratamento(nome):
    return f"Sr(a). {nome.split()[0].capitalize()}" if nome else "Cliente"

# === WEBHOOK PRINCIPAL ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    if not client_token:
        client_token = EXPECTED_CLIENT_TOKEN
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    try:
        data = request.json
        mensagem = data.get("message", "").strip()
        numero = data.get("phone", "").strip()
        nome = data.get("name", "") or "Cliente"

        print(f"📥 {numero} ({nome}): {mensagem}")

        if not deve_responder(mensagem, numero):
            return jsonify({"status": "ignorado"})

        resposta = gerar_resposta_gpt(mensagem, nome, numero)

        if numero not in CONVERSAS:
            CONVERSAS[numero] = []
        CONVERSAS[numero].append(f"Cliente: {mensagem}")
        CONVERSAS[numero].append(f"Assistente: {resposta}")

        enviar_resposta_via_zapi(numero, resposta)
        return jsonify({"status": "respondido", "para": numero})

    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === ENVIO VIA Z-API ===
def enviar_resposta_via_zapi(telefone, mensagem):
    if not telefone or "-group" in telefone or not mensagem.strip():
        return
    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-token": "F124e80fa9ba94101a6eb723b5a20d2b3S"
    }
    payload = {"phone": telefone, "message": mensagem}
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Enviado para {telefone} ✅ Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Falha ao enviar via Z-API: {repr(e)}")

# === GERADOR DE RESPOSTA CONCIERGE ===
def gerar_resposta_gpt(mensagem, nome_cliente, numero):
    saudacao = gerar_saudacao()
    tratamento = formata_tratamento(nome_cliente)

    prompt = f"""
Você é um assistente jurídico estratégico da Teixeira Brito Advogados.

Seu papel:
- Ouvir o cliente com atenção
- NÃO resolver juridicamente
- NÃO explicar leis
- Apenas acolher e perguntar se o cliente deseja:
  - falar com Dr. Dayan diretamente
  - ou agendar com a equipe

Mensagem recebida:
{mensagem}
"""

    introducao = (
        f"{saudacao}, {tratamento}.\n\n"
        "Recebi sua mensagem e quero entender melhor sua situação para direcionar da melhor forma.\n"
        "📌 Deseja falar com o Dr. Dayan ou prefere que nossa equipe entre em contato?\n"
        f"📞 {CONTATO_FIXO} | 📅 {LINK_CALENDLY}"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    corpo = response.choices[0].message["content"].strip()
    return f"{introducao}\n\n{corpo}"

# === REGISTRA QUE VOCÊ ASSUMIU O ATENDIMENTO ===
@app.route("/atendimento-manual", methods=["POST"])
def registrar_atendimento_manual():
    data = request.json
    numero = data.get("numero", "")
    if numero:
        ATENDIMENTO_MANUAL[numero] = str(date.today())
        return jsonify({"status": "registrado", "numero": numero})
    return jsonify({"erro": "Número inválido."}), 400

# === CONSULTA HISTÓRICO ===
@app.route("/conversas/<numero>", methods=["GET"])
def mostrar_conversa(numero):
    return jsonify(CONVERSAS.get(numero, ["Sem histórico para este número."]))

@app.route("/")
def home():
    return "🟢 Whats TB rodando — Concierge Jurídico com Estilo Dayan"
