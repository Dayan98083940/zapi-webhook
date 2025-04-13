from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime
import re

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN") or os.getenv("TOKEN_DA_INSTANCIA")
HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["segunda", "terça", "quarta", "quinta", "sexta"]

# === CONTATOS EXCLUÍDOS ===
CONTATOS_PESSOAIS = ["pai", "mab", "joão", "pedro", "amor", "érika", "helder", "felipe"]
GRUPOS_BLOQUEADOS = ["sagrada família", "providência santa"]

# === DADOS DE CONTATO ===
CONTATO_DIRETO = "(62) 99981-2069"
CONTATO_FIXO = "(62) 3922-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"
ARQUIVO_CONTROLE = "controle_interacoes.json"

# === PALAVRAS-CHAVE ESPECIAIS ===
PALAVRAS_CHAVE = {
    "inventário": "Para inventário, podemos dar andamento de forma rápida. Para isso, vou precisar de alguns documentos. Quer que eu envie a lista completa?",
    "contrato": "Qual contrato você precisa? Fale mais sobre o negócio jurídico que deseja formalizar. Podemos preparar com toda segurança.",
    "divórcio": "Se for consensual, conseguimos resolver rapidamente. Caso contrário, analisamos o cenário. Quer marcar um horário para orientação detalhada?",
    "renegociação de dívidas": "Trabalhamos com renegociação de dívidas bancárias e empresariais. Me conte um pouco da situação para podermos orientar melhor.",
    "atraso de obra": "Você está com problema em obra atrasada? Posso te ajudar a avaliar se cabe restituição ou ação por descumprimento contratual.",
    "leilão": "Você está interessado em acompanhar um leilão ou deseja cancelar um? Podemos te orientar nos dois casos.",
    "holding": "Você deseja estruturar uma holding familiar ou rural? Podemos agendar um diagnóstico e organizar tudo com segurança jurídica."
}

# === CARREGAR CONTROLE DE INTERAÇÕES ===
def carregar_controle():
    if os.path.exists(ARQUIVO_CONTROLE):
        with open(ARQUIVO_CONTROLE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_controle(controle):
    with open(ARQUIVO_CONTROLE, "w", encoding="utf-8") as f:
        json.dump(controle, f, indent=2, ensure_ascii=False)

controle = carregar_controle()

# === CHECAR HORÁRIO E GRUPO ===
def fora_do_horario():
    agora = datetime.now()
    dia_semana = agora.strftime("%A").lower()
    return dia_semana not in DIAS_UTEIS or not (HORARIO_INICIO <= agora.hour < HORARIO_FIM)

def mensagem_é_para_grupo(nome_remetente):
    return any(g in nome_remetente.lower() for g in GRUPOS_BLOQUEADOS)

def contato_excluido(nome):
    return any(p in nome.lower() for p in CONTATOS_PESSOAIS)

# === ROTA PRINCIPAL DE RECEBIMENTO ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    # Verificação de token via URL
    if token != os.getenv("WEBHOOK_URL_TOKEN"):
        return jsonify({"erro": "Token inválido na URL."}), 403

    # Verificação de headers
    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")
    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    try:
        mensagem = data.get("message", "").strip().lower()
        numero = data.get("phone", "")
        nome = data.get("name", "")

        print(f"[{datetime.now()}] 📥 Mensagem recebida de {numero} ({nome}): {mensagem}")

        if mensagem_é_para_grupo(nome) or contato_excluido(nome):
            print("❌ Ignorado (grupo ou contato pessoal).")
            return jsonify({"status": "ignorado"})

        if fora_do_horario():
            resposta = f"Olá! Nosso atendimento é de segunda a sexta, das 08h às 18h. Assim que possível, retornaremos. Deseja agendar um horário comigo? {LINK_CALENDLY}"
        elif mensagem in PALAVRAS_CHAVE:
            resposta = PALAVRAS_CHAVE[mensagem]
        else:
            resposta = gerar_resposta_gpt(mensagem)

        print(f"📤 Resposta enviada: {resposta}")
        return jsonify({"response": resposta})

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {e}")
        return jsonify({"erro": "Falha no processamento"}), 500

# === GERAR RESPOSTA COM GPT-4 ===
def gerar_resposta_gpt(pergunta):
    prompt = f"""
Você é um assistente jurídico do escritório Teixeira.Brito Advogados, liderado por Dayan, especialista em contratos, sucessões, holding e renegociação de dívidas.

Responda à seguinte solicitação com educação, segurança jurídica, clareza e objetividade, no estilo Dayan.

Pergunta: {pergunta}

Se não for possível concluir com base nas informações fornecidas, oriente o cliente a agendar um atendimento pelo link: {LINK_CALENDLY} ou a falar diretamente no WhatsApp {CONTATO_DIRETO}.
    """

    resposta = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6
    )
    texto = resposta.choices[0].message.content.strip()
    texto += f"\n\n📌 Se preferir, fale direto com Dr. Dayan pelo WhatsApp {CONTATO_DIRETO} ou agende um horário: {LINK_CALENDLY}"
    return texto

# === ROTA DE TESTE ===
@app.route("/")
def home():
    return "Servidor ativo. Integração Z-API + GPT-4 rodando."
