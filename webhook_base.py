from flask import Flask, request, jsonify
import os
import openai
import requests
from datetime import datetime, date
import re

app = Flask(__name__)

# === CONFIGURAÇÕES PRINCIPAIS ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuração Z-API
ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "")  # Token para uso em cabeçalhos de envio

# Informações de contato
CONTATO_DIRETO = "+55(62)99808-3940"
CONTATO_FIXO = "(62) 3922-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# Armazenamento de conversa e estados
CONVERSAS = {}  # Histórico de mensagens por número
ATENDIMENTO_MANUAL = {}  # Números marcados para atendimento humano
ESTADO_CONVERSA = {}  # Para controlar o estado da conversa com cada cliente
NOMES_CLIENTES = {}  # Para armazenar o nome do cliente por número

# Estados da conversa
ESTADO_INICIAL = 0       # Primeira interação - Saudação e pedir nome
ESTADO_ESPERA_NOME = 1   # Esperando o cliente informar o nome
ESTADO_ESPERA_DUVIDA = 2 # Esperando o cliente informar sua dúvida
ESTADO_ATENDIMENTO = 3   # Fornecendo resposta à dúvida

# Gatilhos para resposta automática
GATILHOS_RESPOSTA = [
    "quero", "gostaria", "preciso", "dúvida", "processo",
    "como faço", "o que fazer", "procedimento",
    "orientação", "ajuda", "tem como", "posso", "informação", "reunião", "agendamento"
]

# Saudações que também ativam respostas
SAUDACOES = ["bom dia", "boa tarde", "boa noite", "olá", "oi", "alô", "ola", "ei"]

# === FUNÇÕES DE APOIO ===
def gerar_saudacao():
    """Gera uma saudação apropriada baseada na hora do dia."""
    hora = datetime.now().hour
    if hora < 12:
        return "Bom dia"
    elif hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

def formata_tratamento(nome):
    """Formata o tratamento para o cliente com base no nome."""
    if not nome or nome == "Cliente":
        return "Cliente"
    
    nome = nome.lower()
    if "advogado" in nome or "advogada" in nome:
        return f"Dr(a). {nome.split()[0].capitalize()}"
    return f"Sr(a). {nome.split()[0].capitalize()}"

def extrair_mensagem(data):
    """Extrai o texto da mensagem do JSON da Z-API, considerando os diferentes formatos possíveis."""
    try:
        # Verifica se é uma mensagem de texto
        if "text" in data and isinstance(data["text"], dict):
            return data["text"].get("message", "").strip()
        
        # Verifica se é uma imagem com legenda
        elif "image" in data and isinstance(data["image"], dict):
            return data["image"].get("caption", "").strip()
        
        # Verifica se é um documento com legenda
        elif "document" in data and isinstance(data["document"], dict):
            caption = data["document"].get("caption", "").strip()
            filename = data["document"].get("filename", "").strip()
            return f"[Documento: {filename}] {caption}"
        
        # Verifica se é uma reação (não contém texto)
        elif "reaction" in data:
            return ""
        
        # Tenta extrair mensagem do formato antigo
        elif "message" in data:
            if isinstance(data["message"], dict):
                return data["message"].get("text", "").strip()
            else:
                return str(data["message"]).strip()
                
        return ""
    except Exception as e:
        print(f"Erro ao extrair mensagem: {e}")
        return ""

def e_grupo(numero):
    """Verifica se o número é de um grupo."""
    return ("-group" in numero or 
            "g.us" in numero or 
            "group" in numero or
            numero.startswith("120363"))  # ID comum de grupos no WhatsApp

