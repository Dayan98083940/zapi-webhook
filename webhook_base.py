from flask import Flask, request, jsonify
import os
import openai

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

def detectar_assunto(msg):
    if msg:
        termos = ["contrato", "holding", "divórcio", "herança", "inventário", "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"]
        msg = msg.lower()
        for termo in termos:
            if termo in msg:
                return "profissional"
    return "particular"

def gerar_resposta_com_openai(pergunta):
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente jurídico educado e objetivo, representando o escritório Teixeira.Brito Advogados."},
                {"role": "user", "content": pergunta}
            ]
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        return "Desculpe, não consegui gerar uma resposta agora. Tente novamente mais tarde."

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

    if detectar_assunto(mensagem) == "profissional":
        resposta = gerar_resposta_com_openai(mensagem)
        return jsonify({"response": resposta})
    else:
        return jsonify({"response": None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
