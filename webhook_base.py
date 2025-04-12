from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime, timedelta

app = Flask(__name__)

# ========== CONFIGURAÇÕES ==========
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")

if not openai.api_key or not EXPECTED_CLIENT_TOKEN:
    raise Exception("As variáveis OPENAI_API_KEY e CLIENT_TOKEN precisam estar definidas.")

HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["segunda", "terça", "quarta", "quinta", "sexta"]

CONTATO_DIRETO = "+55 62 99808-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

ARQUIVO_CONTROLE = "controle_interacoes.json"

# ========== CARREGAR HISTÓRICO ==========
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

# ========== FUNÇÕES UTILITÁRIAS ==========
def agora():
    return datetime.now()

def hoje():
    return agora().strftime("%Y-%m-%d")

def horario_comercial():
    dia = agora().strftime("%A").lower()
    hora = agora().hour
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
    if foi_atendido_hoje(contato):
        return not horario_comercial()  # só responde fora do horário se for urgente
    return True

def foi_mencionado(mensagem):
    texto = mensagem.lower()
    return any(trigger in texto for trigger in ["@dayan", "dr. dayan", "doutor dayan", "doutora dayan"])

# ========== GPT-4 ==========
def analisar_com_gpt(mensagem, nome):
    prompt = f"""
Você é um assistente jurídico representando o Dr. Dayan.

Funções:
1. Identifique se a mensagem é pessoal, profissional ou urgente.
2. Se for pessoal ou irrelevante, responda com: IGNORAR.
3. Se for urgente e fora do horário, oriente a entrar em contato imediato via: {CONTATO_DIRETO}.
4. Se for profissional mas fora do horário, ofereça o link de agendamento: {LINK_CALENDLY}.
5. Se for profissional e dentro do horário, responda com linguagem educada, empática e formal. Use "Sr.", "Sra.", "Dr.", etc.

Mensagem:
"{mensagem}"

Nome do remetente: {nome}
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

    if not token:
        return jsonify({"error": "Cabeçalho 'Client-Token' ausente"}), 403
    if token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Token inválido"}), 403

    data = request.json
    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    mensagem = data.get("message", "")
    contato = grupo or nome
    is_grupo = bool(grupo)

    # Regras para grupos: só responde se for mencionado
    if is_grupo and not foi_mencionado(mensagem):
        return jsonify({"response": None})

    # Verifica se deve responder com base na sua interação ou limite diário
    if not deve_responder(contato):
        return jsonify({"response": None})

    # Analisar com IA
    resposta = analisar_com_gpt(mensagem, nome)

    if resposta.strip().upper() == "IGNORAR":
        return jsonify({"response": None})

    marcar_resposta(contato)
    return jsonify({"response": resposta})

# ========== REGISTRAR INTERAÇÃO MANUAL ==========
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
