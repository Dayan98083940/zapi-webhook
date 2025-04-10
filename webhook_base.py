from flask import Flask, request, jsonify
import requests
import os
import fitz  # PyMuPDF
import openai

app = Flask(__name__)

# === CONFIGURAÇÕES ===
ZAPI_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1/token/61919ECA32B76ED6ABDAE637/send-text"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "SUA_CHAVE_OPENAI_AQUI"
openai.api_key = OPENAI_API_KEY

# === FUNÇÃO DE RESPOSTA VIA Z-API ===
def enviar_resposta(numero, resposta):
    payload = {
        "phone": numero,
        "message": resposta
    }
    headers = {
        "Content-Type": "application/json"
    }
    return requests.post(ZAPI_URL, json=payload, headers=headers)

# === FUNÇÃO PARA ANALISAR O PDF ===
def analisar_pdf_por_url(url):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return "Não consegui acessar o documento. Por favor, tente novamente."

        # Salva o arquivo temporariamente
        with open("arquivo_temp.pdf", "wb") as f:
            f.write(response.content)

        # Extrai texto com PyMuPDF
        doc = fitz.open("arquivo_temp.pdf")
        texto = ""
        for page in doc:
            texto += page.get_text()

        doc.close()

        if not texto.strip():
            return "O documento está em branco ou ilegível. Tente enviar outro arquivo."

        # Envia para análise da OpenAI
        prompt = (
            "Você é um advogado especialista. Analise o conteúdo abaixo de forma técnica e objetiva, "
            "identificando pontos críticos, cláusulas incompletas ou abusivas, e resuma os riscos e cuidados necessários "
            "em uma linguagem clara para o cliente. A resposta deve seguir o estilo jurídico de Dayan Teixeira.\n\n"
            f"Conteúdo do contrato:\n{texto[:4000]}"
        )

        resposta_openai = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado claro e técnico."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return resposta_openai.choices[0].message["content"]

    except Exception as e:
        return f"Ocorreu um erro durante a análise: {str(e)}"

# === ROTA PRINCIPAL ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        mensagem = ""
        numero = data["messages"][0]["from"].split("@")[0]
        tipo = data["messages"][0]["type"]

        if tipo == "text":
            mensagem = data["messages"][0]["text"]["body"].strip().lower()

            if mensagem in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                resposta = (
                    "Olá! Seja bem-vindo ao Teixeira.Brito Advogados.\n"
                    "Sou o assistente virtual do Dr. Dayan e posso te ajudar com:\n\n"
                    "1️⃣ Análise de contrato\n"
                    "2️⃣ Análise de processo\n"
                    "3️⃣ Atendimento com advogado\n"
                    "4️⃣ Outro assunto\n\n"
                    "Digite o número da opção desejada para continuarmos."
                )
            elif mensagem == "1" or "contrato" in mensagem:
                resposta = (
                    "Perfeito. Encaminhe o contrato em PDF aqui mesmo, e farei uma análise técnica e objetiva para você."
                )
            elif mensagem == "2" or "processo" in mensagem:
                resposta = (
                    "Tudo certo. Me envie o número ou documento do processo que deseja que eu analise."
                )
            elif mensagem == "3":
                resposta = (
                    "Você pode agendar um horário com o Dr. Dayan pelo link abaixo:\n"
                    "📅 https://calendly.com/daan-advgoias"
                )
            elif mensagem == "4" or "outro" in mensagem:
                resposta = (
                    "Claro. Me diga mais sobre o que você precisa e vamos analisar juntos."
                )
            else:
                resposta = (
                    "Recebi sua mensagem. Pode me explicar com mais clareza o que você precisa?"
                )

            enviar_resposta(numero, resposta)

        elif tipo == "document":
            mime = data["messages"][0]["document"].get("mime_type", "")
            if mime == "application/pdf":
                url_pdf = data["messages"][0]["document"]["url"]
                resposta = analisar_pdf_por_url(url_pdf)
            else:
                resposta = "Por enquanto, consigo analisar apenas arquivos em PDF. Por favor, envie nesse formato."

            enviar_resposta(numero, resposta)

        return jsonify({"status": "ok", "mensagem": mensagem if mensagem else tipo})

    except Exception as e:
        return jsonify({"erro": str(e)})

# === RODAR LOCAL OU NO RENDER ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
