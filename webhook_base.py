from flask import Flask, request, jsonify
import os
import openai

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

@app.route("/webhook", methods=["POST"])
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

    try:
        resposta = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico do escritório Teixeira Brito Advogados. Responda de forma clara e objetiva."},
                {"role": "user", "content": mensagem}
            ]
        )
        conteudo = resposta.choices[0].message.content
        return jsonify({"response": conteudo})

    except Exception as e:
        return jsonify({"response": f"Ocorreu um erro: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
