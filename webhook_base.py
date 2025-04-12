from flask import Flask, request, jsonify
import os
import json
from dotenv import load_dotenv
import openai
import requests
from fpdf import FPDF
from datetime import datetime

app = Flask(__name__)
load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")  # Ex: 5562998083940
NUMERO_RELATORIO = "5562998393940"  # WhatsApp da sua esposa para envio do relatório

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

respostas_automaticas = []
log_diario = []

# === Blocos de respostas ===
try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as file:
        respostas_automaticas = json.load(file)
except Exception as e:
    print("❌ Erro ao carregar blocos_respostas.json:", str(e))

# === Verifica assunto ===
def detectar_assunto(msg):
    termos = ["contrato", "holding", "divórcio", "herança", "inventário",
              "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"]
    msg = msg.lower()
    return "profissional" if any(t in msg for t in termos) else "particular"

# === Verifica resposta direta via bloco ===
def responder_com_bloco(msg):
    for bloco in respostas_automaticas:
        for termo in bloco.get("keywords", []):
            if termo in msg.lower():
                return bloco["response"]
    return None

# === Formata o pronome de tratamento ===
def tratar_contato(nome, telefone):
    nome_lower = nome.lower() if nome else ""
    if any(t in nome_lower for t in ["dr ", "doutor", "advogado"]):
        return f"Dr. {nome}"
    elif any(t in nome_lower for t in ["dra", "doutora", "advogada"]):
        return f"Dra. {nome}"
    elif nome:
        return f"Sr(a). {nome}"
    else:
        return "Olá, tudo bem?"

# === GPT humanizado ===
def gerar_resposta_gpt(mensagem, nome, telefone):
    try:
        saudacao = tratar_contato(nome, telefone)
        prompt = f"""
Mensagem do cliente ({saudacao}):
"{mensagem}"

Responda de forma objetiva, empática e sem juridiquês. Se não entender, peça mais informações.
Convide para agendar uma ligação com o Dr. Dayan, caso necessário.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico humanizado e profissional, representando o escritório Teixeira.Brito."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=350,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Erro GPT:", str(e))
        return None

# === Envio pela Z-API ===
def enviar_zapi(phone, message):
    payload = {"phone": phone, "message": message}
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"✅ Enviado para {phone} | Status: {r.status_code} | Resposta: {r.text}")
    except Exception as e:
        print("❌ Erro Z-API:", str(e))

# === Gerar relatório diário em PDF ===
def gerar_relatorio_pdf():
    if not log_diario:
        return None

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Relatório Diário de Atendimentos", ln=True, align="C")
    pdf.ln(10)

    for i, log in enumerate(log_diario, start=1):
        pdf.multi_cell(0, 10, f"{i}. Nome: {log['nome']}\nTelefone: {log['telefone']}\nMensagem: {log['mensagem']}\n", border=0)
        pdf.ln(2)

    nome_arquivo = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    caminho = f"/tmp/{nome_arquivo}"
    pdf.output(caminho)
    return caminho

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "message": "Webhook jurídico ativo"}), 200

@app.route("/webhook", methods=["POST"])
def responder():
    try:
        data = request.json or {}
        print("📩 JSON recebido:", data)

        mensagem = data.get("message", "").strip() \
            or data.get("text", {}).get("message", "") \
            or data.get("text", {}).get("body", "") \
            or data.get("image", {}).get("caption", "") \
            or data.get("document", {}).get("caption", "") \
            or ""

        if not mensagem:
            return jsonify({"response": None})

        is_group = data.get("isGroup", False)
        telefone = data.get("participantPhone") if is_group else data.get("senderPhone") or data.get("phone", "")
        nome = data.get("senderName", "Contato")
        numero_mencionado = NUMERO_INSTANCIA in mensagem

        if is_group and not numero_mencionado:
            print("👥 Ignorado: grupo sem menção direta ao número.")
            return jsonify({"response": None})

        if telefone == NUMERO_INSTANCIA:
            return jsonify({"response": None})

        tipo = detectar_assunto(mensagem)

        if tipo == "profissional":
            resposta = responder_com_bloco(mensagem) or gerar_resposta_gpt(mensagem, nome, telefone)
            if resposta:
                enviar_zapi(telefone, resposta)
                log_diario.append({
                    "telefone": telefone,
                    "nome": nome,
                    "mensagem": mensagem,
                    "resposta": resposta
                })
                return jsonify({"response": resposta})

        return jsonify({"response": None})

    except Exception as e:
        print("❌ Erro geral:", str(e))
        return jsonify({"error": "Erro interno"}), 500

@app.route("/enviar-relatorio", methods=["GET"])
def enviar_relatorio():
    try:
        caminho = gerar_relatorio_pdf()
        if not caminho:
            return jsonify({"status": "vazio", "mensagem": "Nenhuma interação registrada hoje."})

        with open(caminho, "rb") as f:
            base64_pdf = f.read().encode("base64")

        payload = {
            "phone": NUMERO_RELATORIO,
            "fileName": "relatorio_diario.pdf",
            "base64": base64_pdf,
            "caption": "📄 Relatório diário de atendimentos jurídicos."
        }

        headers = {
            "Content-Type": "application/json",
            "Client-Token": ZAPI_TOKEN
        }

        r = requests.post(f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-file-base64", json=payload, headers=headers)
        print("📤 Relatório enviado", r.status_code, r.text)
        return jsonify({"status": "ok", "envio": True})

    except Exception as e:
        print("❌ Erro ao enviar relatório:", str(e))
        return jsonify({"error": "Falha ao enviar relatório"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
