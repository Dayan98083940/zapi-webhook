from flask import Flask, request, jsonify
import os
import openai
import requests
from datetime import datetime, date

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")

ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"

CONTATO_DIRETO = "+55(62)99808-3940"
CONTATO_FORMATADO = "5562998083940"  # Número formatado para Z-API
CONTATO_FIXO = "(62) 3922-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# Tratamento adequado para lista de bloqueados
BLOQUEAR_NUMEROS_ENV = os.getenv("BLOQUEADOS", "")
BLOQUEAR_NUMEROS = [num for num in BLOQUEAR_NUMEROS_ENV.split(",") if num.strip()]

CONVERSAS = {}
ATENDIMENTO_MANUAL = {}

GATILHOS_RESPOSTA = [
    "quero", "gostaria", "preciso", "dúvida", "processo",
    "como faço", "o que fazer", "procedimento",
    "orientação", "ajuda", "tem como", "posso", "informação", "reunião", "agendamento"
]

SAUDACOES = ["bom dia", "boa tarde", "boa noite"]

# === FUNÇÕES DE APOIO ===
def gerar_saudacao():
    hora = datetime.now().hour
    if hora < 12:
        return "Bom dia"
    elif hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

def formata_tratamento(nome):
    nome = nome.lower()
    if "advogado" in nome or "advogada" in nome:
        return f"Dr(a). {nome.split()[0].capitalize()}"
    return f"Sr(a). {nome.split()[0].capitalize()}" if nome else "Cliente"

def deve_responder(mensagem, numero):
    if numero in BLOQUEAR_NUMEROS or "-group" in numero:
        return False
    if numero in ATENDIMENTO_MANUAL and ATENDIMENTO_MANUAL[numero] == str(date.today()):
        print(f"⛔ Atendimento manual ativo para {numero}")
        return False
    msg_lower = mensagem.lower()
    return any(g in msg_lower for g in GATILHOS_RESPOSTA + SAUDACOES)

