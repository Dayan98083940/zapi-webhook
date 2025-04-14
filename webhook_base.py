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
CONTATO_FIXO = "(62) 3922-3940"
CONTATO_BACKUP = "(62) 99981-2069"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

GRUPOS_BLOQUEADOS = ["sagrada família", "providência santa"]
CONTATOS_PESSOAIS = ["pai", "mab", "joão", "pedro", "amor", "érika", "felipe", "helder"]

# === SAUDAÇÃO POR HORÁRIO ===
def gerar_saudacao():
    hora = datetime.now().hour
    if hora < 12:
        return "Bom dia"
    elif 12 <= hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

# === FILTROS ===
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

    # NOVO BLOCO DE VALIDAÇÃO DE HEADERS
    if not client_token or not content_type:
        print("[ERRO] Headers ausentes ou incompletos.")
        return jsonify({"erro": "Headers ausentes."}), 403

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        print(f"[ERRO] Headers inválidos. Token recebido: {client_token}")
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    try:
        mensagem = data.get("message", "").strip()
        numero = data.get("phone", "")
        nome = data.get("name", "")

        print(f"📥 Mensagem recebida de {numero} ({nome}): {mensagem}")

        resposta = gerar_resposta_gpt(mensagem, nome)
        print(f"📤 Resposta enviada: {resposta}")
        return jsonify({"response": resposta})

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {repr(e)}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === GPT-4 COM ESTILO DAYAN ===
def gerar_resposta_gpt(pergunta, nome_cliente):
    saudacao = gerar_saudacao()

    introducao = (
        f"{saudacao}, Sr(a). {nome_cliente}.\n\n"
        "Antes de te orientar com segurança, preciso entender melhor sua situação.\n"
        "📌 Pode me contar, de forma breve, o que está acontecendo ou qual é sua dúvida?\n"
    )

    prompt = f"""
Você é um assistente IA da Teixeira Brito Advogados.

Estilo da resposta:
- Formal, investigativo e direto.
- NÃO EXPLIQUE conceitos jurídicos (ex: não diga o que é holding, como funciona usucapião, etc.), mesmo que o cliente pergunte diretamente.
- Sua função é acolher, investigar e encaminhar o cliente para o atendimento humano.
- Use perguntas curtas e estratégicas para entender a demanda.
- Nunca repita informações ou frases genéricas como “parece que você tem uma dúvida”.
- Responda em no máximo 3 parágrafos objetivos.
- Finalize sempre com:

📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}  
Se não conseguir falar com o Dr. Dayan, entre em contato com o atendimento: {CONTATO_FIXO} ou {CONTATO_BACKUP}

Mensagem recebida do cliente:
{pergunta}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    texto = response.choices[0].message["content"].strip()
    return f"{introducao}\n\n{texto}"

# === ROTA DE STATUS ===
@app.route("/")
def home():
    return "🟢 Integração Whats TB ativa — Estilo Dayan + validação de headers aplicada"
