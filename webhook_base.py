from flask import Flask, request
import requests
import openai
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

# Carrega variáveis do .env
load_dotenv()

# Configurar logs
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Variáveis de ambiente
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-text"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = openai.OpenAI(api_key=OPENAI_API_KEY)
HISTORICO_CLIENTES = {}
NUMERO_DIRETO = "556299812069"

PROMPT_BASE = """
Você é um assistente jurídico que trabalha para o escritório Teixeira.Brito Advogados, liderado pelo Dr. Dayan, especialista em contratos, sucessões, holding e renegociação de dívidas.

Seu objetivo é:
1. Entender a solicitação do cliente recebida via WhatsApp.
2. Ser cordial, claro, técnico e direto nas respostas.
3. Sempre responder como um advogado experiente e confiável, mantendo um tom de autoridade e empatia.
4. Caso a mensagem seja muito curta, como "oi", "bom dia", oriente o cliente a explicar o que precisa.
5. Caso a mensagem mencione documentos, contratos, processos ou análise, solicite o envio do material ou mais informações.
6. Evite respostas genéricas. Seja objetivo e resolutivo.
7. Se não conseguir compreender a solicitação ou se houver repetição de dúvidas, peça para aguardar atendimento humanizado.

Aqui está a mensagem recebida:
"{mensagem}"

Responda como se você fosse o próprio Dr. Dayan ou seu assistente jurídico.
"""

@app.route("/", methods=["GET"])
def health_check():
    return "Webhook Z-API rodando com sucesso.", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logger.info("📩 JSON recebido: %s", data)

    try:
        phone = data.get("participantPhone") or data.get("phone", "")
        from_me = data.get("fromMe", False)
        text_message = data.get("text", {}).get("message")
        is_group = data.get("isGroup", False)
        participant = data.get("participantPhone")

        if not from_me and text_message and phone:
            if is_group and (participant != NUMERO_DIRETO and NUMERO_DIRETO not in text_message):
                return "", 200

            if text_message.strip().startswith("#"):
                resposta = comando_direto(text_message)
            else:
                resposta = analisar_mensagem(text_message)

            if resposta:
                if precisa_atendimento_humano(phone, text_message):
                    resposta += "\n\n📣 Encaminhei sua solicitação para nosso atendimento humanizado. Em breve você receberá retorno."
                enviar_resposta(phone, resposta)

    except Exception as e:
        logger.error("❌ Erro ao processar mensagem: %s", str(e))

    return "", 200

def comando_direto(msg):
    comandos = {
        "#contrato": "Por favor, envie o contrato em PDF ou nos diga do que ele trata.",
        "#agendar": "Você pode agendar um horário com o Dr. Dayan pelo link: https://calendly.com/daan-advgoias",
        "#valores": "Nossos honorários são personalizados conforme a complexidade do caso. Envie mais detalhes para análise."
    }
    return comandos.get(msg.strip().lower(), "Comando não reconhecido. Envie sua dúvida ou utilize um dos comandos válidos: #contrato, #agendar, #valores.")

def analisar_mensagem(texto):
    prompt = PROMPT_BASE.format(mensagem=texto.strip())

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico experiente."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error("❌ Erro com OpenAI: %s", str(e))
        return "Recebi sua mensagem, mas ainda não consegui interpretar totalmente. Em breve, nossa equipe entrará em contato."

def precisa_atendimento_humano(numero, msg):
    historico = HISTORICO_CLIENTES.get(numero, {"repeticoes": 0, "ultima": "", "hora": datetime.now()})
    if msg.strip().lower() == historico["ultima"]:
        historico["repeticoes"] += 1
    else:
        historico["repeticoes"] = 1
        historico["ultima"] = msg.strip().lower()
    historico["hora"] = datetime.now()
    HISTORICO_CLIENTES[numero] = historico
    return historico["repeticoes"] >= 2

def enviar_resposta(numero, mensagem):
    payload = {
        "phone": numero,
        "message": mensagem
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_TOKEN
    }

    try:
        response = requests.post(ZAPI_URL, json=payload, headers=headers)
        logger.info("✅ Mensagem enviada para %s - Status: %s", numero, response.status_code)
        logger.info("Resposta: %s", response.text)
    except Exception as e:
        logger.error("❌ Erro ao enviar mensagem: %s", str(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
