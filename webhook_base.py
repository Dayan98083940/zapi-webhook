from flask import Flask, request, jsonify
import os
import json
import requests
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

def enviar_para_whatsapp(numero, mensagem):
    if not numero:
        print("⚠️ Número vazio. Mensagem não enviada.")
        return
    try:
        headers = {
            "Content-Type": "application/json"
        }
        # Remove quebras de linha e emojis que possam causar erro
        texto = mensagem.replace("\n", " ").strip()

        payload = {
            "phone": numero.strip(),
            "message": texto
        }

        print("📦 Payload a ser enviado para Z-API:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Mensagem enviada para {numero}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")

def formatar_resposta(texto_base, assunto="geral"):
    assinatura = (
        "\n\nSe precisar de mais informações, você pode agendar um horário comigo ou me ligar:"
        "\n📅 https://calendly.com/dayan-advgoias"
        "\n📞 (62) 99808-3940"
    )
    if "processo" in assunto:
        complemento = "\n\nVocê pode me informar o número do atendimento ou processo? Se preferir, podemos agendar uma conversa presencial ou virtual para tratar com mais detalhes."
    else:
        complemento = "\n\nPosso te ajudar em algo mais?"
    return texto_base + assinatura + complemento

# === ROTA PRINCIPAL ===
@app.route("/webhook", methods=["POST"])
def webhook():
    # Aceita token via header OU via querystring
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
        resposta = formatar_resposta("Você deseja abrir um inventário judicial ou extrajudicial? Posso te orientar sobre os documentos e os passos necessários.", "inventário")
    elif "processo" in mensagem:
        resposta = formatar_resposta("Sobre processos judiciais, posso ajudar com a análise ou acompanhamento do seu caso.", "processo")
    elif "contrato" in mensagem:
        resposta = formatar_resposta("Certo, qual contrato? Fale mais sobre o negócio jurídico que deseja formalizar para que possamos entender melhor sua necessidade.", "contrato")
    elif not horario_comercial():
        resposta = formatar_resposta("Olá, agradeço pelo contato. No momento estamos fora do horário de atendimento (segunda a sexta, das 8h às 18h).", "fora_horario")
    else:
        resposta = formatar_resposta("Recebido. Me conte mais detalhes para que eu possa te ajudar melhor.")

    enviar_para_whatsapp(numero, resposta)

    # === LOG PARA MONITORAMENTO NO RENDER ===
    print("📞 Telefone:", numero)
    print("📨 Mensagem recebida:", mensagem)
    print("✅ Resposta enviada:", resposta)

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
