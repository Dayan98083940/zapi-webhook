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
ATENDIMENTO_MANUAL = {}  # {"556299999999": "YYYY-MM-DD"}

GATILHOS_RESPOSTA = [
    "quero", "gostaria", "preciso", "tenho uma dúvida", "como faço",
    "o que fazer", "qual o procedimento", "poderia me orientar",
    "ajuda", "tem como", "posso", "é possível", "vocês fazem", "me explica"
]

SAUDACOES = ["bom dia", "boa tarde", "boa noite", "oi", "olá"]

# === FUNÇÕES ===
def gerar_saudacao():
    hora = datetime.now().hour
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

def identificar_tipo_demanda(mensagem):
    texto = mensagem.lower().strip()

    if any(saud in texto for saud in SAUDACOES):
        return "SAUDACAO"
    if any(gatilho in texto for gatilho in GATILHOS_RESPOSTA):
        return "DIRECIONAR"
    return False

def demanda_esta_clara(mensagem):
    palavras_chave = ["abrir", "fazer", "realizar", "constituir", "iniciar", "resolver", "contrato", "holding", "inventário"]
    return any(p in mensagem.lower() for p in palavras_chave) and len(mensagem.split()) >= 8

def formata_tratamento(nome):
    return f"Sr(a). {nome.split()[0].capitalize()}" if nome else "Cliente"

# === WEBHOOK PRINCIPAL ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")
    if not client_token:
        client_token = EXPECTED_CLIENT_TOKEN

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    try:
        data = request.json
        mensagem = data.get("message", "").strip()
        numero = data.get("phone", "").strip()
        nome = data.get("name", "") or "Cliente"

        print(f"📥 {numero} ({nome}): {mensagem}")

        if numero in BLOQUEAR_NUMEROS or "-group" in numero:
            return jsonify({"status": "ignorado", "motivo": "grupo ou bloqueado"})

        if numero in ATENDIMENTO_MANUAL and ATENDIMENTO_MANUAL[numero] == str(date.today()):
            return jsonify({"status": "ignorado", "motivo": "atendimento manual ativo"})

        tipo = identificar_tipo_demanda(mensagem)
        tratamento = formata_tratamento(nome)
        saudacao = gerar_saudacao()

        if tipo == "SAUDACAO":
            resposta = f"{saudacao}, {tratamento}.\n\nEm que posso te ajudar?"
        elif tipo == "DIRECIONAR":
            if demanda_esta_clara(mensagem):
                resposta = (
                    f"{saudacao}, {tratamento}.\n\n"
                    "Sua mensagem já traz as informações necessárias para iniciarmos o atendimento.\n\n"
                    "Deseja:\n"
                    f"📞 Falar com o Dr. Dayan: {CONTATO_DIRETO}\n"
                    f"📅 Agendar um horário online: {LINK_CALENDLY}"
                )
            else:
                resposta = (
                    f"{saudacao}, {tratamento}.\n\n"
                    "Recebi sua mensagem, mas para poder direcionar corretamente, poderia me dar mais detalhes sobre sua situação?"
                )
        else:
            return jsonify({"status": "ignorado", "motivo": "sem gatilho"})

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
        print(f"❌ Erro ao enviar via Z-API: {repr(e)}")

# === REGISTRO DE ATENDIMENTO MANUAL ===
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
    return jsonify(CONVERSAS.get(numero, ["Sem histórico."]))

@app.route("/")
def home():
    return "🟢 Whats TB — Concierge Inteligente com Direcionamento Estratégico"