# === WEBHOOK PRINCIPAL ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    print(f"Webhook acionado com token: {token}")
    print(f"Headers recebidos: {dict(request.headers)}")
    
    if token != WEBHOOK_URL_TOKEN:
        print(f"❌ Token inválido recebido: {token}")
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")
    print(f"🔍 Recebido — Client-Token: {client_token}, Content-Type: {content_type}")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        print("❌ Headers inválidos.")
        return jsonify({"erro": "Headers inválidos."}), 403

    try:
        data = request.json
        print(f"Dados recebidos: {data}")
        
        mensagem = data.get("message", "").strip()
        numero = data.get("phone", "").strip()
        nome = data.get("name", "").strip() or "Cliente"

        if not mensagem:
            print(f"📥 Mensagem vazia recebida de {numero} — ignorada.")
            return jsonify({"status": "ignorado"})

        if not deve_responder(mensagem, numero):
            print(f"📥 Mensagem sem gatilho recebida de {numero}: {mensagem}")
            return jsonify({"status": "ignorado"})

        resposta = gerar_resposta_gpt(mensagem, nome)
        CONVERSAS.setdefault(numero, []).extend([f"Cliente: {mensagem}", f"Assistente: {resposta}"])

        enviar_resposta_via_zapi(numero, resposta)
        return jsonify({"status": "respondido", "para": numero, "resposta": resposta})
    except Exception as e:
        print(f"❌ Erro ao processar requisição: {e}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === ENVIO Z-API ===
def enviar_resposta_via_zapi(telefone, mensagem):
    if "-group" in telefone or not mensagem.strip():
        print(f"🚫 Mensagem bloqueada para grupo ou vazia: {telefone}")
        return

    # Formatação do número de telefone (se necessário)
    telefone_formatado = telefone
    if not telefone.startswith("55") and telefone.startswith("+"):
        # Remove caracteres não numéricos
        telefone_formatado = ''.join(filter(str.isdigit, telefone))

    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    headers = {
        "Content-Type": "application/json",
        "Client-token": EXPECTED_CLIENT_TOKEN
    }
    payload = {"phone": telefone_formatado, "message": mensagem}
    
    print(f"Payload enviado à Z-API: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"📤 Enviado com sucesso para {telefone}")
        else:
            print(f"❌ Erro ao enviar: Status {response.status_code}, Resposta: {response.text}")
    except Exception as e:
        print(f"❌ Falha ao enviar via Z-API: {e}")

# === GERADOR DE RESPOSTA (GPT-4 Turbo) ===
def gerar_resposta_gpt(mensagem, nome_cliente):
    saudacao = gerar_saudacao()
    tratamento = formata_tratamento(nome_cliente)

    fora_do_horario = datetime.now().hour < 8 or datetime.now().hour >= 18

    if mensagem.lower() in SAUDACOES:
        return (f"{saudacao}, {tratamento}! Como posso auxiliar hoje?\n\n"
                f"Desde já, obrigado pelo contato! 📞 {CONTATO_FIXO} | 📅 {LINK_CALENDLY}")

    if fora_do_horario:
        return (f"{saudacao}, {tratamento}! Nosso atendimento é das 08h às 18h. "
                f"Por favor, agende seu atendimento pelo link: {LINK_CALENDLY}. "
                "Agradecemos a compreensão!")

    prompt = f"""
    Você é um assistente jurídico educado, cordial e objetivo do escritório Teixeira Brito Advogados. 
    Seu objetivo é identificar rapidamente a necessidade do cliente e oferecer direcionamento gentil e eficiente sem detalhar juridicamente.

    Mensagem recebida: "{mensagem}"

    Finalize cordialmente agradecendo e informando que pode ligar para o Dr. Dayan em {CONTATO_DIRETO} ou agendar pelo link {LINK_CALENDLY}.
    """

    try:
        # Versão atualizada da chamada da API OpenAI
        response = openai.chat.completions.create(
            model="gpt-4-0125-preview",  # Nome correto do modelo
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        corpo = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro OpenAI: {e}")
        # Tentar método antigo caso o novo falhe
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            corpo = response.choices[0].message["content"].strip()
        except Exception as e2:
            print(f"Erro OpenAI (método antigo): {e2}")
            corpo = ("No momento não conseguimos gerar uma resposta automática. "
                    "Entre em contato diretamente pelo telefone.")

    return f"{saudacao}, {tratamento}.\n\n{corpo}\n\nObrigado pelo contato! 📞 {CONTATO_FIXO} | 📅 {LINK_CALENDLY}"

# === ROTAS AUXILIARES ===
@app.route("/atendimento-manual", methods=["POST"])
def atendimento_manual():
    numero = request.json.get("numero", "").strip()
    if numero:
        ATENDIMENTO_MANUAL[numero] = str(date.today())
        return jsonify({"status": "registrado", "numero": numero})
    return jsonify({"erro": "Número inválido."}), 400

@app.route("/conversas/<numero>", methods=["GET"])
def conversa(numero):
    return jsonify(CONVERSAS.get(numero, ["Sem histórico."]))

@app.route("/debug", methods=["GET"])
def debug_info():
    # Não retorne chaves sensíveis em produção!
    return jsonify({
        "configurações": {
            "webhook_token_definido": bool(WEBHOOK_URL_TOKEN),
            "client_token_definido": bool(EXPECTED_CLIENT_TOKEN),
            "openai_key_definida": bool(openai.api_key),
            "zapi_configurada": bool(ZAPI_INSTANCE_URL and ZAPI_TOKEN),
        },
        "estatísticas": {
            "conversas_ativas": len(CONVERSAS),
            "atendimentos_manuais": len(ATENDIMENTO_MANUAL),
            "números_bloqueados": BLOQUEAR_NUMEROS
        }
    })

@app.route("/")
def home():
    return "🟢 Whats TB rodando — Atendimento Automatizado Teixeira Brito Advogados"

# === RUN LOCAL ===
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
