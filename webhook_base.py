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

CONTATO_DIRETO = "+55(62)99808-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"
ARQUIVO_CONTROLE = "controle_interacoes.json"

CONTATOS_PESSOAIS = ["pai", "mab", "joão", "pedro", "amor", "érika", "helder", "felipe"]
GRUPOS_BLOQUEADOS = ["sagrada família", "providência santa"]

# === PALAVRAS-CHAVE E RESPOSTAS ===

PALAVRAS_CHAVE = {
    "inventário": (
        "Posso te ajudar com questões relacionadas ao inventário. Para que eu possa orientar da melhor forma, me diga:\n\n"
        "📌 Em que exatamente podemos ajudar? Você já iniciou o processo ou está em fase de organização?\n"
        "📌 Gostaria que eu enviasse a relação dos documentos necessários?\n"
        "📌 Prefere agendar um horário ou conversar por telefone?\n\n"
        f"📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    "contrato": (
        "Claro, posso te ajudar com questões contratuais. Para oferecer a melhor orientação, preciso entender melhor:\n\n"
        "📌 Você precisa elaborar um contrato ou analisar um já existente?\n"
        "📌 Qual o tipo de negócio jurídico envolvido? (Ex: prestação de serviços, compra e venda, locação, sociedade etc.)\n\n"
        f"📌 Me envie essas informações por aqui, ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    "divórcio": (
        "Podemos te ajudar com o processo de divórcio. Para entendermos melhor sua situação, poderia me informar:\n\n"
        "📌 Em que exatamente você precisa de ajuda no divórcio?\n"
        "📌 O casal tem filhos menores ou incapazes?\n"
        "📌 Existe patrimônio ou bens a serem partilhados?\n"
        "📌 As partes estão de comum acordo ou há conflito?\n\n"
        "Essas informações são importantes para sabermos se o divórcio poderá ser extrajudicial (em cartório) ou judicial.\n\n"
        f"📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    "leilão": (
        "Vamos entender melhor sua situação com relação ao leilão. Por gentileza, me informe:\n\n"
        "📌 Você deseja investir em um imóvel que será leiloado?\n"
        "📌 Ou o seu imóvel está indo a leilão ou já foi arrematado?\n\n"
        "Se for investidor, por favor envie o edital do leilão e os dados do bem que pretende arrematar.\n"
        "Se for proprietário ou interessado em suspender ou anular o leilão, me informe:\n"
        "- 📍 Dados do imóvel;\n"
        "- 📎 Número do processo, se houver;\n"
        "- 📆 Data do leilão ou se ele já ocorreu.\n\n"
        f"📌 Envie essas informações por aqui, ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    "atraso de obra": (
        "Se você comprou um imóvel na planta e ainda não recebeu, podemos analisar sua situação para verificar se há responsabilidade da incorporadora e quais medidas cabíveis.\n\n"
        "Para isso, precisarei de:\n"
        "📎 Cópia do contrato de compra e venda;\n"
        "📄 Certidão da matrícula do imóvel;\n"
        "📆 Data prevista de entrega.\n\n"
        "Importante: se o atraso estiver dentro do prazo de carência de 180 dias, não há penalidade ao incorporador. Após esse prazo, é possível pleitear indenizações.\n\n"
        f"📌 Me envie os documentos ou ligue para: {CONTATO_DIRETO} — se preferir, agende: {LINK_CALENDLY}"
    ),

    "regularização de imóveis": (
        "Podemos te ajudar na regularização do seu imóvel. Para entender o melhor caminho, me diga:\n\n"
        "📌 O imóvel possui matrícula?\n"
        "📌 A construção está averbada?\n"
        "📌 Você tem contrato, escritura ou apenas a posse?\n\n"
        "Podemos atuar com:\n"
        "- Averbação de construção ou desmembramento;\n"
        "- Usucapião (judicial ou extrajudicial);\n"
        "- Retificação de área;\n"
        "- Formalização da posse com base em documentação.\n\n"
        f"📌 Me envie os dados por aqui, ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    "holding": (
        "A holding é uma estrutura jurídica voltada para proteger, organizar e controlar bens e empresas. "
        "Ela pode assumir diferentes formatos e finalidades, como:\n\n"
        "🔹 Holding Familiar: planejamento sucessório e proteção do patrimônio;\n"
        "🔹 Holding Rural: organização patrimonial no agronegócio;\n"
        "🔹 Holding Imobiliária: administração e proteção de imóveis.\n\n"
        f"Cada tipo exige análise personalizada. 📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    "holding familiar": (
        "A holding familiar protege o patrimônio da família, facilita a sucessão e reduz custos com inventário. "
        f"📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    "holding rural": (
        "A holding rural evita a fragmentação das terras, reduz impostos e protege o patrimônio agrícola. "
        f"📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    "holding imobiliária": (
        "A holding imobiliária centraliza a gestão de imóveis, reduz tributos e facilita a sucessão. "
        f"📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}"
    ),

    # Alias de redirecionamento
    "averbação": "regularização de imóveis",
    "usucapião": "regularização de imóveis",
    "imóvel irregular": "regularização de imóveis"
}

# === FUNÇÕES DE APOIO ===

def carregar_controle():
    if os.path.exists(ARQUIVO_CONTROLE):
        with open(ARQUIVO_CONTROLE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def fora_do_horario():
    agora = datetime.now()
    dia_semana = agora.strftime("%A").lower()
    return dia_semana not in DIAS_UTEIS or not (HORARIO_INICIO <= agora.hour < HORARIO_FIM)

def mensagem_é_para_grupo(nome_remetente):
    return any(g in nome_remetente.lower() for g in GRUPOS_BLOQUEADOS)

def contato_excluido(nome):
    return any(p in nome.lower() for p in CONTATOS_PESSOAIS)

# === ROTA PRINCIPAL ===

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

        print(f"[{datetime.now()}] 📥 Mensagem de {numero} ({nome}): {mensagem}")

        if mensagem_é_para_grupo(nome) or contato_excluido(nome):
            print("❌ Ignorado.")
            return jsonify({"status": "ignorado"})

        chave = mensagem.strip()
        if chave in PALAVRAS_CHAVE:
            resposta = PALAVRAS_CHAVE.get(PALAVRAS_CHAVE[chave], PALAVRAS_CHAVE[chave])
        else:
            resposta = gerar_resposta_gpt(mensagem)

        print(f"📤 Resposta enviada: {resposta}")
        return jsonify({"response": resposta})

    except Exception as e:
        print(f"❌ Erro: {repr(e)}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

# === GPT-4 (para dúvidas abertas) ===

def gerar_resposta_gpt(pergunta):
    prompt = f"""
Você é assistente jurídico do escritório Teixeira.Brito Advogados, liderado por Dayan. Especialista em contratos, sucessões, holding, renegociação de dívidas e regularização de imóveis.

Responda de forma clara, objetiva e com segurança jurídica. Finalize sempre com: 📌 Ligue para: {CONTATO_DIRETO} ou agende: {LINK_CALENDLY}

Pergunta: {pergunta}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    return response.choices[0].message["content"].strip()

# === ROTA DE SAÚDE ===

@app.route("/")
def home():
    return "🟢 Servidor ativo com inteligência jurídica personalizada para Dr. Dayan"
