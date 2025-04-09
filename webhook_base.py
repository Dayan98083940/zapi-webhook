from flask import Flask, request, jsonify
import os
import openai

app = Flask(__name__)

# 🔐 Sua chave da OpenAI
openai.api_key = "sk-...sua-chave-aqui..."

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
        # 🔁 Chamar a OpenAI para responder
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um assistente jurídico simpático e eficiente."},
                    {"role": "user", "content": mensagem}
                ]
            )
            resposta = completion.choices[0].message.content
        except Exception as e:
            resposta = "Desculpe, houve um erro ao processar sua solicitação. Tente novamente mais tarde."

        return jsonify({"response": resposta
