from flask import Flask, request, jsonify
import os
import json
import openai
import requests
from datetime import datetime, date

app = Flask(__name__)

# === CONFIGURAÇÕES ===
openai.api_key = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL_TOKEN = os.getenv("WEBHOOK_TOKEN")
EXPECTED_CLIENT_TOKEN = "F124e80fa9ba94101a6eb723b5a20d2b3S"

ZAPI_INSTANCE_URL = "https://api.z-api.io/instances/3DF715E26F0310B41D118E66062CE0C1"
ZAPI_TOKEN = "6148D6FDA5C0D66E63947D5B"

CONTATO_DIRETO = "+55(62)99808-3940"
CONTATO_FIXO = "(62) 3922-3940"
LINK_CALENDLY = "https://calendly.com/dayan-advgoias"

# === CONTROLES ===
BLOQUEAR_NUMEROS = os.getenv("BLOQUEADOS", "").split(",")
CONVERSAS = {}
ATENDIMENTO_MANUAL = {}  # {"556299999999": "2024-04-14"}

GATILHOS_RESPOSTA = [
    "quero", "gostaria", "preciso", "tenho uma dúvida",
    "como faço", "o que fazer", "qual o procedimento",
    "poderia me orientar", "ajuda", "tem como", "posso",
    "informação", "processo", "agendar", "consulta", "atendimento"
]

SAUDACOES = ["bom dia", "boa tarde", "boa noite", "olá", "ola", "oi"]

def gerar_saudacao():
    hora = datetime.now().hour
    return "Bom dia