def deve_responder(mensagem, numero):
    """Determina se o bot deve responder à mensagem com base nas regras definidas."""
    # Regra 1: Nunca responder a grupos
    if e_grupo(numero):
        print(f"⛔ Mensagem de grupo ignorada: {numero}")
        return False
        
    # Regra 2: Não responder a números em atendimento manual hoje
    if numero in ATENDIMENTO_MANUAL and ATENDIMENTO_MANUAL[numero] == str(date.today()):
        print(f"⛔ Atendimento manual ativo para {numero}")
        return False
    
    # Regra 3: SEMPRE responder a mensagens de clientes individuais, EXCETO se for vazia
    if not mensagem.strip():
        print(f"⛔ Mensagem vazia ignorada: {numero}")
        return False
    
    # Regra 4: Se já existe uma conversa em andamento, sempre responder
    if numero in ESTADO_CONVERSA:
        return True
    
    # Regra 5: Sempre iniciar conversa com novos clientes (primeira mensagem)
    return True

def processar_documento(mensagem, numero):
    """Processa mensagens relacionadas a documentos."""
    if re.search(r'$$Documento:.+$$', mensagem):
        nome_cliente = NOMES_CLIENTES.get(numero, "Cliente")
        return (f"Obrigado pelo documento, {nome_cliente}. Infelizmente não consigo ler o conteúdo de arquivos diretamente. "
                f"Por favor, descreva brevemente do que se trata para que eu possa tentar ajudar, ou entre em contato diretamente "
                f"pelo telefone {CONTATO_DIRETO} para um atendimento mais detalhado.")
    return None

# === WEBHOOK PRINCIPAL ===
@app.route("/webhook/<token>/receive", methods=["POST"])
def receber_mensagem(token):
    print(f"Webhook acionado com token: {token}")
    print(f"Headers recebidos: {dict(request.headers)}")
    
    # Verificação de token na URL
    if token != ZAPI_TOKEN:
        print(f"❌ Token inválido na URL: {token} (esperado: {ZAPI_TOKEN})")
        return jsonify({"erro": "Token inválido na URL."}), 403

    # Verificar o token nos headers
    z_api_token = request.headers.get("Z-Api-Token")
    content_type = request.headers.get("Content-Type")
    print(f"🔍 Recebido — Z-Api-Token: {z_api_token}, Content-Type: {content_type}")

    if z_api_token != ZAPI_TOKEN or content_type != "application/json":
        print(f"❌ Headers inválidos. Z-Api-Token recebido: {z_api_token}, esperado: {ZAPI_TOKEN}")
        return jsonify({"erro": "Headers inválidos."}), 403

    try:
        data = request.json
        print(f"JSON recebido da Z-API: {data}")
        
        # Extrair dados da mensagem
        mensagem = extrair_mensagem(data)
        numero = data.get("phone", "")
        
        # Verificar se é um grupo e ignorar completamente
        if e_grupo(numero):
            print(f"⛔ Mensagem de grupo ignorada: {numero}")
            return jsonify({"status": "ignorado", "motivo": "grupo"})
        
        # Obter nome do remetente
        if "senderName" in data:
            nome_contato = data.get("senderName", "")
        elif "sender" in data and isinstance(data["sender"], dict):
            nome_contato = data["sender"].get("name", "")
        else:
            nome_contato = "Cliente"
            
        print(f"📥 Mensagem extraída: '{mensagem}', Número: '{numero}', Nome: '{nome_contato}'")

        # Verificar se deve responder
        if not deve_responder(mensagem, numero):
            print(f"📥 Mensagem ignorada: {mensagem}")
            return jsonify({"status": "ignorado"})

        # Verificar se é um documento
        resposta_documento = processar_documento(mensagem, numero)
        if resposta_documento:
            CONVERSAS.setdefault(numero, []).extend([f"Cliente: {mensagem}", f"Assistente: {resposta_documento}"])
            enviar_resposta_via_zapi(numero, resposta_documento)
            return jsonify({"status": "respondido", "para": numero, "resposta": resposta_documento})

        # Processar a mensagem de acordo com o estado da conversa
        resposta = processar_mensagem_por_estado(mensagem, numero, nome_contato)
        
        # Registrar na conversa
        CONVERSAS.setdefault(numero, []).extend([f"Cliente: {mensagem}", f"Assistente: {resposta}"])

        # Enviar resposta
        enviar_resposta_via_zapi(numero, resposta)
        return jsonify({"status": "respondido", "para": numero, "resposta": resposta})
    except Exception as e:
        print(f"❌ Erro ao processar requisição: {e}")
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

