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
ARQUIVO_CONTROLE = "controle_interacoes.json"

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

# === PALAVRAS-CHAVE (respostas serão completadas posteriormente) ===
PALAVRAS_CHAVE = {
    "inventário": "...",
    "contrato": "...",
    "divórcio": "...",
    "leilão": "...",
    "atraso de obra": "...",
    "regularização de imóveis": "...",
    "holding": "...",
    "holding familiar": "...",
    "holding rural": "...",
    "holding imobiliária": "...",
    "averbação": "regularização de imóveis",
    "usucapião": "regularização de imóveis",
    "imóvel irregular": "regularização de imóveis"
}

# === ROTA PRINCIPAL ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    try:
        mensagem = data.get("message", "").strip().lower()
        numero = data.get("phone", "")
        nome = data.get("name", "Cliente")

        if mensagem_pertence_a_grupo(nome) or contato_excluido(nome):
            return jsonify({"status": "ignorado"})

        saudacao = gerar_saudacao()
        chave = mensagem.strip()

        if chave in PALAVRAS_CHAVE:
            resposta_base = PALAVRAS_CHAVE.get(PALAVRAS_CHAVE[chave], PALAVRAS_CHAVE[chave])
        else:
            resposta_base = gerar_resposta_gpt(mensagem)

        resposta = f"{saudacao}, Sr(a). {nome}.\n\n{resposta_base}"

        return jsonify({"response": resposta})

    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === GPT para perguntas abertas ===
def gerar_resposta_gpt(pergunta):
    prompt = f"""
Você é assistente jurídico do escritório Teixeira.Brito Advogados, liderado pelo Dr. Dayan. Especialista em contratos, sucessões, holding, renegociação de dívidas e regularização de imóveis.

Responda com clareza, segurança jurídica e objetividade.

Ao final da resposta, sempre oriente:
📌 Ligue para: +55(62)99808-3940 ou agende: https://calendly.com/dayan-advgoias

Pergunta: {pergunta}
"""
    resposta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return resposta.choices[0].message["content"].strip()

# === ROTA DE SAÚDE ===
@app.route("/")
def home():
    return "🟢 Servidor Teixeira.Brito com assistente digital ativo."
