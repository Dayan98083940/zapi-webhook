from flask import Flask, request, jsonify
from datetime import datetime
import requests
import fitz  # PyMuPDF
import openai
import os

app = Flask(__name__)

# 🔐 Configure sua chave da OpenAI via variável de ambiente ou diretamente aqui
openai.api_key = os.getenv("OPENAI_API_KEY") or "SUA_CHAVE_OPENAI_AQUI"

# 📅 Horário comercial
HORARIOS = {
    "manha_inicio": 8,
    "manha_fim": 12,
    "tarde_inicio": 14,
    "tarde_fim": 18
}

# 📍 Endereço e Calendly
ENDERECO = "Avenida C-5, Quadra 8, Lote 8, nº 504, Jardim América, Goiânia/GO, CEP 74265-050"
LINK_CALENDLY = "https://calendly.com/daan-advgoias"

# 🔍 Função de horário
def horario_comercial():
    agora = datetime.now()
    hora = agora.hour
    return (
        HORARIOS["manha_inicio"] <= hora < HORARIOS["manha_fim"]
        or HORARIOS["tarde_inicio"] <= hora < HORARIOS["tarde_fim"]
    )

# 📥 Extrair texto de PDF
def extrair_texto_pdf(url_arquivo):
    response = requests.get(url_arquivo)
    with open("temp.pdf", "wb") as f:
        f.write(response.content)
    doc = fitz.open("temp.pdf")
    texto = ""
    for page in doc:
        texto += page.get_text()
    doc.close()
    return texto

# 🧠 Gerar resumo técnico com IA
def gerar_resumo_conteudo(texto, tipo="contrato"):
    prompt_base = {
        "contrato": "Você é um advogado especialista. Leia o contrato abaixo e gere um resumo técnico, destacando riscos jurídicos, cláusulas sensíveis e pontos que exigem atenção. Seja direto, sem linguagem genérica.",
        "processo": "Você é um advogado especialista. Leia o processo abaixo e gere um resumo técnico, identificando a fase, pontos críticos e próximos passos."
    }
    prompt = prompt_base[tipo] + f"\n\nTexto:\n{texto}"

    resposta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800
    )
    return resposta.choices[0].message.content.strip()

# 🧩 Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("🔍 JSON recebido:", data)

    mensagem = data.get("message", "").lower()
    nome = data.get("senderName", "Cliente")
    
    # 📎 Detectar se tem anexo PDF
    anexo_url = None
    if "media" in data and isinstance(data["media"], list) and data["media"]:
        anexo_url = data["media"][0].get("url")

    # 🗓️ Agendamento
    if any(p in mensagem for p in ["quero agendar", "quero marcar", "preciso marcar", "agendar reunião"]):
        if not horario_comercial():
            resposta = f"Olá, {nome}! Atendemos em horário comercial (08h–12h / 14h–18h). Posso registrar sua solicitação e te retornar no primeiro horário disponível."
        else:
            resposta = (
                f"Olá, {nome}! O Dr. Dayan realiza atendimentos virtuais (Microsoft Teams) e presenciais.\n"
                f"Você prefere **virtual** ou **presencial**?"
            )
        return jsonify({"response": resposta})

    if "virtual" in mensagem:
        return jsonify({
            "response": (
                f"Perfeito! Você pode escolher o melhor horário para atendimento virtual com o Dr. Dayan aqui:\n"
                f"👉 {LINK_CALENDLY}\n\n"
                "A reunião será feita pelo Microsoft Teams."
            )
        })

    if "presencial" in mensagem:
        return jsonify({
            "response": (
                f"Claro! Nosso endereço é:\n{ENDERECO}\n\n"
                "Por favor, informe o melhor dia e horário (entre 08h–12h ou 14h–18h) para verificarmos disponibilidade."
            )
        })

    # 📄 Análise de Contrato / Processo
    if any(p in mensagem for p in [
        "analisa esse contrato", "analise esse contrato", "analisar contrato",
        "dá uma olhada nesse contrato", "analisa esse processo", "analise esse processo"
    ]):
        if anexo_url:
            tipo = "contrato" if "contrato" in mensagem else "processo"
            try:
                texto = extrair_texto_pdf(anexo_url)
                resumo = gerar_resumo_conteudo(texto, tipo)
                resposta = (
                    f"📄 **Resumo preliminar do {tipo} enviado:**\n\n"
                    f"{resumo}\n\n"
                    f"Se quiser seguir com análise completa ou providências, posso agendar uma conversa com o Dr. Dayan. Deseja agendar agora?"
                )
            except Exception as e:
                resposta = f"Ocorreu um erro ao tentar analisar o documento: {str(e)}"
        else:
            resposta = (
                "Parece que você mencionou análise de contrato ou processo, mas não enviou o arquivo. "
                "Pode mandar em PDF que farei a análise preliminar para você."
            )
        return jsonify({"response": resposta})

    # 🧾 Resposta padrão
    return jsonify({"response": "Recebido! Já estou processando sua mensagem. Em breve você terá um retorno do Dr. Dayan ou de nossa equipe."})

# 🔄 Executar localmente
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
