from flask import Flask, request, jsonify
import requests
import fitz  # PyMuPDF
import openai
import os

app = Flask(__name__)

# === CONFIGURAÇÕES ===
ZAPI_INSTANCE_ID = "3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "32EF0706F060E25B5CE884CC"
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
OPENAI_KEY = os.getenv("OPENAI_API_KEY") or "SUA_CHAVE_OPENAI"
openai.api_key = OPENAI_KEY

# === FUNÇÃO: Enviar resposta via Z-API ===
def enviar_resposta(numero, resposta):
    payload = {
        "phone": numero,
        "message": resposta
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }
    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"\n[ENVIANDO] Para: {numero}")
        print("Mensagem:", resposta)
        print("Status Z-API:", r.status_code)
        print("Retorno Z-API:", r.text)
    except Exception as e:
        print("Erro ao enviar resposta:", str(e))

# === FUNÇÃO: Analisar PDF por URL ===
def analisar_pdf_por_url(url):
    try:
        res = requests.get(url)
        if res.status_code != 200:
            return "Não consegui acessar o documento. Por favor, envie novamente."

        with open("documento.pdf", "wb") as f:
            f.write(res.content)

        doc = fitz.open("documento.pdf")
        texto = "".join(page.get_text() for page in doc)
        doc.close()

        if not texto.strip():
            return "O documento está em branco ou ilegível."

        prompt = (
            "Você é um advogado técnico e direto. Analise o conteúdo abaixo e gere um resumo jurídico no estilo Dayan Teixeira. "
            "Destaque cláusulas críticas, riscos e orientações para o cliente.\n\n"
            f"{texto[:4000]}"
        )

        resposta_ai = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado objetivo, técnico e experiente."},
                {"role": "user", "content": prompt}
            ]
        )

        return resposta_ai.choices[0].message["content"]

    except Exception as e:
        return f"Erro ao analisar o contrato: {str(e)}"

# === ROTA DO WEBHOOK ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        msg = data.get("messages", [{}])[0]
        tipo = msg.get("type")
        numero = msg.get("from", "").split("@")[0]

        print("\nJSON recebido:", data)

        if tipo == "text":
            texto = msg.get("text", {}).get("body", "").strip().lower()

            if texto in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                resposta = (
                    "Olá! Sou o assistente virtual do Dr. Dayan da Teixeira.Brito Advogados. Posso te ajudar com:\n\n"
                    "1 - Análise de contrato\n2 - Análise de processo\n3 - Falar com advogado\n4 - Outro assunto\n\nDigite o número da opção desejada."
                )
            elif texto == "1" or "contrato" in texto:
                resposta = "Perfeito. Envie o contrato em PDF e farei a análise técnica."
            elif texto == "2" or "processo" in texto:
                resposta = "Certo. Envie o número ou o arquivo do processo."
            elif texto == "3":
                resposta = "Para agendar com Dr. Dayan, acesse: https://calendly.com/daan-advgoias"
            elif texto == "4" or "outro" in texto:
                resposta = "Ok. Me diga com clareza o que você precisa."
            else:
                resposta = "Não entendi. Pode detalhar melhor o que você deseja resolver?"

            enviar_resposta(numero, resposta)

        elif tipo == "document":
            doc = msg.get("document", {})
            mime = doc.get("mime_type", "")
            url = doc.get("url", "")

            if mime == "application/pdf":
                resposta = analisar_pdf_por_url(url)
            else:
                resposta = "Por enquanto, aceito apenas arquivos em PDF."

            enviar_resposta(numero, resposta)

        else:
            resposta = "Recebi sua mensagem, mas ainda não consigo interpretar esse tipo de conteúdo. Envie um texto ou PDF."
            enviar_resposta(numero, resposta)

        return jsonify({"status": "ok"})

    except Exception as e:
        print("Erro geral:", str(e))
        return jsonify({"erro": str(e)})

# === EXECUÇÃO DO SERVIDOR ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
