from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime, timedelta
import traceback

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN") or os.getenv("TOKEN_DA_INSTANCIA")

if not openai.api_key:
    print("⚠️ OPENAI_API_KEY não definida.")
if not EXPECTED_CLIENT_TOKEN:
    print("⚠️ CLIENT_TOKEN não definido.")

HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["monday", "tuesday", "wednesday", "thursday", "friday"]

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

def foi_mencionado(mensagem):
    texto = mensagem.lower()
    return any(trigger in texto for trigger in ["@dayan", "dr. dayan", "doutor dayan", "doutora dayan"])

# === GERA RESPOSTA HUMANIZADA COM GPT ===
def gerar_resposta(mensagem, nome, fora_horario=False):
    if fora_horario:
        return (
            f"Olá, {nome}. Agradeço pelo contato.\n\n"
            f"No momento estamos fora do horário de atendimento (segunda a sexta, das 8h às 18h).\n"
            f"Você pode agendar um horário para amanhã no link abaixo, ou me enviar uma mensagem caso seja urgente:\n"
            f"📅 {LINK_CALENDLY}\n📞 {CONTATO_DIRETO}"
        )

    prompt = f"""
Você é um assistente jurídico representando o advogado Dr. Dayan.

Seu papel é iniciar o atendimento de forma humanizada, acolhedora e respeitosa.

Nunca forneça pareceres jurídicos, mas ofereça o primeiro acolhimento e, quando necessário, redirecione para o agendamento com o Dr. Dayan ou para contato direto.

Mensagem recebida:
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
        traceback.print_exc()
        print(f"❌ Erro ao gerar resposta com GPT: {e}")
        return "Desculpe, houve um erro ao processar sua solicitação."

# === ROTA PRINCIPAL ===
@app.route("/webhook", methods=["POST"])
def webhook():
    token = request.headers.get("Client-Token")
    print(f"🔐 Token recebido: {token}")
    
    if not token:
        return jsonify({"error": "Cabeçalho 'Client-Token' ausente."}), 403
    if token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Token inválido."}), 403

    data = request.json
    print("📥 Dados recebidos:", json.dumps(data, indent=2, ensure_ascii=False))

    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    mensagem = data.get("message", "")
    contato = grupo or nome
    is_grupo = bool(grupo)

    print(f"📩 Mensagem de: {nome} | Grupo: {grupo or 'Privado'}")
    print(f"📨 Conteúdo: {mensagem}")

    if is_grupo and not foi_mencionado(mensagem):
        print("🔕 Ignorado: mensagem em grupo sem menção.")
        return jsonify({"response": None})

    if pausado_por_interacao(contato):
        print("⏸️ IA pausada por interação manual.")
        return jsonify({"response": None})

    # Resposta rápida por palavra-chave (opcional)
    if "contrato" in mensagem.lower():
        resposta = "Perfeito, podemos te ajudar com isso. Você deseja um contrato imobiliário, empresarial ou outro?"
    elif not horario_comercial():
        resposta = gerar_resposta(mensagem, nome, fora_horario=True)
    else:
        resposta = gerar_resposta(mensagem, nome)

    marcar_resposta(contato)
    print(f"✅ Resposta enviada: {resposta[:100]}...")
    return jsonify({"response": resposta})

# === ROTA DE STATUS ===
@app.route("/", methods=["GET"])
def status():
    return jsonify({
        "status": "online",
        "message": "Servidor do Webhook Dr. Dayan ativo ✅"
    })

# === ERRO 404 ===
@app.errorhandler(404)
def rota_nao_encontrada(e):
    return jsonify({
        "error": "Rota não encontrada. Use /webhook para POSTs válidos."
    }), 404

# === EXECUÇÃO ===
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
