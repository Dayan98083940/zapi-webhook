from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Token de segurança (recebido nos headers)
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "seu_token_aqui")

# Lista de contatos e grupos bloqueados
bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

# Carrega as respostas automáticas a partir do JSON
with open('blocos_respostas.json', encoding='utf-8') as f:
    blocos_respostas = json.load(f)

def detectar_resposta(msg):
    msg = msg.lower()
    for bloco in blocos_respostas:
        if bloco.get("trigger") and bloco["trigger"].lower() in msg:
            return bloco["response"]
        for palavra in bloco["keywords"]:
            if palavra.lower() in msg:
                return bloco["response"]
    return None

@app.route('/webhook', methods=['POST'])
def responder():
    # Verifica o token do header
    client_token = request.headers.get('Client-Token')
    if client_token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json

    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    mensagem = data.get("message", "")
    historico = data.get("messageCount", 1)

    # Bloqueios
    if nome in bloqueados or grupo in grupos_bloqueados:
        return jsonify({"response": None})

    # Só responde na primeira interação
    if historico > 1:
        return jsonify({"response": None})

    # Detecta e envia a resposta
    resposta = detectar_resposta(mensagem)
    return jsonify({"response": resposta}) if resposta else jsonify({"response": None})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
