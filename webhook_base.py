from flask import Flask, request, jsonify
import os
import openai
import requests
from datetime import datetime
import re

app = Flask(__name__)

# === CONFIGURAÇÕES PRINCIPAIS ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuração Z-API
ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "")

# Informações de contato
BACKOFFICE_WHATSAPP = "+55(62)99981-2069"
BACKOFFICE_FIXO = "(62) 3922-3940"
BACKOFFICE_EMAIL = "contato@advgoias.com.br"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# Armazenamento de conversa e estados
CONVERSAS = {}
NOMES_CLIENTES = {}
ULTIMA_MENSAGEM = {}

# === FUNÇÕES DE APOIO ===
def gerar_saudacao():
    hora = datetime.now().hour
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

def extrair_nome(mensagem):
    mensagem = mensagem.strip().lower()
    padroes = [
        r'me chamo (.+)', r'meu nome é (.+)', r'sou (.+)', r'é (.+)',
        r'oi,? sou (.+)', r'olá,? sou (.+)', r'aqui é (.+)',
        r'aqui quem fala é (.+)', r'fala com (.+)', r'pode me chamar de (.+)'
    ]
    for padrao in padroes:
        match = re.match(padrao, mensagem, re.I)
        if match:
            return match.group(1).strip().title()
    if len(mensagem.split()) <= 3 and mensagem.isalpha():
        return mensagem.title()
    return None

def extrair_mensagem(data):
    try:
        if "text" in data and isinstance(data["text"], dict):
            return data["text"].get("message", "").strip()
        if "image" in data:
            return data["image"].get("caption", "").strip()
        if "document" in data:
            caption = data["document"].get("caption", "").strip()
            filename = data["document"].get("filename", "").strip()
            return f"[Documento: {filename}] {caption}"
        return ""
    except Exception as e:
        print(f"Erro ao extrair mensagem: {e}")
        return ""

def e_grupo(numero):
    return "-group" in numero or "g.us" in numero

def deve_responder(mensagem, numero):
    if e_grupo(numero) or not mensagem.strip():
        return False
    if ULTIMA_MENSAGEM.get(numero) == mensagem:
        return False
    ULTIMA_MENSAGEM[numero] = mensagem
    return True

# === ROTAS PRINCIPAIS ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != ZAPI_TOKEN:
        return jsonify({"erro": "Token inválido."}), 403

    data = request.json
    mensagem = extrair_mensagem(data)
    numero = data.get("phone", "")

    if not deve_responder(mensagem, numero):
        return jsonify({"status": "ignorado"})

    if numero not in NOMES_CLIENTES:
        nome_cliente = extrair_nome(mensagem)
        if nome_cliente:
            NOMES_CLIENTES[numero] = nome_cliente
            resposta = f"Obrigado, {nome_cliente}! Encaminhamos sua mensagem para nossa equipe que entrará em contato em breve. Se preferir, entre em contato diretamente pelo telefone {BACKOFFICE_FIXO}, WhatsApp {BACKOFFICE_WHATSAPP} ou pelo e-mail {BACKOFFICE_EMAIL}."
        else:
            resposta = f"{gerar_saudacao()}! Poderia me informar seu nome para que nossa equipe entre em contato com você?"
    else:
        resposta = f"{gerar_saudacao()}, {NOMES_CLIENTES[numero]}! Recebemos sua mensagem e nossa equipe entrará em contato. Caso prefira, pode nos contatar diretamente pelo telefone {BACKOFFICE_FIXO}, WhatsApp {BACKOFFICE_WHATSAPP} ou e-mail {BACKOFFICE_EMAIL}."

    enviar_resposta_via_zapi(numero, resposta)
    return jsonify({"status": "respondido"})

def enviar_resposta_via_zapi(telefone, mensagem):
    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    headers = {"Content-Type": "application/json", "Client-token": CLIENT_TOKEN}
    payload = {"phone": telefone, "message": mensagem}
    requests.post(url, json=payload, headers=headers)

@app.route("/")
def home():
    return "🟢 Whats TB rodando — Atendimento Automatizado Teixeira Brito Advogados"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
