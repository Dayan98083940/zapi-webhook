from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime

app = Flask(__name__)

# === CONFIGURAÇÕES GERAIS ===
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")  # Ex: F124e80fa9ba94101a6eb723b5a20d2b3S
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")  # Ex: 6148D6FDA5C0D66E63947D5B

HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["segunda", "terça", "quarta", "quinta", "sexta"]

# === CONTATOS A IGNORAR ===
CONTATOS_PESSOAIS = ["pai", "mab", "joão", "pedro", "amor", "érika", "helder", "felipe"]
GRUPOS_BLOQUEADOS = ["sagrada família", "providência santa"]

# === DADOS DE CONTATO ===
CONTATO_DIRETO = "(62) 99981-2069"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"
ARQUIVO_CONTROLE = "controle_interacoes.json"

# === PALAVRAS-CHAVE ===
PALAVRAS_CHAVE = {
    "inventário": "Para inventário, podemos dar andamento de forma rápida. Posso te enviar a lista de documentos?",
    "contrato": "Qual contrato você deseja elaborar? Informe o tipo de negócio jurídico para que possamos estruturar com segurança.",
    "divórcio": "Se for consensual, conseguimos resolver de forma rápida. Se for litigioso, podemos analisar o caso com urgência. Deseja marcar um horário?",
    "renegociação de dívidas": "Trabalhamos com renegociação de dívidas bancárias e empresariais. Me diga um pouco sobre sua situação.",
    "atraso de obra": "Você está com problema em obra atrasada? Podemos verificar se há fundamento para restituição ou ação por descumprimento.",
    "leilão": "Você deseja participar de um leilão ou evitar um? Atendemos ambos os casos com segurança jurídica.",
    "holding": "Se deseja estruturar uma holding familiar ou rural, podemos fazer isso com planejamento patrimonial. Quer marcar um diagnóstico?"
}

# === FUNÇÕES AUXILIARES ===
def carregar_controle():
    if os.path.exists(ARQUIVO_CONTROLE):
        with open(ARQUIVO_CONTROLE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_controle(controle):
    with open(ARQUIVO_CONTROLE, "w", encoding="utf-8") as f:
        json.dump(controle, f, indent=2, ensure_ascii=False)

controle = carregar_controle()

def fora_do_horario():
    agora = datetime.now()
    dia_semana = agora.strftime("%A").lower()
    return dia_semana not in DIAS_UTEIS or not (HORARIO_INICIO <= agora.hour < HORARIO_FIM)

def mensagem_é_para_grupo(nome_remetente):
    return any(g in nome_remetente.lower() for g in GRUPOS_BLOQUEADOS)

def contato_excluido(nome):
    return any(p in nome.lower() for p in CONTATOS_PESSOAIS)

# === WEBHOOK DE RECEBIMENTO ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_TOKEN:
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    try:
        mensagem = data.get("message", "").strip().lower()
        numero = data.get("phone", "")
        nome = data.get("name", "")

        print(f"\n[{datetime.now()}] 📥 Mensagem de {numero} ({nome}): {mensagem}")

        if mensagem_é_para_grupo(nome) or contato_excluido(nome):
            print("❌ Ignorado (grupo ou contato pessoal).")
            return jsonify({"status": "ignorado"})

# Verifica se está fora do horário E a mensagem não contém o código de teste
if "teste-dayan" not in mensagem and fora_do_horario():
    resposta = f"Olá! Nosso atendimento é de segunda a sexta, das 08h às 18h. Deseja agendar um horário? {LINK_CALENDLY}"
elif mensagem in PALAVRAS_CHAVE:
    resposta = PALAVRAS_CHAVE[mensagem]
else:
    resposta = gerar_resposta_gpt(mensagem)


        print(f"📤 Resposta enviada: {resposta}")
        return jsonify({"response": resposta})

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {e}")
        return jsonify({"erro": "Erro interno"}), 500

# === GPT-4 PARA RESPOSTAS LIVRES ===
def gerar_resposta_gpt(pergunta):
    prompt = f"""
Você é assistente jurídico do escritório Teixeira.Brito Advogados, liderado por Dayan, especialista em contratos, sucessões, holding e renegociação de dívidas.

Responda com educação, clareza, objetividade e segurança jurídica no estilo Dayan.

Pergunta: {pergunta}

Se não for possível responder com segurança, oriente o cliente a agendar atendimento pelo link: {LINK_CALENDLY} ou falar direto no WhatsApp {CONTATO_DIRETO}.
"""

    resposta = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    texto = resposta.choices[0].message.content.strip()
    texto += f"\n\n📌 Se preferir, fale direto com Dr. Dayan: {CONTATO_DIRETO} ou agende aqui: {LINK_CALENDLY}"
    return texto

# === ROTA DE TESTE ===
@app.route("/")
def home():
    return "🟢 Servidor está rodando com GPT-4 + Z-API"
