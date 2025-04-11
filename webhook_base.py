@app.route("/webhook", methods=["POST"])
def responder():
    try:
        data = request.json or {}
        print("📩 JSON recebido:", data)

        mensagem = data.get("message", "").strip() \
            or data.get("text", {}).get("body", "") \
            or data.get("text", {}).get("message", "") \
            or data.get("image", {}).get("caption", "") \
            or ""

        telefone = data.get("participantPhone") or data.get("senderPhone") or data.get("phone") or ""
        nome = data.get("senderName", "")
        grupo = data.get("groupName", "")
        historico = data.get("messageCount", 0)

        if not mensagem or not telefone:
            print("⚠️ Dados incompletos. Ignorando.")
            return jsonify({"response": None})

        if telefone == os.getenv("NUMERO_INSTANCIA"):
            print("⛔ Ignorado: tentativa de responder ao próprio número.")
            return jsonify({"response": None})

        if nome in bloqueados or grupo in grupos_bloqueados:
            print(f"⛔ Ignorado: contato ou grupo bloqueado ({nome or grupo})")
            return jsonify({"response": None})

        if historico > 1:
            print("🔁 Ignorado: histórico de mensagens > 1")
            return jsonify({"response": None})

        tipo = detectar_assunto(mensagem)

        if tipo == "profissional":
            resposta = responder_com_bloco(mensagem) or gerar_resposta_gpt(mensagem)
            if resposta:
                enviar_zapi(telefone, resposta)
                return jsonify({"response": resposta})

        return jsonify({"response": None})

    except Exception as e:
        print("❌ Erro geral:", str(e))
        return jsonify({"error": "Erro interno"}), 500
