from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime, timedelta

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "seu_token_aqui")
ATENDIMENTO = {
    "inicio": 8,
    "fim": 18,
    "dias": ["segunda", "terca", "quarta", "quinta", "sexta"]
}
NUMERO_URGENTE = "+55 62 99808-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# === DADOS DE CONTROLE ===
ARQUIVO_CONTROLE = "controle_interacoes.json"

# Carregar histórico
if os.path.exists(ARQUIVO_CONTROLE):
    with open(ARQUIVO_CONTROLE, encoding='utf-8') as f:
        controle = json.load(f)
else:
    controle = {}

def salvar_controle():
    with open(ARQUIVO_CONTROLE, "w", encoding='utf-8') as f:
        json.dump(controle, f, ensure_ascii=False, indent=2)

# === FUNÇÕES DE REGRAS ===

def eh_horario_comercial():
    agora = datetime.now()
    dia_semana = agora.strftime("%A").lower()
    return dia_semana in ATENDIMENTO["dias"] and ATENDIMENTO["inicio"] <= agora.hour < ATENDIMENTO["fim"]

def ja_interagiu_hoje(contato):
    hoje = datetime.now().strftime("%Y-%m-%d")
    return controle.get(contato, {}).get("ultima_resposta", "") == hoje

def usuario_assumiu(contato):
    dado = controle.get(contato, {})
    if not dado.get("interacao_manual"):
        return False
    ultima = datetime.fromisoformat(dado["interacao_manual"])
    return datetime.now() - ultima < timedelta(minutes=30)

def registrar_interacao_manual(contato):
    if contato not in controle:
        controle[contato] = {}
    controle[contato]["interacao_manual"] = datetime.now().isoformat()
    salvar_controle()

def registrar_resposta(contato):
    if contato not in controle:
        controle[contato] = {}
    controle[contato]["ultima_resposta"] = datetime.now().strftime("%Y-%m-%d")
    salvar_controle()

def foi_mencionado(texto, nome="dayan"):
    texto = texto.lower()
    return any(x in texto for x in [f"@{nome}", "dr. dayan", "doutor dayan"])

def analisar_mensagem(texto, nome_contato):
    prompt = f"""
Você é um assistente jurídico representando o Dr. Dayan. Analise a seguinte mensagem:

Mensagem: "{texto}"

1. A mensagem é pessoal ou profissional?
2. É urgente ou pode esperar?
3. Responda com empatia e linguagem formal, usando Sr., Sra., Dr., etc.

Se a mensagem for pessoal ou irrelevante, responda apenas com: IGNORAR
Se for urgente, direcione para o telefone pessoal: {NUMERO_URGENTE}
Se for profissional mas não urgente fora do horário, sugira o agendamento via: {LINK_CALENDLY}
"""
    resposta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=500
    )
    return resposta.choices[0].message.content.strip()

@app.route("/webhook", methods=["POST"])
def responder():
    token = request.headers.get("Client-Token")
    if token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    mensagem = data.get("message", "")
    is_grupo = bool(grupo)
    contato = grupo or nome

    # Se for grupo e não for menção direta, ignora
    if is_grupo and not foi_mencionado(mensagem):
        return jsonify({"response": None})

    # Se você interagiu nos últimos 30 minutos, IA não responde
    if usuario_assumiu(contato):
        return jsonify({"response": None})

    # Se já respondeu hoje e ainda está dentro do horário, mantém silêncio
    if ja_interagiu_hoje(contato) and eh_horario_comercial():
        return jsonify({"response": None})

    # Se for fora do expediente, analisa via IA
    if not eh_horario_comercial():
        resposta = analisar_mensagem(mensagem, nome)
        if resposta == "IGNORAR":
            return jsonify({"response": None})
        registrar_resposta(contato)
        return jsonify({"response": resposta})

    # Durante o expediente — análise completa
    resposta = analisar_mensagem(mensagem, nome)
    if resposta == "IGNORAR":
        return jsonify({"response": None})

    registrar_resposta(contato)
    return jsonify({"response": resposta})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
