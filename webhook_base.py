from flask import Flask, request, jsonify

app = Flask(__name__)

bloqueados = ["Amor", "João Manoel", "Pedro Dávila", "Pai", "Mab", "Helder", "Érika", "Felipe"]
grupos_bloqueados = ["Sagrada Família", "Providência Santa"]

def detectar_assunto(msg):
    profissionais = ["contrato", "holding", "divórcio", "herança", "inventário", "processo", "consulta", "renegociação", "empresa", "advogado", "atendimento"]
    msg = msg.lower()
    for termo in profissionais:
        if termo in msg:
            return "profissional"
    return "particular"

@app.route('/webhook', methods=['POST'])
def responder():
    data = request.json
    nome = data.get("senderName")
    grupo = data.get("groupName")
    mensagem = data.get("message")
    historico = data.get("messageCount")

    if nome in bloqueados or grupo in grupos_bloqueados:
        return jsonify({"response": None})

    if historico > 1:
        return jsonify({"response": None})

    tipo = detectar_assunto(mensagem)
    if tipo == "profissional":
        if "atendimento" in mensagem or "consulta" in mensagem:
            resposta = "Oi! Claro que podemos te atender. Você prefere presencial ou online? Me diz o melhor horário que verifico a agenda. 😉"
        elif "processo" in mensagem:
            resposta = "Vamos verificar com nossa equipe jurídica e te dar um retorno completo. Você prefere que liguemos ou prefere agendar um horário presencial?"
        elif "holding" in mensagem or "contrato" in mensagem:
            resposta = "Posso te orientar com base na legislação, sim. Mas cada caso é único. Quer que eu mande um material ou agendamos uma conversa com um especialista?"
        else:
            resposta = "Podemos sim te ajudar com isso. Você prefere conversar por aqui ou quer agendar um atendimento?"
        return jsonify({"response": resposta})
    else:
        return jsonify({"response": None})

if __name__ == '__main__':
import os
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


