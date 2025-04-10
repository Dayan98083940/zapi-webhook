from flask import Flask, request, jsonify
import requests
import fitz  # PyMuPDF
import openai
import os

app = Flask(__name__)

# === CONFIGURAÇÃO Z-API E OPENAI ===
ZAPI_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1/token/32EF0706F060E25B5CE884CC/send-text"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "SUA_CHAVE_OPENAI"
openai.api_key = OPENAI_API_KEY

# === ENVIA RESPOSTA ===
def enviar_resposta(numero, resposta):
    print(f"\n📣 [ENVIAR] Para: {numero}")
    print(f"📝 Mensagem: {resposta}")

    payload = {"phone": numero, "message": resposta}
    headers = {"Content-Type": "application/json"}

    try:
        r = requests.post(ZAPI_URL, json=payload, headers=headers)
        print("🔁 Status Z-API:", r.status_code)
        print("📩 Retorno Z-API:", r.text)
    except Exception as e:
        print("❌ Erro ao enviar mensagem:", str(e))

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
            return "O PDF está vazio ou ilegível. Envie outro arquivo."

        prompt = (
            "Você é um advogado técnico, influente e objetivo. Analise o seguinte contrato no estilo Dayan Teixeira: destaque cláusulas críticas, riscos, obrigações desproporcionais, omissões e oriente com clareza e autoridade:\n\n"
            f"{texto[:4000]}"
        )

        resposta_ai = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado cordial, direto, com postura de autoridade."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return resposta_ai.choices[0].message["content"]

    except Exception as e:
        print("❌ Erro ao analisar PDF:", str(e))
        return f"Tivemos um problema ao analisar o arquivo: {str(e)}"

# === WEBHOOK PRINCIPAL ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("🔍 JSON recebido:", data)

        msg = data.get("messages", [{}])[0]
        tipo = msg.get("type", "undefined")
        numero = msg.get("from", "").split("@")[0]

        print(f"📥 Tipo de mensagem: {tipo} | Número: {numero}")

        if tipo == "text":
            texto = msg.get("text", {}).get("body", "").strip().lower()
            print("🧾 Conteúdo:", texto)

            if texto in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                resposta = (
                    "Olá! Seja muito bem-vindo ao Teixeira.Brito Advogados. 🙌\n\n"
                    "Sou o assistente do Dr. Dayan — objetivo, influente e pronto para te orientar.\n\n"
                    "Escolha uma opção:\n"
                    "1️⃣ Análise de contrato\n"
                    "2️⃣ Análise de processo\n"
                    "3️⃣ Falar com o Dr. Dayan\n"
                    "4️⃣ Outro assunto"
                )
            elif texto == "1" or "contrato" in texto:
                resposta = "Perfeito. Envie o contrato em PDF aqui mesmo. Farei uma análise técnica e objetiva."
            elif texto == "2" or "processo" in texto:
                resposta = "Certo. Envie o número ou arquivo do processo. Vamos avaliar juntos."
            elif texto == "3":
                resposta = "📅 Agende com Dr. Dayan aqui: https://calendly.com/daan-advgoias"
            elif texto == "4" or "outro" in texto:
                resposta = "Me diga com clareza o que você precisa. Estou aqui para ajudar com precisão."
            else:
                resposta = "Recebi sua mensagem. Pode me explicar melhor o que você precisa resolver?"

            enviar_resposta(numero, resposta)

        elif tipo == "document":
            doc = msg.get("document", {})
            mime = doc.get("mime_type", "")
            url = doc.get("url")

            if mime == "application/pdf" and url:
                resposta = analisar_pdf_por_url(url)
            else:
                resposta = "Só consigo analisar arquivos PDF. Por favor, envie o contrato nesse formato."

            enviar_resposta(numero, resposta)

        else:
            resposta = (
                "Recebi sua mensagem, mas ainda não consigo interpretar esse conteúdo.\n"
                "Tente enviar um texto ou contrato em PDF. Ficarei feliz em ajudar."
            )
            enviar_resposta(numero, resposta)

        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ Erro geral:", str(e))
        return jsonify({"erro": str(e)})

# === EXECUÇÃO NO RENDER ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
