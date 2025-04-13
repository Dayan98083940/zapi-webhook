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

HORARIO_INICIO = 8
HORARIO_FIM = 18
DIAS_UTEIS = ["segunda", "terça", "quarta", "quinta", "sexta"]

CONTATOS_PESSOAIS = ["pai", "mab", "joão", "pedro", "amor", "érika", "helder", "felipe"]
GRUPOS_BLOQUEADOS = ["sagrada família", "providência santa"]

CONTATO_DIRETO = "+55(62)99808-3940"
EMAIL_CONTATO = "dayan@advgoias.com.br"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"
ARQUIVO_CONTROLE = "controle_interacoes.json"

PALAVRAS_CHAVE = {
    "inventário": "Para inventário, podemos dar andamento de forma rápida. Posso te enviar a lista de documentos?",
    "contrato": "Qual contrato você deseja elaborar? Informe o tipo de negócio jurídico para que possamos estruturar com segurança.",
    "divórcio": "Se for consensual, conseguimos resolver de forma rápida. Se for litigioso, podemos analisar o caso com urgência. Deseja marcar um horário?",
    "renegociação de dívidas": "Trabalhamos com renegociação de dívidas bancárias e empresariais. Me diga um pouco sobre sua situação.",
    "atraso de obra": "Você está com problema em obra atrasada? Podemos verificar se há fundamento para restituição ou ação por descumprimento.",
    "leilão": "Você deseja participar de um leilão ou evitar um? Atendemos ambos os casos com segurança jurídica.",

    "holding": (
        "A holding é uma estrutura jurídica voltada para proteger, organizar e controlar bens e empresas. "
        "Ela pode assumir diferentes formatos e finalidades, como:\n\n"
        "🔹 *Holding Familiar*: foco no planejamento sucessório e na proteção do patrimônio da família;\n"
        "🔹 *Holding Rural*: voltada para produtores e proprietários de terras, facilita a sucessão e organização patrimonial do agronegócio;\n"
        "🔹 *Holding Imobiliária*: ideal para quem possui imóveis, centraliza a gestão, facilita a sucessão e gera benefícios fiscais.\n\n"
        f"Cada tipo exige análise personalizada. Agende um atendimento em {LINK_CALENDLY} ou fale no WhatsApp {CONTATO_DIRETO}."
    ),

    "holding familiar": (
        "A holding familiar é uma ferramenta eficaz para proteger o patrimônio da família, planejar a sucessão e reduzir custos com inventário. "
        "Permite organizar os bens em uma empresa, com cotas divididas entre os membros da família, evitando conflitos e garantindo continuidade.\n\n"
        f"Para saber como aplicar esse modelo no seu caso, agende em {LINK_CALENDLY} ou chame no WhatsApp {CONTATO_DIRETO}."
    ),

    "holding rural": (
        "A holding rural é ideal para produtores que desejam planejar a sucessão da fazenda, proteger seus bens e administrar melhor o patrimônio familiar. "
        "Ela evita a fragmentação de terras, reduz impostos em caso de doação e facilita o controle da atividade agrícola.\n\n"
        f"Se quiser saber como aplicar no seu caso, agende conosco: {LINK_CALENDLY} ou fale pelo WhatsApp {CONTATO_DIRETO}."
    ),

    "holding imobiliária": (
        "A holding imobiliária permite administrar e proteger imóveis próprios ou alugados de forma eficiente. "
        "Ela facilita a sucessão dos bens, reduz impostos em doações e centraliza a gestão patrimonial.\n\n"
        f"Se você possui imóveis e quer estruturar isso com segurança, agende um diagnóstico em {LINK_CALENDLY} ou envie mensagem para {CONTATO_DIRETO}."
    )
}

def carregar_controle():
    if os.path.exists(ARQUIVO_CONTROLE):
        with open(ARQUIVO_CONTROLE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_controle(controle):
    with open(ARQUIVO_CONTROLE, "w", encoding="utf-8") as f:
        json.dump(controle, f, indent=2, ensure_ascii=False)

controle = carregar_controle()

def fora_do_horario():
    agora = datetime.now()
    dia_semana = agora.strftime("%A").lower()
    return dia_semana not in DIAS_UTEIS or not (HORARIO_INICIO <= agora.hour < HORARIO_FIM)

def mensagem_é_para_grupo(nome_remetente):
    return any(g in nome_remetente.lower() for g in GRUPOS_BLOQUEADOS)

def contato_excluido(nome):
    return any(p in nome.lower() for p in CONTATOS_PESSOAIS)

@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    if token != WEBHOOK_URL_TOKEN:
        return jsonify({"erro": "Token inválido na URL."}), 403

    client_token = request.headers.get("Client-Token")
    content_type = request.headers.get("Content-Type")

    if client_token != EXPECTED_CLIENT_TOKEN or content_type != "application/json":
        return jsonify({"erro": "Headers inválidos."}), 403

    data = request.json

    try:
        mensagem = data.get("message", "").strip().lower()
        numero = data.get("phone", "")
        nome = data.get("name", "")

        print(f"\n[{datetime.now()}] 📥 Mensagem de {numero} ({nome}): {mensagem}")

        if mensagem_é_para_grupo(nome) or contato_excluido(nome):
            print("❌ Ignorado (grupo ou contato pessoal).")
            return jsonify({"status": "ignorado"})

        if "teste-dayan" not in mensagem and fora_do_horario():
            resposta = f"Olá! Nosso atendimento é de segunda a sexta, das 08h às 18h. Deseja agendar um horário? {LINK_CALENDLY}"
        elif mensagem in PALAVRAS_CHAVE:
            resposta = PALAVRAS_CHAVE[mensagem]
        else:
            resposta = gerar_resposta_gpt(mensagem)

        print(f"📤 Resposta enviada: {resposta}")
        return jsonify({
            "response": f"{resposta}\n\n📌 Fale com Dr. Dayan: {CONTATO_DIRETO} | 📧 {EMAIL_CONTATO} | Agende: {LINK_CALENDLY}"
        })

    except Exception as e:
        print(f"❌ Erro ao processar mensagem: {repr(e)}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

def gerar_resposta_gpt(pergunta):
    prompt = f"""
Você é assistente jurídico do escritório Teixeira.Brito Advogados, liderado por Dayan, especialista em contratos, sucessões, holding e renegociação de dívidas.

Responda com educação, clareza, objetividade e segurança jurídica no estilo Dayan.

Pergunta: {pergunta}

Se não for possível responder com segurança, oriente o cliente a agendar atendimento pelo link: {LINK_CALENDLY} ou falar direto no WhatsApp {CONTATO_DIRETO}.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    texto = response.choices[0].message["content"].strip()
    texto += f"\n\n📌 WhatsApp: {CONTATO_DIRETO} | 📧 {EMAIL_CONTATO} | Agende: {LINK_CALENDLY}"
    return texto

@app.route("/")
def home():
    return "🟢 Servidor ativo com GPT-4, pronto para orientar sobre holdings e muito mais."
