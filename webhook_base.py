from flask import Flask, request, jsonify
import requests
import fitz
import openai
import os

app = Flask(__name__)

# === CONFIGURAÇÃO ===
ZAPI_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1/token/61919ECA32B76ED6ABDAE637/send-text"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "SUA_CHAVE_OPENAI"
openai.api_key = OPENAI_API_KEY

# === ENVIA MENSAGEM VIA Z-API ===
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
        print("❌ Falha ao enviar para Z-API:", str(e))

# === ANALISA CONTRATO PDF ===
def analisar_pdf_por_url(url):
    try:
        res = requests.get(url)
        if res.status_code != 200:
            return "Não consegui acessar o documento. Verifique o envio e tente novamente."

        with open("contrato.pdf", "wb") as f:
            f.write(res.content)

        doc = fitz.open("contrato.pdf")
        texto = "".join(page.get_text() for page in doc)
        doc.close()

        if not texto.strip():
            return "Recebi o PDF, mas ele está em branco ou ilegível. Por gentileza, reenvie um arquivo válido."

        prompt = (
            "Você é um advogado com postura de autoridade, técnico, educado e cordial. "
            "Analise o contrato abaixo e gere uma resposta humanizada no estilo de Dayan Teixeira, influente e executor. "
            "A resposta deve ser clara, objetiva, com destaque para riscos, omissões, cláusulas de atenção e orientação ao cliente.\n\n"
            f"{texto[:4000]}"
        )

        resposta_ai = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um advogado influente, educado e assertivo."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return resposta_ai.choices[0].message["content"]

    except Exception as e:
        print("❌ Erro ao analisar PDF:", str(e))
        return "Tive um problema ao ler o documento. Se puder, envie novamente ou me avise que posso orientar de outra forma."

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
            print("🧾 Conteúdo do texto:", texto)

            if texto in ["oi", "olá", "bom dia", "boa tarde", "boa noite"]:
                resposta = (
                    "Olá! Seja muito bem-vindo ao Teixeira.Brito Advogados. 🙌\n\n"
                    "Sou o assistente pessoal do Dr. Dayan — advogado influente, objetivo e comprometido com soluções reais.\n\n"
                    "📌 Como posso te ajudar hoje?\n"
                    "1️⃣ Análise de contrato\n"
                    "2️⃣ Análise de processo\n"
                    "3️⃣ Atendimento com o Dr. Dayan\n"
                    "4️⃣ Outro assunto\n\n"
                    "Digite o número da opção desejada. Estou aqui para te orientar com clareza."
                )
            elif texto == "1" or "contrato" in texto:
                resposta = (
                    "Perfeito. Pode enviar o contrato em PDF aqui mesmo.\n"
                    "Farei uma análise técnica, objetiva e personalizada para você."
                )
            elif texto == "2" or "processo" in texto:
                resposta = (
                    "Certo. Envie o número ou o arquivo do processo.\n"
                    "Vou avaliar com cuidado e te devolver uma análise clara sobre os próximos passos."
                )
            elif texto == "3":
                resposta = (
                    "📅 Para falar com o Dr. Dayan, acesse:\n"
                    "https://calendly.com/daan-advgoias\n\n"
                    "Escolha o melhor horário para você. Será um prazer te atender."
                )
            elif texto == "4" or "outro" in texto:
                resposta = (
                    "Claro, me explique com mais detalhes o que você precisa.\n"
                    "Estou aqui para te ouvir e te ajudar com precisão e respeito."
                )
            else:
                resposta = (
                    "Recebi sua mensagem. Pode me dizer com mais clareza o que você deseja tratar?\n"
                    "Estou aqui para te guiar da melhor forma."
                )

            enviar_resposta(numero, resposta)

        elif tipo == "document":
            doc = msg.get("document", {})
            mime = doc.get("mime_type", "")
            url = doc.get("url")

            if mime == "application/pdf" and url:
                resposta = analisar_pdf_por_url(url)
            else:
                resposta = "Por enquanto, só consigo analisar arquivos em PDF. Por gentileza, envie o contrato nesse formato."

            enviar_resposta(numero, resposta)

        else:
            resposta = (
                "Recebi sua mensagem, mas ainda não consigo interpretar esse tipo de conteúdo.\n"
                "Você pode tentar novamente com um texto ou um contrato em PDF? Ficarei feliz em te ajudar."
            )
            enviar_resposta(numero, resposta)

        return jsonify({"status": "ok"})

    except Exception as e:
        print("❌ ERRO no webhook:", str(e))
        return jsonify({"erro": str(e)})

# === EXECUÇÃO NO RENDER ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
