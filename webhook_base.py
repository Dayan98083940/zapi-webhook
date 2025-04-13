from flask import Flask, request, jsonify
import os
import json
import openai
from datetime import datetime

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")

CONTATO_DIRETO = "+55(62)99808-3940"
CONTATO_FIXO = "(62) 3922-3940"
CONTATO_BACKUP = "(62) 99981-2069"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

GRUPOS_BLOQUEADOS = ["sagrada família", "providência santa"]
CONTATOS_PESSOAIS = ["pai", "mab", "joão", "pedro", "amor", "érika", "felipe", "helder"]

# === SAUDAÇÃO POR HORÁRIO ===
def gerar_saudacao():
    hora = datetime.now().hour
    if hora < 12:
        return "Bom dia"
    elif 12 <= hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

# === FILTROS ===
def mensagem_é_para_grupo(nome_remetente):
    return any(g in nome_remetente.lower() for g in GRUPOS_BLOQUEADOS)

def contato_excluido(nome):
    return any(p in nome.lower() for p in CONTATOS_PESSOAIS)

# === WEBHOOK PRINCIPAL ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        print("[ERRO] Headers inválidos.")
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json
    try:
        mensagem = data.get("message", "").strip()
        numero = data.get("phone", "")
        nome = data.get("name", "")

        print(f"📥 Mensagem recebida de {numero} ({nome}): {mensagem}")

        resposta = gerar_resposta_gpt(mensagem, nome)
        print(f"📤 Resposta enviada: {resposta}")
        return jsonify({"response": resposta})

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {repr(e)}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === GPT-4 ESTILO DAYAN ===
def gerar_resposta_gpt(pergunta, nome_cliente):
    saudacao = gerar_saudacao()
    pergunta_lower = pergunta.lower()
    explicativo = any(p in pergunta_lower for p in ["o que é", "como funciona", "para que serve", "pra que serve"])

    if explicativo:
        introducao = f"{saudacao}, Sr(a). {nome_cliente}.\n\nClaro, vou te explicar de forma objetiva:\n"
    else:
        introducao = (
            f"{saudacao}, Sr(a). {nome_cliente}.\n\n"
            "Antes de te orientar com segurança, preciso entender melhor sua situação. "
            "Pode me contar, resumidamente, o que está acontecendo?"
        )

    prompt = f"""
Você é o assistente jurídico digital do Dr. Dayan, advogado especialista em contratos, sucessões, holdings, regularização de imóveis, renegociação de dívidas e proteção patrimonial.

Seu estilo de resposta deve seguir o padrão Dayan:
- Formal, respeitoso e direto.
- Comece acolhendo o cliente com base na situação apresentada.
- Se a pergunta for do tipo "o que é", "como funciona", "para que serve", explique com clareza e brevidade.
- Caso contrário, investigue com perguntas curtas e assertivas para compreender a necessidade real.
- Não repita frases genéricas ou vazias.
- Limite a resposta a no máximo 3 parágrafos curtos.
- Finalize sempre com:

📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}  
Se não conseguir falar com o Dr. Dayan, entre em contato com o atendimento: {CONTATO_FIXO} ou {CONTATO_BACKUP}

Mensagem recebida do cliente:
{pergunta}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    texto = response.choices[0].message["content"].strip()
    return f"{introducao}\n\n{texto}"

# === ROTA DE STATUS ===
@app.route("/")
def home():
    return "🟢 Integração Whats TB ativa com Estilo Dayan"