def processar_mensagem_por_estado(mensagem, numero, nome_contato):
    """Processa a mensagem com base no estado atual da conversa."""
    # Obter o estado atual da conversa ou definir como inicial
    estado_atual = ESTADO_CONVERSA.get(numero, ESTADO_INICIAL)
    saudacao = gerar_saudacao()
    
    print(f"📋 Processando mensagem no estado {estado_atual} para {numero}")
    
    # Verifica se é fora do horário comercial (8h às 18h)
    fora_do_horario = datetime.now().hour < 8 or datetime.now().hour >= 18
    if fora_do_horario:
        return (f"{saudacao}! Nosso atendimento é das 08h às 18h. "
                f"Por favor, agende seu atendimento pelo link: {LINK_CALENDLY}. "
                "Agradecemos a compreensão!")
    
    # Processar de acordo com o estado
    if estado_atual == ESTADO_INICIAL:
        # Primeira interação: Saudação e solicitar nome
        ESTADO_CONVERSA[numero] = ESTADO_ESPERA_NOME
        return (f"{saudacao}! Sou a IA do suporte da Teixeira Brito Advogados. "
                "Antes de começarmos o atendimento, poderia me dizer seu nome?"
               )
    
    elif estado_atual == ESTADO_ESPERA_NOME:
        # Cliente informou o nome, solicitar como podemos ajudar
        nome_cliente = mensagem.strip()
        # Armazenar o nome para futuras interações
        NOMES_CLIENTES[numero] = nome_cliente
        
        ESTADO_CONVERSA[numero] = ESTADO_ESPERA_DUVIDA
        return (f"Obrigado, {nome_cliente}! Como posso te ajudar hoje?")
    
    elif estado_atual == ESTADO_ESPERA_DUVIDA:
        # Cliente informou a dúvida, analisar e responder
        ESTADO_CONVERSA[numero] = ESTADO_ATENDIMENTO
        return analisar_duvida_cliente(mensagem, NOMES_CLIENTES.get(numero, "Cliente"))
    
    elif estado_atual == ESTADO_ATENDIMENTO:
        # Continuação da conversa após a resposta inicial
        return analisar_duvida_cliente(mensagem, NOMES_CLIENTES.get(numero, "Cliente"))
    
    # Fallback - não deveria chegar aqui
    return "Desculpe, houve um erro no processamento. Por favor, tente novamente mais tarde."

def analisar_duvida_cliente(mensagem, nome_cliente):
    """Analisa a dúvida do cliente e gera uma resposta adequada usando GPT."""
    
    # Verificar palavras-chave para documentos
    if "pdf" in mensagem.lower() or "word" in mensagem.lower() or "documento" in mensagem.lower() or "arquivo" in mensagem.lower():
        return (f"Olá {nome_cliente}, infelizmente não consigo ler ou processar arquivos PDF ou Word diretamente. "
                f"Por favor, descreva o conteúdo ou sua dúvida em texto para que eu possa ajudar. "
                f"Para análise de documentos complexos, recomendo agendar um atendimento pelo link: {LINK_CALENDLY}.")
                
    # Preparar o prompt para o GPT
    prompt = f"""
    Você é um assistente jurídico educado, cordial e objetivo do escritório Teixeira Brito Advogados.
    
    Mensagem do cliente: "{mensagem}"
    Nome do cliente: {nome_cliente}
    
    Analise a mensagem e siga estas diretrizes:
    
    1. Se for relacionado a um processo judicial existente:
       - Informe que será necessário um atendimento direto com nossa equipe
       - Oriente para entrar em contato pelo telefone ou agendar uma consulta
       - Não solicite detalhes específicos do processo
       
    2. Se for uma consulta jurídica geral:
       - Forneça orientações gerais e preliminares
       - Evite dar conselhos jurídicos específicos
       - Direcione para um atendimento pessoal se o caso for complexo
       
    3. Se for solicitação de agendamento:
       - Recomende o agendamento pelo link do Calendly: {LINK_CALENDLY}
       
    4. Se detectar uma situação urgente:
       - Oriente para entrar em contato imediatamente pelo telefone: {CONTATO_DIRETO}
       
    5. Priorize sempre o atendimento mais personalizado para casos mais complexos.
    
    Responda com empatia e linguagem acessível, finalizando sempre com uma orientação clara sobre os próximos passos.
    """

    try:
        # Tentar com a API mais recente
        try:
            response = openai.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            corpo = response.choices[0].message.content.strip()
        except AttributeError:
            # Fallback para o método antigo da API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400
            )
            corpo = response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"Erro OpenAI: {e}")
        corpo = (f"Olá {nome_cliente}, no momento não conseguimos processar sua consulta. "
                 f"Recomendamos que entre em contato diretamente pelo telefone {CONTATO_DIRETO} "
                 f"ou agende uma consulta em {LINK_CALENDLY}.")

    # Montar resposta final com assinatura e contatos
    return f"{corpo}\n\nPara agendar um atendimento com Dr. Dayan: {LINK_CALENDLY}\nTelefone: {CONTATO_FIXO} | Celular: {CONTATO_DIRETO}"

