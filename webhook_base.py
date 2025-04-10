from flask import Flask, request, jsonify
import requests
import fitz  # PyMuPDF
import openai
import os

app = Flask(__name__)

# === CONFIGURAÇÃO ===
ZAPI_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1/token/61919ECA32B76ED6ABDAE637/send-text"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "SUA_CHAVE_OPENAI_AQUI"
openai.api_key = OPENAI_API_KEY

# === ENVIA RESPOSTA VIA Z-API ===
def enviar_resposta(numero, resposta):
    payload = {
        "phone": numero,
        "message": resposta
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(ZAPI_URL, json=payload, headers=headers)
        print(f"⏩ Respondendo para {numero}:\n{resposta}")
        print("🔁 Retorno da Z-API:", res.status_code, res.text)
    except Exception as e:
        print("❌ Erro ao enviar resposta:", str(e))

# === ANALISA PDF COM OPENAI ===
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
            "Você é um advogado técnico e direto. Analise o conteúdo abaixo e gere um resumo jurídico no estilo Dayan Teixeira: "
            "destaque cláusulas de risco, omissões importantes e oriente o cliente de forma clara.\n\n"
            f"Conteúdo do contrato:\n{texto[:4000]}"
        )

        resposta_ai = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado técnico e direto."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return resposta_ai.choices[0].message["content"]

    except Exception as e:
        return f"Ocorreu um erro na análise do PDF: {str(e)}"

# === WEBHOOK PRINCIPAL ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        msg = data["messages"][0]
        tipo = msg.get("type")
        numero = msg.get("from", "").split("@")[0]

        if tipo == "text":
            texto = msg["text"]["body"].strip().lower()

            if texto in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                resposta = (
                    "Olá! Seja bem-vindo ao Teixeira.Brito Advogados.\n"
                    "Sou o assistente do Dr. Dayan. Posso te ajudar com:\n\n"
                    "1️⃣ Análise de contrato\n"
                    "2️⃣ Análise de processo\n"
                    "3️⃣ Falar com advogado\n"
                    "4️⃣ Outro assunto\n\n"
                    "Digite o número da opção desejada."
                )
            elif texto == "1" or "contrato" in texto:
                resposta = "Perfeito. Envie o contrato em PDF aqui mesmo que farei a análise para você."
            elif texto == "2" or "processo" in texto:
                resposta = "Tudo certo. Me envie o número ou arquivo do processo que deseja que eu analise."
            elif texto == "3":
                resposta = "📅 Para agendar com Dr. Dayan, acesse: https://calendly.com/daan-advgoias"
            elif texto == "4" or "outro" in texto:
                resposta = "Claro. Me explique com clareza o que você precisa para que eu possa te ajudar melhor."
            else:
                resposta = "Recebi sua mensagem. Pode me dar mais detalhes sobre o que você precisa?"

            enviar_resposta(numero, resposta)

        elif tipo == "document":
            doc = msg["document"]
            mime = doc.get("mime_type", "")
            url = doc.get("url")

            if mime == "application/pdf":
                resposta = analisar_pdf_por_url(url)
            else:
                resposta = "No momento só consigo analisar arquivos em PDF. Por favor, envie nesse formato."

            enviar_resposta(numero, resposta)

        else:
            enviar_resposta(numero, "Recebi sua mensagem, mas ainda não consigo processar esse tipo de conteúdo. Envie em texto ou PDF.")

        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ Erro geral:", str(e))
        return jsonify({"erro": str(e)})

# === EXECUÇÃO LOCAL OU RENDER ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
