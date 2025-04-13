from flask import Flask, request, jsonify
import os
import json
import requests
import re
import emoji
import openai
from datetime import datetime, timedelta

app = Flask(__name__)

# === VARIÁVEIS DE AMBIENTE ===
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN") or "F124e80fa9ba94101a6eb723b5a20d2b3S"
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

def remover_emojis(texto):
    return emoji.replace_emoji(texto, replace='')

def limpar_texto(texto):
    texto = remover_emojis(texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def autenticar_requisicao(token_url):
    token_header = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")

    if token_url != EXPECTED_CLIENT_TOKEN:
        return False, "Token inválido na URL"
    if token_header != EXPECTED_CLIENT_TOKEN:
        return False, "Client-Token ausente ou incorreto no header"
    if content_type != "application/json":
        return False, "Content-Type inválido"
    return True, ""

def enviar_para_whatsapp(numero, mensagem):
    if not numero:
        print("⚠️ Número vazio. Mensagem não enviada.")
        return
    try:
        headers = {
            "Content-Type": "application/json",
            "Client-Token": EXPECTED_CLIENT_TOKEN
        }

        print(f"📡 Enviando com headers: {headers}")

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
        "\n\nSe precisar de mais informações, agende um horário ou entre em contato diretamente:"
        "\nAgendamento: https://calendly.com/dayan-advgoias"
        f"\nTelefone: {CONTATO_DIRETO}"
    )
    if "processo" in assunto:
        complemento = "\n\nPor gentileza, informe o número do processo ou atendimento. Se preferir, podemos agendar uma reunião presencial ou virtual para tratar os detalhes."
    elif "genérica" in assunto:
        complemento = "\n\nSua solicitação está um pouco genérica. Encaminharei para atendimento direto ou podemos agendar um horário para entender melhor."
    else:
        complemento = "\n\nHá mais alguma informação que possa me fornecer para te ajudar com precisão?"

    return texto_base + assinatura + complemento

def gerar_resposta_gpt(mensagem, nome):
    prompt = f"""
Você é um assistente jurídico representando o advogado Dr. Dayan.

Seu papel é iniciar o atendimento com abordagem formal, técnica e objetiva, e qualificar a solicitação.

Sempre encerre com proposta de agendamento ou contato direto com o Dr. Dayan.

Mensagem recebida:
\"{mensagem}\"
Remetente: {nome}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=400
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro ao gerar resposta com GPT-4: {e}")
        return "Recebemos sua mensagem. Podemos conversar por atendimento direto ou agendar um horário."

# === ROTA PRINCIPAL ===
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

    print("🧩 DADOS RECEBIDOS:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if "inventário" in mensagem:
        resposta = formatar_resposta("Você está buscando abrir um inventário? Podemos definir se será judicial ou extrajudicial, conforme o caso.", "inventário")
    elif "processo" in mensagem:
        resposta = formatar_resposta("Posso te ajudar com a situação do processo. Você sabe o número ou assunto envolvido?", "processo")
    elif "contrato" in mensagem:
        resposta = formatar_resposta("Você deseja elaborar, revisar ou rescindir um contrato? Me envie mais detalhes para que eu entenda melhor.", "contrato")
    elif not horario_comercial():
        resposta = formatar_resposta("Olá. No momento estamos fora do horário de atendimento (segunda a sexta, das 8h às 18h).", "fora_horario")
    else:
        resposta = gerar_resposta_gpt(mensagem, nome)

    enviar_para_whatsapp(numero, resposta)

    print("📞 Telefone:", numero)
    print("📨 Mensagem recebida:", mensagem)
    print("✅ Resposta enviada:", resposta)

    return jsonify({"response": resposta})

# === ROTAS AUTENTICADAS PARA Z-API ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def webhook_receive(token):
    autorizado, erro = autenticar_requisicao(token)
    if not autorizado:
        return jsonify({"error": erro}), 403

    data = request.json or {}
    print("📩 Mensagem recebida da Z-API:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return jsonify({"status": "received"})

@app.route("/webhook/<token>/send", methods=["POST"])
def webhook_send(token):
    autorizado, erro = autenticar_requisicao(token)
    if not autorizado:
        return jsonify({"error": erro}), 403

    data = request.json or {}
    print("📤 Status de envio recebido da Z-API:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return jsonify({"status": "acknowledged"})

@app.route("/", methods=["GET"])
def status():
    return jsonify({"status": "online"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Rota não encontrada"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
