from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

def detectar_assunto(msg):
    profissionais = ["contrato", "holding", "divórcio", "herança", "inventário", "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"]
    if msg:
        msg = msg.lower()
        for termo in profissionais:
            if termo in msg:
                return "profissional"
    return "particular"

def gerar_resposta_chatgpt(mensagem):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico simpático, objetivo e informativo."},
                {"role": "user", "content": mensagem}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Desculpe, tivemos um erro ao gerar resposta."

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

    if tipo == "profissional":
        resposta = gerar_resposta_chatgpt(mensagem)
        return jsonify({"response": resposta})
    else:
        return jsonify({"response": None})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