# === ENVIO Z-API ===
def enviar_resposta_via_zapi(telefone, mensagem):
    """Envia resposta para o WhatsApp via Z-API."""
    if e_grupo(telefone) or not mensagem.strip():
        print(f"🚫 Mensagem bloqueada para grupo ou vazia: {telefone}")
        return

    # Formatação do número de telefone
    telefone_formatado = telefone
    if not telefone.startswith("55") and telefone.startswith("+"):
        # Remove caracteres não numéricos
        telefone_formatado = ''.join(filter(str.isdigit, telefone))

    url = f"{ZAPI_INSTANCE_URL}/token/{ZAPI_TOKEN}/send-text"
    
    # Headers conforme especificação da Z-API
    headers = {
        "Content-Type": "application/json",
        "Client-token": CLIENT_TOKEN
    }
    
    payload = {"phone": telefone_formatado, "message": mensagem}
    
    print(f"Enviando para Z-API - URL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"📤 Enviado com sucesso para {telefone}, Status: {response.status_code}")
        else:
            print(f"❌ Erro ao enviar: Status {response.status_code}, Resposta: {response.text}")
    except Exception as e:
        print(f"❌ Falha ao enviar via Z-API: {e}")

# === ROTAS AUXILIARES ===
@app.route("/atendimento-manual", methods=["POST"])
def atendimento_manual():
    """Marca um número para atendimento manual (válido apenas para o dia atual)."""
    numero = request.json.get("numero", "").strip()
    if numero:
        ATENDIMENTO_MANUAL[numero] = str(date.today())
        return jsonify({"status": "registrado", "numero": numero})
    return jsonify({"erro": "Número inválido."}), 400

@app.route("/reset/<numero>", methods=["POST"])
def reset_conversa(numero):
    """Reseta o estado da conversa para um número específico."""
    if numero in ESTADO_CONVERSA:
        del ESTADO_CONVERSA[numero]
    if numero in CONVERSAS:
        CONVERSAS[numero] = []
    if numero in NOMES_CLIENTES:
        del NOMES_CLIENTES[numero]
    return jsonify({"status": "reset_ok", "numero": numero})

@app.route("/conversas/<numero>", methods=["GET"])
def conversa(numero):
    """Retorna o histórico de conversa para um número específico."""
    return jsonify({
        "numero": numero,
        "nome": NOMES_CLIENTES.get(numero, "Desconhecido"),
        "estado": ESTADO_CONVERSA.get(numero, 0),
        "historico": CONVERSAS.get(numero, ["Sem histórico."])
    })

@app.route("/estado/<numero>", methods=["GET"])
def estado(numero):
    """Retorna o estado atual da conversa para um número específico."""
    estado = ESTADO_CONVERSA.get(numero, ESTADO_INICIAL)
    estados = {
        0: "INICIAL",
        1: "ESPERA_NOME",
        2: "ESPERA_DUVIDA",
        3: "ATENDIMENTO"
    }
    return jsonify({
        "numero": numero,
        "nome": NOMES_CLIENTES.get(numero, "Desconhecido"),
        "estado": estado,
        "descricao": estados.get(estado, "DESCONHECIDO")
    })

@app.route("/debug", methods=["GET"])
def debug_info():
    """Retorna informações de debug sobre o estado atual do sistema."""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "horario_comercial": 8 <= datetime.now().hour < 18,
        "configurações": {
            "openai_key_definida": bool(openai.api_key),
            "zapi_configurada": bool(ZAPI_INSTANCE_URL and ZAPI_TOKEN),
            "client_token": bool(CLIENT_TOKEN),
        },
        "estatísticas": {
            "conversas_ativas": len(CONVERSAS),
            "clientes_identificados": len(NOMES_CLIENTES),
            "conversas_por_estado": {
                "inicial": len([k for k, v in ESTADO_CONVERSA.items() if v == ESTADO_INICIAL]),
                "espera_nome": len([k for k, v in ESTADO_CONVERSA.items() if v == ESTADO_ESPERA_NOME]),
                "espera_duvida": len([k for k, v in ESTADO_CONVERSA.items() if v == ESTADO_ESPERA_DUVIDA]),
                "atendimento": len([k for k, v in ESTADO_CONVERSA.items() if v == ESTADO_ATENDIMENTO])
            },
            "atendimentos_manuais": len(ATENDIMENTO_MANUAL)
        }
    })

