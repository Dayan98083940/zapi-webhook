from flask import Flask, request, jsonify
import os
import openai
import requests
from datetime import datetime, date
import re

app = Flask(__name__)

# === CONFIGURAÇÕES PRINCIPAIS ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuração Z-API
ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "")

# Informações de contato
CONTATO_DIRETO = "+55(62)99808-3940"
CONTATO_FIXO = "(62) 3922-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# Armazenamento de conversa e estados
CONVERSAS = {}
ATENDIMENTO_MANUAL = {}
ESTADO_CONVERSA = {}
NOMES_CLIENTES = {}

# Estados da conversa
ESTADO_INICIAL = 0
ESTADO_ESPERA_NOME = 1
ESTADO_ESPERA_DUVIDA = 2
ESTADO_ATENDIMENTO = 3

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
    return mensagem.title()

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
        if "message" in data:
            return data["message"].get("text", "").strip() if isinstance(data["message"], dict) else str(data["message"]).strip()
        return ""
    except Exception as e:
        print(f"Erro ao extrair mensagem: {e}")
        return ""

def e_grupo(numero):
    return "-group" in numero or "g.us" in numero or numero.startswith("120363")

def deve_responder(mensagem, numero):
    if e_grupo(numero) or numero in ATENDIMENTO_MANUAL or not mensagem.strip():
        return False
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

    estado_atual = ESTADO_CONVERSA.get(numero, ESTADO_INICIAL)

    if estado_atual == ESTADO_INICIAL:
        ESTADO_CONVERSA[numero] = ESTADO_ESPERA_NOME
        resposta = f"{gerar_saudacao()}! Poderia me dizer seu nome?"

    elif estado_atual == ESTADO_ESPERA_NOME:
        nome_cliente = extrair_nome(mensagem)
        NOMES_CLIENTES[numero] = nome_cliente
        ESTADO_CONVERSA[numero] = ESTADO_ESPERA_DUVIDA
        resposta = f"Obrigado, {nome_cliente}! Como posso te ajudar hoje?"

    else:
        resposta = analisar_duvida_cliente(mensagem, NOMES_CLIENTES.get(numero, "Cliente"))

    enviar_resposta_via_zapi(numero, resposta)
    return jsonify({"status": "respondido"})

def analisar_duvida_cliente(mensagem, nome_cliente):
    prompt = f"""Você é um assistente jurídico educado.
Cliente: {nome_cliente}
Mensagem: {mensagem}
Faça perguntas adicionais se necessário para entender melhor a necessidade do cliente e dê orientações gerais. Sugira contato ou agendamento para casos específicos."""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3, max_tokens=400
    )

    corpo = response.choices[0].message["content"].strip()
    return f"{corpo}\n\nAgende: {LINK_CALENDLY}\nTel: {CONTATO_FIXO} | Cel: {CONTATO_DIRETO}"

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
