from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import json
import openai
import requests

app = Flask(__name__)
load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")  # Ex: 5562998083940

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ✅ Não bloquear ninguém por padrão
bloqueados = []
grupos_bloqueados = []

# ✅ Carrega os blocos de respostas automáticas
try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as file:
        blocos = json.load(file)
except Exception as e:
    print("❌ Erro ao carregar respostas:", str(e))
    blocos = []

def detectar_assunto(mensagem):
    termos = [
        "contrato", "holding", "divórcio", "herança", "inventário", "processo",
        "consulta", "renegociação", "empresa", "advogado", "atendimento", "usucapião"
    ]
    mensagem = mensagem.lower()
    return "profissional" if any(p in mensagem for p in termos) else "particular"

def buscar_bloco(mensagem):
    msg = mensagem.lower()
    for bloco in blocos:
        if any(keyword in msg for keyword in bloco.get("keywords", [])):
            return bloco["response"]
    return None

def gerar_resposta_gpt(mensagem):
    prompt = f"""
Você é o Dr. Dayan, advogado do escritório Teixeira.Brito Advogados.

Mensagem recebida:
"{mensagem}"

Responda com clareza, empatia e profissionalismo, sem jargões jurídicos. Se não compreender a dúvida, peça mais detalhes e ofereça a opção de agendamento de uma ligação ou consulta.
    """
    try:
        resposta = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é o Dr. Dayan, especialista em direito civil e empresarial."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350,
            temperature=0.4
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("❌ GPT erro:", e)
        return None

def enviar_mensagem_whatsapp(numero, texto):
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    payload = {
        "phone": numero,
        "message": texto
    }
    try:
        resposta = requests.post(ZAPI_URL, headers=headers, json=payload)
        print(f"✅ Enviado para {numero} | Status: {resposta.status_code} | Resposta: {resposta.text}")
    except Exception as e:
        print("❌ Falha ao enviar mensagem:", e)

@app.route("/", methods=["GET"])
def healthcheck():
    return jsonify({"status": "online", "mensagem": "Webhook jurídico ativo"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json or {}
        mensagem = (
            data.get("message") or
            data.get("text", {}).get("body") or
            data.get("image", {}).get("caption") or
            data.get("document", {}).get("caption") or
            ""
        ).strip()

        if not mensagem:
            return jsonify({"response": None})

        is_group = data.get("isGroup", False)
        telefone = data.get("participantPhone") if is_group else data.get("senderPhone", "")
        nome = data.get("senderName", "")
        grupo = data.get("groupName", "")

        if not telefone or telefone == NUMERO_INSTANCIA:
            return jsonify({"response": None})

        # ✅ Libera todos os contatos e grupos, mas valida a menção no grupo
        if is_group and NUMERO_INSTANCIA not in mensagem:
            print("👥 Ignorado (grupo sem menção ao número)")
            return jsonify({"response": None})

        assunto = detectar_assunto(mensagem)
        if assunto == "profissional":
            resposta = buscar_bloco(mensagem) or gerar_resposta_gpt(mensagem)
            if resposta:
                enviar_mensagem_whatsapp(telefone, resposta)
                return jsonify({"response": resposta})

        return jsonify({"response": None})
    except Exception as e:
        print("❌ Erro no webhook:", e)
        return jsonify({"error": "Erro interno"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
