from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests
import re
import emoji
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permitir testes locais com frontend se necessário

# === VARIÁVEIS DE AMBIENTE ===
EXPECTED_TOKEN = os.getenv("CLIENT_TOKEN") or "F124e80fa9ba94101a6eb723b5a20d2b3S"
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID") or "SUA_INSTANCE_ID_AQUI"
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN") or "SEU_ZAPI_TOKEN_AQUI"

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

def saudacao():
    hora = agora().hour
    if hora < 12:
        return "Bom dia"
    elif hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

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
            "Client-Token": ZAPI_TOKEN  # Token vindo da variável de ambiente
        }

        texto_limpo = mensagem.strip()

        payload = {
            "phone": numero.strip(),
            "message": texto_limpo
        }

        payload = {k: v for k, v in payload.items() if v}

        print("📦 Enviando para Z-API:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
        response = requests.post(url, json=payload, headers=headers)

        print(f"📤 Mensagem enviada para {numero}: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")

def resposta_fora_do_expediente():
    return (
        "Obrigado por entrar em contato comigo.\n\n"
        "No momento, eu e toda a equipe estamos fora do expediente, renovando as energias para te atender com excelência no próximo horário disponível.\n\n"
        "Fique tranquilo(a), sua mensagem já foi registrada e será respondida assim que possível.\n\n"
        f"Se preferir, podemos já deixar um horário agendado:\nAgendamento: {LINK_CALENDLY}"
    )

# === ROTA PRINCIPAL ===
@app.route("/webhook", methods=["POST"])
def webhook():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token or token != EXPECTED_TOKEN:
        return jsonify({"error": "Token de autorização inválido."}), 403

    data = request.json or {}

    mensagem = data.get("message", "").lower()
    nome = data.get("senderName", "").strip()
    numero = data.get("sender")
    
    if not numero:
        numero = data.get("chatId", "").split("@")[0]
    else:
        numero = numero.split("@")[0]

    print("🧩 DADOS RECEBIDOS:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"📥 Mensagem: {mensagem}")
    print(f"👤 Nome: {nome}")
    print(f"📱 Número: {numero}")

    # === Regras de Resposta ===
    if not horario_comercial():
        resposta = resposta_fora_do_expediente()
    elif "inventário" in mensagem:
        resposta = f"{saudacao()}, {nome}.\n\nVocê está buscando abrir um inventário? Podemos definir se será judicial ou extrajudicial, conforme o caso."
    elif "processo" in mensagem:
        resposta = f"{saudacao()}, {nome}.\n\nPosso te ajudar com a situação do processo. Você sabe o número ou assunto envolvido?"
    elif "contrato" in mensagem:
        resposta = f"{saudacao()}, {nome}.\n\nVocê deseja elaborar, revisar ou rescindir um contrato? Me envie mais detalhes para que eu entenda melhor."
    else:
        resposta = f"{saudacao()}, {nome}.\n\nRecebi sua mensagem. Poderia me explicar melhor para que eu possa te orientar com precisão?"

    enviar_para_whatsapp(numero, resposta)

    print("✅ Resposta enviada:", resposta)

    return jsonify({"response": resposta})

# === ROTAS DE STATUS E ERROS ===
@app.route("/", methods=["GET"])
def status():
    return jsonify({"status": "online"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Rota não encontrada"}), 404

# === INICIAR SERVIDOR ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 1000)