@app.route("/test", methods=["POST"])
def test_endpoint():
    """Endpoint de teste para simulação de mensagens sem usar a Z-API."""
    try:
        data = request.json
        print(f"Dados de teste recebidos: {data}")
        
        mensagem = data.get("message", "Olá, preciso de uma informação.")
        numero = data.get("phone", "5562998083940")
        nome = data.get("name", "Cliente Teste")
        
        # Forçar estado específico para teste (opcional)
        if "estado" in data:
            ESTADO_CONVERSA[numero] = data["estado"]
        
        if "nome" in data:
            NOMES_CLIENTES[numero] = data["nome"]
            
        # Simula verificação de grupo
        if e_grupo(numero):
            return jsonify({
                "status": "teste_grupo",
                "resposta": "Esta é uma mensagem de grupo e seria ignorada"
            })
        
        # Verifica se deve responder
        if not deve_responder(mensagem, numero):
            resposta = "[TESTE] Esta mensagem não ativaria uma resposta automática."
        else:
            # Verificar se é um documento
            resposta_documento = processar_documento(mensagem, numero)
            if resposta_documento:
                resposta = resposta_documento
            else:
                # Processar normalmente
                resposta = processar_mensagem_por_estado(mensagem, numero, nome)
            
        print(f"Resposta gerada: {resposta}")
        
        return jsonify({
            "status": "teste_ok",
            "mensagem_recebida": mensagem,
            "resposta_gerada": resposta,
            "responderia": deve_responder(mensagem, numero),
            "estado_atual": ESTADO_CONVERSA.get(numero, ESTADO_INICIAL),
            "nome_registrado": NOMES_CLIENTES.get(numero, "Não registrado")
        })
    except Exception as e:
        return jsonify({"erro": str(e)})

@app.route("/")
def home():
    """Página inicial que confirma que o serviço está em execução."""
    return "🟢 Whats TB rodando — Atendimento Automatizado Teixeira Brito Advogados"

# === RUN LOCAL ===
if __name__ == "__main__":
    # Verificação de configurações na inicialização
    print("=== INICIANDO SERVIDOR ===")
    print(f"OpenAI API Key: {'Configurada' if openai.api_key else 'NÃO CONFIGURADA'}")
    print(f"Z-API Token: {ZAPI_TOKEN}")
    print(f"Client Token: {'Configurado' if CLIENT_TOKEN else 'NÃO CONFIGURADO'}")
    print("Lista de gatilhos de resposta:")
    for gatilho in GATILHOS_RESPOSTA:
        print(f"  - {gatilho}")
    print("=== CONFIGURAÇÃO CONCLUÍDA ===")
    
    app.run(host='0.0.0.0', port=10000)
