from flask import Flask, request, jsonify
import requests
import fitz  # PyMuPDF
import openai
import os

app = Flask(__name__)

# === CONFIG ===
ZAPI_INSTANCE_ID = "3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "61919ECA32B76ED6ABDAE637"
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-text"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "SUA_CHAVE_OPENAI"
openai.api_key = OPENAI_API_KEY


def enviar_resposta(numero, resposta):
    payload = {
        "phone": numero,
        "message": resposta
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN  # CORREÇÃO AQUI
    }

    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"\n📣 [ENVIAR] Para: {numero}")
        print(f"📝 Mensagem: {resposta}")
        print("🔁 Status Z-API:", r.status_code)
        print("📩 Retorno Z-API:", r.text)
    except Exception as e:
        print("❌ Erro ao enviar resposta:", str(e))


def analisar_pdf_por_url(url):
    try:
        res = requests.get(url)
        if res.status_code != 200:
            return "Não consegui acessar o documento. Por favor, envie novamente."

        with open("contrato.pdf", "wb") as f:
            f.write(res.content)

        doc = fitz.open("contrato.pdf")
        texto = "".join(page.get_text() for page in doc)
        doc.close()

        if not texto.strip():
            return "O contrato está em branco ou ilegível. Tente enviar outro arquivo."

        prompt = (
            "Você é um advogado técnico e direto. Analise o conteúdo abaixo e gere um resumo jurídico no estilo Dayan Teixeira. "
            "Destaque cláusulas críticas, riscos contratuais e orientações claras para o cliente.\n\n"
            f"{texto[:4000]}"
        )

        resposta_ai = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado técnico e objetivo."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return resposta_ai.choices[0].message["content"]

    except Exception as e:
        return f"Erro ao analisar o contrato: {str(e)}"


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("🔍 JSON recebido:", data)

        if not data or "type" not in data:
            return jsonify({"erro": "Payload malformado"})

        tipo = data.get("type")
        numero = data.get("phone")

        if not numero:
            return jsonify({"erro": "Número não encontrado"})

        if tipo == "text":
            texto = data.get("text", {}).get("message", "").strip().lower()

            if texto in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                resposta = (
                    "Olá! Sou o assistente virtual do Dr. Dayan.\n"
                    "Posso te ajudar com:\n\n"
                    "1️⃣ Análise de contrato\n"
                    "2️⃣ Análise de processo\n"
                    "3️⃣ Falar com advogado\n"
                    "4️⃣ Outro assunto\n\n"
                    "Digite o número da opção desejada."
                )
            elif texto == "1" or "contrato" in texto:
                resposta = "Perfeito. Envie o contrato em PDF aqui mesmo e farei uma análise técnica e objetiva."
            elif texto == "2" or "processo" in texto:
                resposta = "Certo. Envie o número ou o arquivo do processo que deseja que eu avalie."
            elif texto == "3":
                resposta = "📅 Para agendar um atendimento com Dr. Dayan, acesse:\nhttps://calendly.com/daan-advgoias"
            elif texto == "4" or "outro" in texto:
                resposta = "Compreendido. Me diga com clareza o que você precisa para que eu possa te orientar da melhor forma."
            else:
                resposta = "Recebi sua mensagem. Pode detalhar melhor o que você deseja resolver?"

            enviar_resposta(numero, resposta)

        elif tipo == "document":
            doc = data.get("document", {})
            mime = doc.get("mime_type", "")
            url = doc.get("documentUrl")

            if mime == "application/pdf":
                resposta = analisar_pdf_por_url(url)
            else:
                resposta = "Por enquanto, só consigo analisar arquivos em PDF. Por favor, envie nesse formato."

            enviar_resposta(numero, resposta)

        else:
            enviar_resposta(numero, "Recebi sua mensagem, mas ainda não consigo interpretar esse conteúdo.\nTente enviar um texto ou contrato em PDF. Ficarei feliz em ajudar.")

        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ Erro geral:", str(e))
        return jsonify({"erro": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
