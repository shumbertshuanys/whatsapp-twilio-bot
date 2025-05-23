from flask import Flask, request
import requests
import os
import json
import re
from datetime import datetime
import sqlite3
from datetime import timedelta

app = Flask(__name__)

@app.route("/twilio-webhook", methods=["POST"])
def receber_mensagem():
    print("🔍 Dados recebidos no webhook:", flush=True)
    print(request.form, flush=True)

    mensagem = request.form.get("Body")
    telefone = request.form.get("From")
    nome_wa = request.form.get("ProfileName")

    nome_lead = nome_wa if nome_wa else f"Lead WhatsApp {telefone.replace('whatsapp:', '').strip()}"
    codigo_imovel = extrair_codigo_imovel(mensagem)

    print(f"📨 Nova mensagem de {telefone}: {mensagem}", flush=True)
    print(f"👤 Nome detectado: {nome_lead}", flush=True)

    cadastrar_lead_no_vista(telefone, mensagem, nome_lead, codigo_imovel)
    
    if deve_responder(telefone):
        registrar_resposta(telefone)
        enviar_mensagem_confirmacao(telefone, nome_lead)
    else:
        print("⏱️ Resposta automática não enviada (intervalo de 2h ainda não passou).", flush=True)


    return "Mensagem recebida com sucesso", 200

def cadastrar_lead_no_vista(telefone, mensagem, nome, codigo=None):
    url = "http://fabianal-rest.vistahost.com.br/lead?key=1c0de57a8bef6c682ab91c949ec29506"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    telefone_limpo = telefone.replace("whatsapp:", "").strip()

    lead_data = {
        "lead": {
            "nome": nome,
            "fone": telefone_limpo,
            "mensagem": mensagem,
            "veiculo": "Instagram",
            "interesse": "venda",
            "corretor": 2
        }
    }

    if codigo:
        lead_data["lead"]["anuncio"] = codigo

    payload = {
        "cadastro": json.dumps(lead_data)
    }

    response = requests.post(url, data=payload, headers=headers)

    print("📤 Enviando lead ao Vista Soft:", flush=True)
    print(json.dumps(lead_data, indent=2, ensure_ascii=False), flush=True)

    if response.status_code == 200:
        print("✅ Vista Soft respondeu com sucesso:", flush=True)
        print(response.text, flush=True)
        registrar_envio_vista(telefone_limpo, nome, mensagem, codigo, response.text)

    elif response.status_code == 400 and "já existe" in response.text:
        print("ℹ️ Cliente já cadastrado. Tentando lançar histórico...", flush=True)
        registrar_envio_vista(telefone_limpo, nome, mensagem, codigo, response.text)
        try:
            resposta_json = response.json()
            codigo_cliente = resposta_json["message"][1]["Cliente_codigo"]
            if codigo and codigo_cliente:
                lançar_historico_cliente(codigo_cliente, codigo, mensagem)
        except Exception as e:
            print("⚠️ Erro ao interpretar resposta de cliente já existente:", flush=True)
            print(e, flush=True)
            print(response.text, flush=True)
    else:
        print(f"❌ Erro ao cadastrar lead: {response.status_code}", flush=True)
        print(response.text, flush=True)
        registrar_envio_vista(telefone_limpo, nome, mensagem, codigo, response.text)

def lançar_historico_cliente(codigo_cliente, codigo_imovel, mensagem):
    url = "http://fabianal-rest.vistahost.com.br/clientes/detalhes?key=1c0de57a8bef6c682ab91c949ec29506"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    historico_data = {
        "fields": {
            "Cliente": codigo_cliente,
            "Historico": {
                "Assunto": "Lead do Instagram",
                "Imovel": codigo_imovel,
                "Texto": mensagem
            }
        }
    }

    payload = {
        "cadastro": json.dumps(historico_data)
    }

    response = requests.post(url, data=payload, headers=headers)

    print("📝 Lançando histórico no cliente existente:", flush=True)
    print(json.dumps(historico_data, indent=2, ensure_ascii=False), flush=True)

    if response.status_code == 200:
        print("✅ Histórico lançado com sucesso.", flush=True)
    else:
        print(f"❌ Erro ao lançar histórico: {response.status_code}", flush=True)
        print(response.text, flush=True)

