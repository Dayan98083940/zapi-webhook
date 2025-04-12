from fpdf import FPDF
from datetime import datetime
from threading import Timer

# Variáveis globais de armazenamento de interações
interacoes_hoje = []

# Número atualizado para envio do relatório (esposa)
NUMERO_RELATORIO = "5562998393940"  # +55 62 99839-3940

def registrar_interacao(nome, telefone, mensagem, aguardando_resposta=False):
    interacoes_hoje.append({
        "nome": nome,
        "telefone": telefone,
        "mensagem": mensagem,
        "pendente": aguardando_resposta
    })

def gerar_pdf_relatorio():
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="📋 Relatório de Atendimentos - Diário", ln=True, align="C")
        pdf.ln(10)

        if not interacoes_hoje:
            pdf.cell(200, 10, txt="Nenhuma interação registrada hoje.", ln=True)
        else:
            for idx, i in enumerate(interacoes_hoje, start=1):
                pendente = "✅ Respondido" if not i["pendente"] else "⏳ Aguardando retorno"
                pdf.multi_cell(0, 10, txt=f"{idx}. Nome: {i['nome']}\nTelefone: {i['telefone']}\nMensagem: {i['mensagem']}\nStatus: {pendente}")
                pdf.ln(5)

        nome_arquivo = f"relatorio_{datetime.now().strftime('%d-%m-%Y')}.pdf"
        caminho = os.path.join("/tmp", nome_arquivo)
        pdf.output(caminho)

        return caminho
    except Exception as e:
        print("❌ Erro ao gerar relatório PDF:", str(e))
        return None

def enviar_relatorio_diario():
    caminho_pdf = gerar_pdf_relatorio()
    if not caminho_pdf:
        return

    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/send-file"
    files = {'file': open(caminho_pdf, 'rb')}
    data = {
        "phone": NUMERO_RELATORIO,
        "message": f"📄 Relatório diário de atendimentos {datetime.now().strftime('%d/%m/%Y')}"
    }
    headers = {
        "Client-Token": ZAPI_TOKEN
    }
    try:
        response = requests.post(url, files=files, data=data, headers=headers)
        print(f"📤 Relatório enviado para {NUMERO_RELATORIO} | Status: {response.status_code}")
    except Exception as e:
        print("❌ Erro ao enviar relatório:", str(e))

# Agendamento diário (ex: 22h)
def agendar_envio_diario():
    now = datetime.now()
    hora_envio = now.replace(hour=22, minute=0, second=0, microsecond=0)
    if now > hora_envio:
        hora_envio = hora_envio.replace(day=now.day + 1)
    delay = (hora_envio - now).total_seconds()
    Timer(delay, executar_rotina_diaria).start()

def executar_rotina_diaria():
    enviar_relatorio_diario()
    interacoes_hoje.clear()
    agendar_envio_diario()

# Iniciar agendamento ao rodar app
agendar_envio_diario()
