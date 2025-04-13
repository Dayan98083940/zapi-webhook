from flask import Flask, request, jsonify
import os
import json
import requests
import re
from datetime import datetime, timedelta

app = Flask(__name__)

# === VARIÁVEIS DE AMBIENTE ===
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN") or os.getenv("TOKEN_DA_INSTANCIA")
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")

# === CONFIGURAÇÕES ===
HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
CONTATO_DIRETO = "+55 62 99808-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# === FUNÇÕES DE APOIO ===
def agora():
    return datetime.now()

def horario_comercial():
    dia = agora().strftime("%A").lower()
    hora = agora().hour
    return dia in DIAS_UTEIS and HORARIO_INICIO <= hora < HORARIO_FIM

import emoji

def remover_emojis(texto):
    return emoji.replace_emoji(texto, replace='')

def limpar_texto(texto):
    texto = remover_emojis(texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def enviar_para_whatsapp(numero, mensagem):
    if not numero:
        print("⚠️ Número vazio. Mensagem não enviada.")
        return
    try:
        headers = {
            "Content-Type": "application/json",
            "Client-Token": EXPECTED_CLIENT_TOKEN  # REINSERIDO AQUI
        }

        texto_limpo = limpar_texto(str(mensagem))

        payload = {
            "phone": numero.strip(),
            "message": texto_limpo
        }
        payload = {k: v for k, v in payload.items() if v}

        print("📦 Payload a ser enviado para Z-API:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Mensagem enviada para {numero}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")

def formatar_resposta(texto_base, assunto="geral"):
    assinatura = (
        "\n\nCaso precise de mais informações, agende um horário comigo ou entre em contato:"
        "\nAgendamento: https://calendly.com/dayan-advgoias"
        f"\nTelefone: {CONTATO_DIRETO}"
    )
    if "processo" in assunto:
        complemento = "\n\nSe possível, informe o número do atendimento ou processo. Podemos também agendar uma reunião presencial ou virtual para tratar os detalhes."
    else:
        complemento = "\n\nPosso te auxiliar em mais alguma demanda?"

    return texto_base + assinatura + complemento

# === ROTA PRINCIPAL ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def webhook_receive(token):
    if token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Token inválido na URL do /receive"}), 403

    data = request.json or {}
    print("📩 Mensagem recebida da Z-API:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return jsonify({"status": "received"})

@app.route("/webhook", methods=["POST"])
def webhook():
    token = request.headers.get("Client-Token") or request.args.get("token")
    if not token or token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Token inválido ou ausente."}), 403

    data = request.json or {}
    mensagem = data.get("message", "").lower()
    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    numero = data.get("sender") or data.get("chatId", "").split("@")[0]

    print("Dados recebidos:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if "inventário" in mensagem:
        resposta = formatar_resposta("Você deseja abrir um inventário judicial ou extrajudicial? Posso orientá-lo quanto aos documentos necessários e ao procedimento.", "inventário")
    elif "processo" in mensagem:
        resposta = formatar_resposta("Em relação ao processo, posso ajudar com análise, acompanhamento ou defesa, conforme o caso.", "processo")
    elif "contrato" in mensagem:
        resposta = formatar_resposta("Certo. Qual é o tipo de contrato que você precisa elaborar ou revisar?", "contrato")
    elif not horario_comercial():
        resposta = formatar_resposta("Olá. No momento estamos fora do horário de atendimento (segunda a sexta, das 8h às 18h).", "fora_horario")
    else:
        resposta = formatar_resposta("Recebido. Por gentileza, forneça mais detalhes para que eu possa atendê-lo da melhor forma.")

    enviar_para_whatsapp(numero, resposta)

    print("Telefone:", numero)
    print("Mensagem recebida:", mensagem)
    print("Resposta enviada:", resposta)

    return jsonify({"response": resposta})

# === ROTA DE STATUS ===
@app.route("/", methods=["GET"])
def status():
    return jsonify({"status": "online"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Rota não encontrada"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
