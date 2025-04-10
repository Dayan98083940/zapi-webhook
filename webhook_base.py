from flask import Flask, request, jsonify
import requests
import os
import openai
import fitz  # PyMuPDF

app = Flask(__name__)

# Configuração
ZAPI_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1/token/61919ECA32B76ED6ABDAE637/send-text"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "SUA_CHAVE_OPENAI"
openai.api_key = OPENAI_API_KEY

# Envia resposta via Z-API
def enviar_resposta(numero, resposta):
    payload = {
        "phone": numero,
        "message": resposta
    }
    headers = {
        "Content-Type": "application/json"
    }
    requests.post(ZAPI_URL, json=payload, headers=headers)

# Analisa PDF enviado
def analisar_pdf_por_url(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return "Não consegui acessar o documento. Por favor, envie novamente."

        with open("contrato.pdf", "wb") as f:
            f.write(response.content)

        doc = fitz.open("contrato.pdf")
        texto = ""
        for pagina in doc:
            texto += pagina.get_text()
        doc.close()

        if not texto.strip():
            return "O arquivo está em branco ou ilegível. Tente outro documento."

        prompt = (
            "Você é um advogado especialista. Faça uma análise técnica e objetiva do contrato abaixo, "
            "identificando cláusulas abusivas, pontos de atenção, ausência de prazos, obrigações mal definidas, etc. "
            "Fale de forma clara e direta, no estilo Dayan Teixeira.\n\n"
            f"Contrato:\n{texto[:4000]}"
        )

        resposta_ai = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado claro, direto e técnico."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return resposta_ai.choices[0].message["content"]

    except Exception as e:
        return f"Ocorreu um erro na análise: {str(e)}"

# Webhook principal
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        tipo = data.get("type") or data["messages"][0].get("type")
        numero = data.get("phone") or data["messages"][0]["from"].split("@")[0]

        if tipo == "text":
            mensagem = data["messages"][0]["text"]["body"].strip().lower()

            if mensagem in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                resposta = (
                    "Olá! Seja bem-vindo ao Teixeira.Brito Advogados.\n"
                    "Sou o assistente virtual do Dr. Dayan. Posso te ajudar com:\n\n"
                    "1️⃣ Análise de contrato\n"
                    "2️⃣ Análise de processo\n"
                    "3️⃣ Atendimento com advogado\n"
                    "4️⃣ Outro assunto\n\n"
                    "Digite o número da opção desejada."
                )
            elif mensagem == "1" or "contrato" in mensagem:
                resposta = "Perfeito. Envie o contrato em PDF aqui mesmo e farei a análise para você."
            elif mensagem == "2" or "processo" in mensagem:
                resposta = "Envie o número ou arquivo do processo que deseja que eu analise."
            elif mensagem == "3":
                resposta = "📅 Agende seu atendimento com o Dr. Dayan: https://calendly.com/daan-advgoias"
            elif mensagem == "4" or "outro" in mensagem:
                resposta = "Claro. Me explique melhor o que você precisa."
            else:
                resposta = "Recebi sua mensagem. Pode me dar mais detalhes sobre o que precisa?"

            enviar_resposta(numero, resposta)

        elif tipo == "document":
            doc_info = data["messages"][0]["document"]
            mime = doc_info.get("mime_type", "")
            url = doc_info.get("url")

            if mime == "application/pdf":
                resposta = analisar_pdf_por_url(url)
            else:
                resposta = "Atualmente só consigo analisar arquivos em PDF. Por favor, envie nesse formato."

            enviar_resposta(numero, resposta)

        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"erro": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
