from flask import Flask, request
import requests
import os
import json
import re
from datetime import datetime

app = Flask(__name__)

@app.route("/twilio-webhook", methods=["POST"])
def receber_mensagem():
    mensagem = request.form.get("Body")
    telefone = request.form.get("From")

    print(f"📨 Nova mensagem de {telefone}: {mensagem}")

    nome_lead = f"Lead WhatsApp {telefone.replace('whatsapp:', '').strip()}"
    codigo_imovel = extrair_codigo_imovel(mensagem)

    cadastrar_lead_no_vista(telefone, mensagem, nome_lead, codigo_imovel)
    enviar_mensagem_confirmacao(telefone, nome_lead)

    return "Mensagem recebida com sucesso", 200

def cadastrar_lead_no_vista(telefone, mensagem, nome, codigo=None):
    url = "http://fabianal-rest.vistahost.com.br/lead?key=1c0de57a8bef6c682ab91c949ec29506"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    telefone_limpo = telefone.replace("whatsapp:", "").strip()

    lead_data = {
        "lead": {
            "nome": nome,
            "fone": telefone_limpo,
            "mensagem": mensagem,
            "veiculo": "Instagram",
            "interesse": "venda"
        }
    }

    if codigo:
        lead_data["lead"]["anuncio"] = codigo

    payload = {
        "cadastro": json.dumps(lead_data)
    }

    response = requests.post(url, data=payload, headers=headers)

    if response.status_code == 200:
        print("✅ Lead enviado ao Vista Soft.")
        print(response.text)
    else:
        print(f"❌ Erro ao cadastrar lead: {response.status_code} - {response.text}")

def extrair_codigo_imovel(texto):
    padrao = r"c[oó]digo\s*(\d+)"
    match = re.search(padrao, texto, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def enviar_mensagem_confirmacao(telefone, nome):
    account_sid = os.environ.get("TWILIO_SID")
    auth_token = os.environ.get("TWILIO_TOKEN")
    from_whatsapp = os.environ.get("TWILIO_NUMBER")

    saudacao = gerar_saudacao()
    mensagem = f"{saudacao}, {nome}! 😃\n\nBem-vindo(a) à 📲 www.FabianaLouzadaimoveis.com.br\nNossa corretora de imóveis irá te chamar com mais detalhes em breve."

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    payload = {
        "To": telefone,
        "From": f"whatsapp:{from_whatsapp}",
        "Body": mensagem
    }

    response = requests.post(url, data=payload, auth=(account_sid, auth_token))

    if response.status_code in [200, 201]:
        print("✅ Mensagem de confirmação enviada ao lead.")
    else:
        print(f"❌ Erro ao enviar mensagem: {response.status_code} - {response.text}")

def gerar_saudacao():
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia"
    elif 12 <= hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
