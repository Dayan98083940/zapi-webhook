from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

# A chave da API é lida da variável de ambiente
openai.api_key = os.getenv("OPENAI_API_KEY")

# Nomes e grupos bloqueados
bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

# Função para identificar se a mensagem tem palavras-chave profissionais
def detectar_assunto(msg):
    profissionais = ["contrato", "holding", "divórcio", "herança", "inventário", "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"]
    if msg:
        msg = msg.lower()
        for termo in profissionais:
            if termo in msg:
                return "profissional"
    return "particular"

# Rota principal do webhook
@app.route('/webhook', methods=['POST'])
def responder():
    data = request.get_json()

    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    mensagem = data.get("message", "")
    historico = data.get("messageCount", 0)

    if nome in bloqueados or grupo in grupos_bloqueados:
        return jsonify({"response": None})

    if historico and historico > 1:
        return jsonify({"response": None})

    tipo = detectar_assunto(mensagem)

    # Se for particular, não responde
    if tipo == "particular":
        return jsonify({"response": None})

    # Se for profissional, usa OpenAI para gerar resposta
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # ou gpt-4, se preferir
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico amigável e eficiente, que oferece respostas iniciais e convida para atendimento especializado."},
                {"role": "user", "content": mensagem}
            ],
            temperature=0.7,
            max_tokens=200
        )

        resposta = completion.choices[0].message.content.strip()
        return jsonify({"response": resposta})

    except Exception as e:
        print(f"Erro com OpenAI: {str(e)}")
        return jsonify({"response": "Tivemos um erro ao tentar responder. Por favor, tente novamente em instantes."})

# Inicializa o servidor
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
