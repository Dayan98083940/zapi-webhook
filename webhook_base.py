from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime
import os
import json
import openai
import requests
from fpdf import FPDF

app = Flask(__name__)
load_dotenv()

ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NUMERO_INSTANCIA = os.getenv("NUMERO_INSTANCIA")

ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"
client = openai.OpenAI(api_key=OPENAI_API_KEY)

respostas_automaticas = []
historico_respostas = []

try:
    with open("blocos_respostas.json", "r", encoding="utf-8") as file:
        respostas_automaticas = json.load(file)
except Exception as e:
    print("Erro ao carregar blocos_respostas.json:", e)

def detectar_assunto(msg):
    termos = ["holding", "contrato", "divórcio", "herança", "inventário", "processo",
              "renegociação", "dívida", "judicial", "empresa", "consulta", "advogado", "atendimento", "usucapião"]
    msg = msg.lower()
    return "profissional" if any(t in msg for t in termos) else "particular"

def pronome_tratamento(nome):
    nome = nome.lower()
    if any(p in nome for p in ["dr", "doutor", "advogado", "dra", "advogada"]):
        return "Dr." if "dra" not in nome else "Dra."
    return "Sr." if nome[-1] != "a" else "Sra."

def gerar_resposta(mensagem, nome):
    prompt = f"""
Mensagem recebida de {nome}:
"{mensagem}"

Responda de forma clara, sem termos jurídicos complexos. Use linguagem humanizada.
Caso não compreenda totalmente a dúvida, peça mais informações.
Sempre ofereça a opção de agendamento ou ligação com Dr. Dayan.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é assistente jurídico com linguagem empática e acessível, representando Dr. Dayan, advogado especialista em direito civil."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Erro ao gerar resposta GPT:", str(e))
        return "Tive uma dificuldade para interpretar sua mensagem. Pode explicar com um pouco mais de detalhes, por favor?"

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
        print("Erro ao enviar pela Z-API:", str(e))

def gerar_pdf_relatorio():
    if not historico_respostas:
        return

    hoje = datetime.now().strftime("%d/%m/%Y")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_title("Relatório Diário")

    pdf.cell(0, 10, f"Relatório Diário - {hoje}", ln=True, align="C")
    pdf.ln(10)

    for item in historico_respostas:
        pdf.multi_cell(0, 10, f"{item['nome']} ({item['telefone']}) - Assunto: {item['assunto']}")
        pdf.ln(1)

    filename = "relatorio_dia.pdf"
    pdf.output(filename)

    enviar_zapi(NUMERO_INSTANCIA, "📄 Seu relatório diário está pronto.")
    with open(filename, "rb") as file:
        requests.post(
            f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-file",
            headers={"Client-Token": ZAPI_TOKEN},
            files={"file": file},
            data={"phone": NUMERO_INSTANCIA, "filename": "Relatório_Diário.pdf"}
        )

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "online", "message": "Webhook jurídico ativo"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json or {}
        mensagem = data.get("text", {}).get("message", "") \
            or data.get("text", {}).get("body", "") \
            or data.get("image", {}).get("caption", "") \
            or data.get("document", {}).get("caption", "") \
            or ""

        if not mensagem:
            return jsonify({"response": None})

        is_group = data.get("isGroup", False)
        telefone = data.get("participantPhone") if is_group else data.get("senderPhone") or data.get("phone", "")
        nome = data.get("senderName", "Contato")
        grupo = data.get("groupName", "")

        if telefone == NUMERO_INSTANCIA:
            return jsonify({"response": None})

        if is_group and NUMERO_INSTANCIA not in mensagem:
            print("Grupo sem menção direta, ignorado.")
            return jsonify({"response": None})

        tipo = detectar_assunto(mensagem)

        if tipo == "profissional":
            resposta = None
            for bloco in respostas_automaticas:
                if any(kw in mensagem.lower() for kw in bloco.get("keywords", [])):
                    resposta = bloco["response"]
                    break

            if not resposta:
                tratamento = pronome_tratamento(nome)
                resposta = gerar_resposta(mensagem, f"{tratamento} {nome}")

            historico_respostas.append({
                "nome": nome,
                "telefone": telefone,
                "assunto": mensagem
            })

            enviar_zapi(telefone, resposta)
            return jsonify({"response": resposta})

        return jsonify({"response": None})
    except Exception as e:
        print("Erro geral:", str(e))
        return jsonify({"error": "Erro interno"}), 500

# 🚀 Agendado externamente por cron job ou script de controle diário
@app.route("/relatorio", methods=["GET"])
def gerar_relatorio():
    gerar_pdf_relatorio()
    return jsonify({"status": "Relatório gerado e enviado via WhatsApp"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
