from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Tokens de segurança
EXPECTED_CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "seu_token_aqui")

# Bloqueios
bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

# Carregar respostas do JSON
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
    # Verifica token no header
    client_token = request.headers.get('Client-Token')
    if client_token != EXPECTED_CLIENT_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    nome = data.get("senderName", "")
    grupo = data.get("groupName", "")
    mensagem = data.get("message", "")
    historico = data.get("messageCount", 1)

    if nome in bloqueados or grupo in grupos_bloqueados:
        return jsonify({"response": None})

    if historico > 1:
        return jsonify({"response": None})

    resposta = detectar_resposta(mensagem)
    if resposta:
        return jsonify({"response": resposta})
    return jsonify({"response": None})

if __name__ == '__main__':
    app.run(port=5000)
