from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime, timedelta

app = Flask(__name__)

# === VARIÁVEIS DE AMBIENTE ===
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN") or os.getenv("TOKEN_DA_INSTANCIA")

if not openai.api_key:
    print("⚠️ AVISO: OPENAI_API_KEY não definida.")
if not EXPECTED_CLIENT_TOKEN:
    print("⚠️ AVISO: CLIENT_TOKEN não definida.")

# === CONFIGURAÇÕES ===
HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["segunda", "terça", "quarta", "quinta", "sexta"]

CONTATO_DIRETO = "+55 62 99808-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"
ARQUIVO_CONTROLE = "controle_interacoes.json"

# === CONTROLE DE INTERAÇÕES ===
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
    salvar_controle(contato)

def registrar_interacao_manual(contato):
    if contato not in controle:
        controle[contato] = {}
    controle[contato]["interacao_manual"] = agora().isoformat()
    salvar_controle(contato)

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
        return not horario_comercial()
    return True

def foi_mencionado(mensagem):
    texto = mensagem.lower()
    return any(trigger in texto for trigger in ["@dayan", "dr. dayan", "doutor dayan", "doutora dayan"])

# === GPT-4 com log de erro detalhado ===
def analisar_com_gpt(mensagem, nome):
    prompt = f"""
Você é um assistente jurídico representando o Dr. Dayan.

Funções:
1. Identifique se a mensagem é pessoal, profissional ou urgente.
2. Se for pessoal ou irrelevante, responda com: IGNORAR.
3. Se for urgente fora do horário, oriente contato direto via: {CONTATO_DIRETO}.
4. Se for profissional fora do horário, ofereça agendamento via: {LINK_CALENDLY}.
5. Se for profissional no horário, responda com empatia e linguagem formal.

Mensagem:
"{mensagem}"

Remetente: {nome}
"""
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=400
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Erro ao consultar o GPT:")
        print(e)  # <- Isso aparecerá nos logs da Render
        return "Desculpe, houve um erro ao processar sua solicitação."

# === ROTA PRINCIPAL ===
@app.route("/webhook", methods=["POST"])
def webhook():
    token = request.headers.get("Client-Token")

    if not token:
        return jsonify({"error": "Cabeçalho 'Client-Token' ausente."}), 403
    if token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Token inválido."}), 403

    data = request.json
    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    mensagem = data.get("message", "")
    contato = grupo or nome
    is_grupo = bool(grupo)

    if is_grupo and not foi_mencionado(mensagem):
        return jsonify({"response": None})

    if not deve_responder(contato):
        return jsonify({"response": None})

    resposta = analisar_com_gpt(mensagem, nome)

    if resposta.strip().upper() == "IGNORAR":
        return jsonify({"response": None})

    marcar_resposta(contato)
    return jsonify({"response": resposta})

# === ROTA DE STATUS ===
@app.route("/", methods=["GET"])
def status():
    return jsonify({
        "status": "online",
        "message": "Servidor do Webhook Dr. Dayan ativo ✅"
    })

# === ROTA PARA REGISTRO MANUAL ===
@app.route("/registrar-manual", methods=["POST"])
def registrar_manual():
    data = request.json
    contato = data.get("contato")
    if not contato:
        return jsonify({"error": "Contato é obrigatório"}), 400
    registrar_interacao_manual(contato)
    return jsonify({"status": "Registrado com sucesso."})

# === TRATAMENTO DE ERRO 404 ===
@app.errorhandler(404)
def rota_nao_encontrada(e):
    return jsonify({
        "error": "Rota não encontrada. Use /webhook para POSTs válidos."
    }), 404

# === EXECUÇÃO ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
