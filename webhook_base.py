from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")

CONTATO_DIRETO = "+55(62)99808-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"
CONTATO_ATENDIMENTO = "(62) 3922-3940 ou (62)99981-2069"

HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["segunda", "terça", "quarta", "quinta", "sexta"]

CONTATOS_PESSOAIS = ["pai", "mab", "joão", "pedro", "amor", "érika", "helder", "felipe"]
GRUPOS_BLOQUEADOS = ["sagrada família", "providência santa"]

# === SAUDAÇÃO AUTOMÁTICA ===
def gerar_saudacao():
    hora = datetime.now().hour
    if hora < 12:
        return "Bom dia"
    elif 12 <= hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

# === FUNÇÕES DE APOIO ===
def fora_do_horario():
    agora = datetime.now()
    dia_semana = agora.strftime("%A").lower()
    return dia_semana not in DIAS_UTEIS or not (HORARIO_INICIO <= agora.hour < HORARIO_FIM)

def mensagem_pertence_a_grupo(nome):
    return any(g in nome.lower() for g in GRUPOS_BLOQUEADOS)

def contato_excluido(nome):
    return any(p in nome.lower() for p in CONTATOS_PESSOAIS)

# === ROTA PRINCIPAL ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        print("[ERRO] Token inválido na URL.")
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        print("[ERRO] Headers inválidos.")
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    try:
        mensagem = data.get("message", "").strip()
        numero = data.get("phone", "")
        nome = data.get("name", "Cliente")

        print(f"📥 Mensagem recebida de {numero} ({nome}): {mensagem}")

        if mensagem_pertence_a_grupo(nome) or contato_excluido(nome):
            print("[INFO] Mensagem ignorada (grupo ou contato pessoal).")
            return jsonify({"status": "ignorado"})

        saudacao = gerar_saudacao()
        resposta_base = gerar_resposta_gpt(mensagem)

        resposta = f"{saudacao}, Sr(a). {nome}.\n\n{resposta_base}"

        print(f"📤 Resposta enviada: {resposta}")
        return jsonify({"response": resposta})

    except Exception as e:
        print(f"❌ Erro interno ao processar mensagem: {repr(e)}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === GPT PARA RESPOSTAS GERAIS ===
def gerar_resposta_gpt(pergunta):
    prompt = f"""
Você é um assistente jurídico que representa o Dr. Dayan, do escritório Teixeira.Brito Advogados. Especialista em contratos, sucessões, holding, regularização de imóveis, renegociação de dívidas e demandas familiares.

Responda de forma respeitosa, investigativa e objetiva. Sempre inicie com uma pergunta aberta ou direcionadora e ao final oriente:
📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}
Se não conseguir falar diretamente com o Dr. Dayan, entre em contato com o atendimento: {CONTATO_ATENDIMENTO}

Mensagem recebida: {pergunta}
"""
    resposta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return resposta.choices[0].message["content"].strip()

# === ROTA DE STATUS ===
@app.route("/")
def home():
    return "🟢 Servidor Teixeira.Brito com assistente digital ativo."
