from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Horário comercial
HORARIOS = {
    "manha_inicio": 8,
    "manha_fim": 12,
    "tarde_inicio": 14,
    "tarde_fim": 18
}

# Endereço presencial fixo
ENDERECO = "Avenida C-5, Quadra 8, Lote 8, nº 504, Jardim América, Goiânia/GO, CEP 74265-050"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    mensagem = data.get("message", "").lower()
    nome = data.get("senderName", "Cliente")

    # Verifica se está fora do horário comercial
    agora = datetime.now()
    hora = agora.hour
    fora_do_horario = not (
        (HORARIOS["manha_inicio"] <= hora < HORARIOS["manha_fim"]) or
        (HORARIOS["tarde_inicio"] <= hora < HORARIOS["tarde_fim"])
    )

    if "quero agendar" in mensagem or "preciso marcar" in mensagem or "quero marcar" in mensagem:
        if fora_do_horario:
            resposta = f"Olá, {nome}! Atendemos em horário comercial (08h–12h / 14h–18h). Posso registrar seu pedido e te retornamos no primeiro horário disponível amanhã."
        else:
            resposta = (
                f"Olá, {nome}! O Dr. Dayan realiza atendimentos virtuais e presenciais.\n"
                "Você prefere **virtual** (via Microsoft Teams) ou **presencial** (em nosso escritório)?"
            )
        return jsonify({"response": resposta})

    if "virtual" in mensagem:
        return jsonify({
            "response": (
                "Perfeito! Você pode escolher o melhor horário disponível para atendimento virtual através do link abaixo:\n"
                "👉 https://calendly.com/daan-advgoias\n\n"
                "O atendimento será feito via Microsoft Teams."
            )
        })

    if "presencial" in mensagem or "no escritório" in mensagem:
        return jsonify({
            "response": (
                f"Claro! O atendimento presencial será no nosso escritório localizado em:\n"
                f"{ENDERECO}\n\n"
                "Você pode sugerir o melhor horário dentro do expediente (08h–12h / 14h–18h) e confirmaremos em seguida."
            )
        })

    # Resposta padrão (placeholder)
    return jsonify({"response": "Recebido! Já estou processando sua mensagem. Em instantes você terá um retorno."})

if __name__ == '__main__':
    app.run()
