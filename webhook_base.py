from flask import Flask, request, jsonify
import os
import json
from datetime import datetime
# import openai  # Comentado para teste sem erro 500

app = Flask(__name__)

# === CONFIGURAÇÕES ===
# openai.api_key = os.getenv("OPENAI_API_KEY")  # Habilite depois do teste
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")

HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["segunda", "terça", "quarta", "quinta", "sexta"]

CONTATOS_PESSOAIS = ["pai", "mab", "joão", "pedro", "amor", "érika", "helder", "felipe"]
GRUPOS_BLOQUEADOS = ["sagrada família", "providência santa"]

CONTATO_DIRETO = "+55(62)99808-3940"
EMAIL_CONTATO = "dayan@advgoias.com.br"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"
ARQUIVO_CONTROLE = "controle_interacoes.json"

PALAVRAS_CHAVE = {
    "inventário": "Para inventário, podemos dar andamento de forma rápida. Posso te enviar a lista de documentos?",
    "contrato": "Qual contrato você deseja elaborar? Informe o tipo de negócio jurídico para que possamos estruturar com segurança.",
    "divórcio": "Se for consensual, conseguimos resolver de forma rápida. Se for litigioso, podemos analisar o caso com urgência. Deseja marcar um horário?",
    "renegociação de dívidas": "Trabalhamos com renegociação de dívidas bancárias e empresariais. Me diga um pouco sobre sua situação.",
    "atraso de obra": "Você está com problema em obra atrasada? Podemos verificar se há fundamento para restituição ou ação por descumprimento.",
    "leilão": "Você deseja participar de um leilão ou evitar um? Atendemos ambos os casos com segurança jurídica.",
    "holding": "Se deseja estruturar uma holding familiar ou rural, podemos fazer isso com planejamento patrimonial. Quer marcar um diagnóstico?"
}

# === FUNÇÕES DE APOIO ===

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

# === WEBHOOK PRINCIPAL ===

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
        nome = data.get("name", "")

        print(f"\n[{datetime.now()}] 📥 Mensagem de {numero} ({nome}): {mensagem}")

        if mensagem_é_para_grupo(nome) or contato_excluido(nome):
            print("❌ Ignorado (grupo ou contato pessoal).")
            return jsonify({"status": "ignorado"})

        if "teste-dayan" not in mensagem and fora_do_horario():
            resposta = f"Olá! Nosso atendimento é de segunda a sexta, das 08h às 18h. Deseja agendar um horário? {LINK_CALENDLY}"
        elif mensagem in PALAVRAS_CHAVE:
            resposta = PALAVRAS_CHAVE[mensagem]
        else:
            resposta = f"✅ Resposta simulada. GPT-4 receberia: '{mensagem}'"

        print(f"📤 Resposta enviada: {resposta}")
        return jsonify({"response": f"{resposta}\n\n📌 Fale com Dr. Dayan: {CONTATO_DIRETO} | 📧 {EMAIL_CONTATO} ou agende: {LINK_CALENDLY}"})

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {repr(e)}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === ROTA DE SAÚDE ===

@app.route("/")
def home():
    return "🟢 Servidor está rodando com GPT-4 + Z-API"
