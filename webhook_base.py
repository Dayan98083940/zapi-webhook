from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime, timedelta

app = Flask(__name__)

# ========== CONFIGURAÇÕES ==========
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "seu_token_aqui")

HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["segunda", "terça", "quarta", "quinta", "sexta"]

CONTATO_DIRETO = "+55 62 99808-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

ARQUIVO_CONTROLE = "controle_interacoes.json"

# ========== HISTÓRICO DE INTERAÇÕES ==========
def carregar_controle():
    try:
        with open(ARQUIVO_CONTROLE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def salvar_controle(dados):
    with open(ARQUIVO_CONTROLE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

controle = carregar_controle()

# ========== FUNÇÕES DE CONTROLE ==========
def agora():
    return datetime.now()

def hoje():
    return datetime.now().strftime("%Y-%m-%d")

def horario_comercial():
    dia = datetime.now().strftime("%A").lower()
    hora = datetime.now().hour
    return dia in DIAS_UTEIS and HORARIO_INICIO <= hora < HORARIO_FIM

def foi_atendido_hoje(contato):
    return controle.get(contato, {}).get("ultima_resposta") == hoje()

def marcar_resposta(contato):
    if contato not in controle:
        controle[contato] = {}
    controle[contato]["ultima_resposta"] = hoje()
    salvar_controle(controle)

def registrar_interacao_manual(contato):
    if contato not in controle:
        controle[contato] = {}
    controle[contato]["interacao_manual"] = agora().isoformat()
    salvar_controle(controle)

def pausado_por_interacao(contato):
    interacao = controle.get(contato, {}).get("interacao_manual")
    if not interacao:
        return False
    ultima = datetime.fromisoformat(interacao)
    return agora() - ultima < timedelta(minutes=30)

def deve_responder(contato):
    if pausado_por_interacao(contato):
        return False
    if not horario_comercial() and foi_atendido_hoje(contato):
        return False
    if horario_comercial() and foi_atendido_hoje(contato):
        return False
    return True

def foi_mencionado(mensagem):
    texto = mensagem.lower()
    return any(trigger in texto for trigger in ["@dayan", "dr. dayan", "doutor dayan", "doutora dayan"])

# ========== GPT-4 ==========
def analisar_com_gpt(mensagem, nome):
    prompt = f"""
Você é um assistente jurídico em nome do Dr. Dayan.

Analise a mensagem recebida abaixo:
- Determine se é pessoal, profissional ou urgente
- Caso pessoal → responda: IGNORAR
- Caso urgente fora do horário → forneça o número direto: {CONTATO_DIRETO}
- Caso profissional fora do horário → ofereça agendamento via Calendly: {LINK_CALENDLY}
- Caso profissional no horário → responda com empatia e linguagem formal

Mensagem:
"{mensagem}"
De: {nome}
"""
    resposta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=400
    )
    return resposta.choices[0].message.content.strip()

# ========== WEBHOOK PRINCIPAL ==========
@app.route("/webhook", methods=["POST"])
def webhook():
    token = request.headers.get("Client-Token")
    if token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    mensagem = data.get("message", "")
    contato = grupo or nome
    is_grupo = bool(grupo)

    # Regra para grupos: só responde com menção
    if is_grupo and not foi_mencionado(mensagem):
        return jsonify({"response": None})

    # Não responde se você interagiu recentemente
    if not deve_responder(contato):
        return jsonify({"response": None})

    # Analisa com GPT
    resposta = analisar_com_gpt(mensagem, nome)

    if resposta.strip().upper() == "IGNORAR":
        return jsonify({"response": None})

    marcar_resposta(contato)
    return jsonify({"response": resposta})

# ========== ROTA OPCIONAL PARA REGISTRAR SUA INTERAÇÃO MANUAL ==========
@app.route("/registrar-manual", methods=["POST"])
def registrar_manual():
    data = request.json
    contato = data.get("contato")
    if not contato:
        return jsonify({"error": "Contato é obrigatório"}), 400
    registrar_interacao_manual(contato)
    return jsonify({"status": "Registrado com sucesso."})

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
