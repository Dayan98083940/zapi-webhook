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

# === IDENTIFICADOR DE PALAVRA-CHAVE ===
def identificar_palavra_chave(texto):
    texto = texto.lower()
    if "inventário" in texto:
        return "inventário"
    elif "contrato" in texto:
        return "contrato"
    elif "divórcio" in texto:
        return "divórcio"
    elif "leilão" in texto:
        return "leilão"
    elif "obra" in texto and "atras" in texto:
        return "atraso de obra"
    elif any(p in texto for p in ["usucapião", "averbação", "formalizar", "imóvel irregular", "regularizar"]):
        return "regularização de imóveis"
    elif "holding familiar" in texto:
        return "holding familiar"
    elif "holding rural" in texto:
        return "holding rural"
    elif "holding imobiliária" in texto:
        return "holding imobiliária"
    elif "holding" in texto:
        return "holding"
    else:
        return None

# === PALAVRAS-CHAVE (exemplo reduzido) ===
PALAVRAS_CHAVE = {
    "inventário": "Mensagem padrão para inventário...",
    "contrato": "Mensagem padrão para contrato..."
}

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
        chave = identificar_palavra_chave(mensagem)

        if chave in PALAVRAS_CHAVE:
            resposta_base = PALAVRAS_CHAVE.get(PALAVRAS_CHAVE[chave], PALAVRAS_CHAVE[chave])
        else:
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

# === ROTA DE STATUS ===
@app.route("/")
def home():
    return "🟢 Servidor Teixeira.Brito com assistente digital ativo."
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

# === IDENTIFICADOR DE PALAVRA-CHAVE ===
def identificar_palavra_chave(texto):
    texto = texto.lower()
    if "inventário" in texto:
        return "inventário"
    elif "contrato" in texto:
        return "contrato"
    elif "divórcio" in texto:
        return "divórcio"
    elif "leilão" in texto:
        return "leilão"
    elif "obra" in texto and "atras" in texto:
        return "atraso de obra"
    elif any(p in texto for p in ["usucapião", "averbação", "formalizar", "imóvel irregular", "regularizar"]):
        return "regularização de imóveis"
    elif "holding familiar" in texto:
        return "holding familiar"
    elif "holding rural" in texto:
        return "holding rural"
    elif "holding imobiliária" in texto:
        return "holding imobiliária"
    elif "holding" in texto:
        return "holding"
    else:
        return None

# === PALAVRAS-CHAVE (exemplo reduzido) ===
PALAVRAS_CHAVE = {
    "inventário": "Mensagem padrão para inventário...",
    "contrato": "Mensagem padrão para contrato..."
}

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
        chave = identificar_palavra_chave(mensagem)

        if chave in PALAVRAS_CHAVE:
            resposta_base = PALAVRAS_CHAVE.get(PALAVRAS_CHAVE[chave], PALAVRAS_CHAVE[chave])
        else:
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

# === ROTA DE STATUS ===
@app.route("/")
def home():
    return "🟢 Servidor Teixeira.Brito com assistente digital ativo."
