from flask import Flask, request, jsonify
import os
import json
import openai
import requests
from datetime import datetime

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")
EXPECTED_CLIENT_TOKEN = "F124e80fa9ba94101a6eb723b5a20d2b3S"

# === CONTATOS ===
CONTATO_DIRETO = "+55(62)99808-3940"
CONTATO_FIXO = "(62) 3922-3940"
CONTATO_BACKUP = "(62) 99981-2069"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# === Z-API ===
ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"

# === BLOQUEIOS E HISTÓRICO ===
BLOQUEAR_NUMEROS = os.getenv("BLOQUEADOS", "").split(",")
CONVERSAS = {}

# === FUNÇÕES AUXILIARES ===
def gerar_saudacao():
    hora = datetime.now().hour
    if hora < 12:
        return "Bom dia"
    elif hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

# === ROTAS PRINCIPAIS ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        print("[ERRO] Token inválido na URL.")
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")

    if not client_token:
        print("[AVISO] Token ausente — assumindo origem Z-API.")
        client_token = EXPECTED_CLIENT_TOKEN

    if not content_type:
        return jsonify({"erro": "Headers ausentes."}), 403

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        print(f"[ERRO] Headers inválidos. Token recebido: {client_token}")
        return jsonify({"erro": "Headers inválidos."}), 403

    try:
        data = request.json
        mensagem = data.get("message", "").strip()
        numero = data.get("phone", "").strip()
        nome = data.get("name", "") or "Cliente"

        print(f"📥 Mensagem recebida de {numero} ({nome}): {mensagem}")

        if numero in BLOQUEAR_NUMEROS:
            print(f"⛔ Número bloqueado: {numero}")
            return jsonify({"status": "bloqueado", "mensagem": "Número ignorado pelo sistema."})

        resposta = gerar_resposta_gpt(mensagem, nome)
        print(f"📤 Resposta gerada: {resposta}")

        if numero not in CONVERSAS:
            CONVERSAS[numero] = []
        CONVERSAS[numero].append(f"Cliente: {mensagem}")
        CONVERSAS[numero].append(f"Assistente: {resposta}")

        enviar_resposta_via_zapi(numero, resposta, mensagem_original=mensagem)
        return jsonify({"status": "ok", "enviado_para": numero})

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {repr(e)}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === ENVIO CONDICIONAL PARA GRUPOS E INDIVIDUAL ===
def enviar_resposta_via_zapi(telefone, mensagem, mensagem_original=""):
    headers = {"Content-Type": "application/json"}

    if "-group" in telefone:
        if "dayan" in mensagem_original.lower():
            resposta_grupo = (
                "Olá! Para assuntos jurídicos, por favor, me chame no privado para que eu possa te orientar com segurança. 📲"
            )
            payload = {"phone": telefone, "message": resposta_grupo}
            url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
            try:
                response = requests.post(url, json=payload, headers=headers)
                print(f"📤 Mensagem enviada para grupo {telefone}.")
                print(f"🧾 Resposta da Z-API: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Erro ao responder grupo: {repr(e)}")
        else:
            print(f"👥 Grupo detectado, sem menção a Dayan — ignorando.")
        return

    if not telefone or not mensagem.strip():
        print(f"⛔ Ignorado: número inválido ou mensagem vazia → {telefone}")
        return

    payload = {"phone": telefone, "message": mensagem}
    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Mensagem enviada para {telefone} via Z-API.")
        print(f"🧾 Resposta da Z-API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar via Z-API: {repr(e)}")

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
- Nunca repita informações ou frases genéricas como "parece que você tem uma dúvida".
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

# === CONSULTA HISTÓRICO ===
@app.route("/conversas/<numero>", methods=["GET"])
def mostrar_conversa(numero):
    return jsonify(CONVERSAS.get(numero, ["Sem histórico para este número."]))

@app.route("/")
def home():
    return "🟢 Whats TB rodando com Estilo Dayan, controle de grupos e Z-API"
