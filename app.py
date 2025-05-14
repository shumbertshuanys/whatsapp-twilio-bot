from flask import Flask, request
import requests

app = Flask(__name__)

@app.route("/twilio-webhook", methods=["POST"])
def receber_mensagem():
    mensagem = request.form.get("Body")
    telefone = request.form.get("From")

    print(f"📨 Nova mensagem de {telefone}: {mensagem}")

    # Em breve: cadastrar_lead_no_vista(telefone, mensagem)

    return "Mensagem recebida com sucesso", 200

if __name__ == "__main__":
    app.run(port=5000)