def extrair_codigo_imovel(texto):
    padrao = r"c[oó]digo\s*(\d+)"
    match = re.search(padrao, texto, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

import os
import requests
from pytz import timezone

def enviar_mensagem_confirmacao(telefone, nome):
    account_sid = os.environ.get("TWILIO_SID")
    auth_token = os.environ.get("TWILIO_TOKEN")
    from_whatsapp = os.environ.get("TWILIO_NUMBER")

    saudacao = gerar_saudacao()
    mensagem = (
        f"{saudacao}, {nome}! 😃\n\n"
        "Bem-vindo(a) à 📲 *Fabiana Louzada Imóveis*\n"
        "Nosso corretor de imóveis irá te chamar com mais detalhes em breve.\n"
        "🌐 https://www.fabianalouzadaimoveis.com.br"
    )

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = {
        "To": telefone,
        "From": f"whatsapp:{from_whatsapp}",
        "Body": mensagem
    }

    try:
        response = requests.post(url, data=payload, auth=(account_sid, auth_token))
        if response.status_code in [200, 201]:
            print("✅ Mensagem de confirmação enviada ao lead.", flush=True)
        else:
            print(f"❌ Erro ao enviar mensagem ({response.status_code}): {response.text}", flush=True)
    except requests.exceptions.RequestException as e:
        print("❌ Falha ao tentar enviar mensagem via API do Twilio:", flush=True)
        print(str(e), flush=True)
    except Exception as e:
        print("❌ Erro inesperado ao enviar mensagem de confirmação:", flush=True)
        print(str(e), flush=True)

from pytz import timezone

def gerar_saudacao():
    fuso_brasil = timezone("America/Sao_Paulo")
    hora = datetime.now(fuso_brasil).hour
    if 5 <= hora < 12:
        return "Bom dia"
    elif 12 <= hora < 18:
        return "Boa tarde"
    else:
        return "Boa noite"

def deve_responder(telefone):
    try:
        conn = sqlite3.connect("respostas.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS respostas (
                telefone TEXT PRIMARY KEY,
                ultima_resposta DATETIME
            )
        """)
        cursor.execute("SELECT ultima_resposta FROM respostas WHERE telefone = ?", (telefone,))
        row = cursor.fetchone()

        fuso_brasil = timezone("America/Sao_Paulo")
        agora = datetime.now(fuso_brasil)

        if row:
            ultima_resposta = datetime.fromisoformat(row[0])
            if agora - ultima_resposta < timedelta(hours=2):
                return False

        return True
    finally:
        conn.close()

def registrar_resposta(telefone):
    conn = sqlite3.connect("respostas.db")
    cursor = conn.cursor()
    fuso_brasil = timezone("America/Sao_Paulo")
    agora = datetime.now(fuso_brasil).isoformat()
    cursor.execute("REPLACE INTO respostas (telefone, ultima_resposta) VALUES (?, ?)", (telefone, agora))
    conn.commit()
    conn.close()

def registrar_envio_vista(telefone, nome, mensagem, codigo_imovel, resposta_crm):
    try:
        conn = sqlite3.connect("envios.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS envios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefone TEXT,
                nome TEXT,
                mensagem TEXT,
                codigo_imovel INTEGER,
                resposta_crm TEXT,
                data_envio DATETIME
            )
        """)
        agora = datetime.now(timezone("America/Sao_Paulo")).isoformat()
        cursor.execute("""
            INSERT INTO envios (telefone, nome, mensagem, codigo_imovel, resposta_crm, data_envio)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (telefone, nome, mensagem, codigo_imovel, resposta_crm, agora))
        conn.commit()
    finally:
        conn.close()

@app.route("/ping", methods=["GET"])
def ping():
    return "🏓 Bot ativo", 200

from flask import Response
import csv
from io import StringIO

@app.route("/export-csv", methods=["GET"])
def export_csv():
    try:
        conn = sqlite3.connect("respostas.db")
        cursor = conn.cursor()
        cursor.execute("SELECT telefone, ultima_resposta FROM respostas ORDER BY ultima_resposta DESC")
        dados = cursor.fetchall()
        conn.close()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["telefone", "ultima_resposta"])
        writer.writerows(dados)
        output.seek(0)

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=relatorio_leads.csv"}
        )
    except Exception as e:
        return {"erro": str(e)}, 500

@app.route("/export-envios", methods=["GET"])
def export_envios():
    try:
        conn = sqlite3.connect("envios.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT telefone, nome, mensagem, codigo_imovel, resposta_crm, data_envio
            FROM envios
            ORDER BY data_envio DESC
        """)
        dados = cursor.fetchall()
        conn.close()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["telefone", "nome", "mensagem", "codigo_imovel", "resposta_crm", "data_envio"])
        writer.writerows(dados)
        output.seek(0)

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=envios_crm.csv"}
        )
    except Exception as e:
        return {"erro": str(e)}, 500

def inicializar_banco():
    try:
        conn = sqlite3.connect("respostas.db")
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS respostas (
            telefone TEXT PRIMARY KEY,
            ultima_resposta TEXT
        )
        """)
        conn.commit()
        print("🛠️ Banco de dados de respostas inicializado com sucesso.", flush=True)
    except Exception as e:
        print("⚠️ Erro ao inicializar banco de dados de respostas:", e, flush=True)
    finally:
        conn.close()

import subprocess
if __name__ == "__main__":
    from threading import Thread

    # Iniciar o painel Streamlit em segundo plano
    def start_streamlit():
        subprocess.Popen(["streamlit", "run", "dashboard.py"])

    Thread(target=start_streamlit).start()
    app.run(host="0.0.0.0", port=10000)
