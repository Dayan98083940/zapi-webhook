INSTRUÇÕES DE CONFIGURAÇÃO Z-API - DAYAN BRITO

1. OBJETIVO:
Automatizar o WhatsApp Business apenas para atendimentos profissionais, sem interferir em assuntos pessoais.
Respostas automáticas devem acontecer apenas se:
- A mensagem for a primeira interação.
- O assunto for identificado como profissional.
- Não houver engajamento direto com você ainda.

2. TÓPICOS PROFISSIONAIS (Palavras-chave detectadas):
- holding, contrato, divórcio, inventário, processo, renegociação, dívida, judicial, empresa, regularização, consulta, advogado, atendimento, herança, usucapião, etc.

3. TÓPICOS PARTICULARES (Ignorar):
- Bom dia, boa noite, emojis, vídeos, fotos, palavras como: amém, parabéns, rsrs, família, etc.
- Conversas em andamento com cliente: IA não responde mais após interação inicial.

4. COMO FUNCIONA:
- A IA detecta palavras-chave e responde uma única vez.
- Se o cliente continuar a conversa, você assume.
- Contatos e grupos bloqueados (sem resposta): "Amor", "Pai", "João Manoel", "Pedro Dávila", "Providência Santa", "Sagrada Família".

5. IMPORTANTE:
- Este sistema pode ser expandido com integração ao seu CRM ou Google Agenda.
- Respostas estão no arquivo: blocos_respostas.json
- Lógica do webhook pronta em: webhook_base.py

