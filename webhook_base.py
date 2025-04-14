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
    "poderia me orientar", "ajuda", "tem como", "posso",
    "informação", "processo", "agendar", "consulta", "atendimento"
]

SAUDACOES = ["bom dia", "boa tarde", "boa noite", "olá", "ola", "oi"]

def gerar_saudacao():
    hora = datetime.now().hour
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

def eh_saudacao(mensagem):
    return any(s in mensagem.lower() for s in SAUDACOES)

def deve_responder(mensagem, numero):
    if numero in BLOQUEAR_NUMEROS or "-group" in numero:
        return False
    if numero in ATENDIMENTO_MANUAL and ATENDIMENTO_MANUAL[numero] == str(date.today()):
        print(f"⛔ {numero} em atendimento manual hoje.")
        return False
    return any(g in mensagem.lower() for g in GATILHOS_RESPOSTA)

def formata_tratamento(nome):
    return f"Sr(a). {nome.split()[0].capitalize()}" if nome else "Cliente"

def fora_do_horario():
    agora = datetime.now()
    return agora.hour < 8 or agora.hour >= 18 or agora.weekday() >= 5  # Segunda a sexta, 08 às 18h

@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token") or EXPECTED_CLIENT_TOKEN
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    mensagem = data.get("message", "").strip()
    numero = data.get("phone", "").strip()
    nome = data.get("name", "") or "Cliente"

    print(f"📥 {numero} ({nome}): {mensagem}")

    if not mensagem:
        print("Mensagem vazia — ignorada.")
        return jsonify({"status": "ignorado"})

    if numero in BLOQUEAR_NUMEROS or "-group" in numero:
        print("Número bloqueado ou grupo — ignorado.")
        return jsonify({"status": "ignorado"})

    if eh_saudacao(mensagem):
        resposta = f"{gerar_saudacao()}, {formata_tratamento(nome)}! Como posso ajudar você hoje?"
        enviar_resposta_via_zapi(numero, resposta)
        return jsonify({"status": "respondido"})

    if fora_do_horario():
        resposta = (
            f"{gerar_saudacao()}, {formata_tratamento(nome)}!\n\n"
            "Nosso horário de atendimento é de segunda a sexta, das 08h às 18h. "
            f"Por favor, entre em contato pelo 📞 {CONTATO_FIXO} ou agende um horário 📅 {LINK_CALENDLY}."
        )
        enviar_resposta_via_zapi(numero, resposta)
        return jsonify({"status": "respondido"})

    if deve_responder(mensagem, numero):
        resposta = gerar_resposta_gpt(mensagem, nome)
        enviar_resposta_via_zapi(numero, resposta)
        return jsonify({"status": "respondido"})

    print("Mensagem sem gatilho claro — ignorada.")
    return jsonify({"status": "ignorado"})

def enviar_resposta_via_zapi(telefone, mensagem):
    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-token": EXPECTED_CLIENT_TOKEN
    }
    payload = {"phone": telefone, "message": mensagem}
    try:
        requests.post(url, json=payload, headers=headers)
        print(f"📤 Enviado para {telefone}.")
    except Exception as e:
        print(f"❌ Erro Z-API: {repr(e)}")

def gerar_resposta_gpt(mensagem, nome_cliente):
    tratamento = formata_tratamento(nome_cliente)
    prompt = f"""
Você é o assistente virtual da Teixeira Brito Advogados.

Sua função é:
- Entender e filtrar brevemente a solicitação do cliente.
- NÃO explicar juridicamente.
- Perguntar diretamente se deseja atendimento pelo telefone fixo ou agendar uma reunião com Dr. Dayan.

Mensagem recebida:
{mensagem}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    corpo = response.choices[0].message["content"].strip()
    return (
        f"{gerar_saudacao()}, {tratamento}.\n\n{corpo}\n\n"
        f"📞 {CONTATO_FIXO} | 📅 {LINK_CALENDLY}"
    )

@app.route("/atendimento-manual", methods=["POST"])
def registrar_atendimento_manual():
    numero = request.json.get("numero", "")
    if numero:
        ATENDIMENTO_MANUAL[numero] = str(date.today())
        return jsonify({"status": "registrado", "numero": numero})
    return jsonify({"erro": "Número inválido."}), 400

@app.route("/conversas/<numero>", methods=["GET"])
def mostrar_conversa(numero):
    return jsonify(CONVERSAS.get(numero, ["Sem histórico."]))

@app.route("/")
def home():
    return "🟢 Whats TB rodando com atendimento inteligente"
