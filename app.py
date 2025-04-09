from flask import Flask, render_template, jsonify
import csv
import datetime
import random
import json
import os

import psycopg2
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
# from twilio.rest import Client

load_dotenv(dotenv_path=".env.local")
"""
# Configurações do Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = 'whatsapp:+14155238886'  # Número padrão do sandbox Twilio
ADMIN_WHATSAPP_TO = os.getenv("ADMIN_WHATSAPP_TO")

print(f"TWILIO_ACCOUNT_SID: {TWILIO_ACCOUNT_SID}")
print(f"TWILIO_AUTH_TOKEN: {TWILIO_AUTH_TOKEN}")
print(f"ADMIN_WHATSAPP_TO: {ADMIN_WHATSAPP_TO}")

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not ADMIN_WHATSAPP_TO:
    print("[ERRO] Credenciais Twilio não configuradas corretamente.")

# Flag para detectar primeiro acesso
first_access_sent = False
first_sort_sent = False

# Envio de mensagens WhatsApp
def send_whatsapp_message(message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=ADMIN_WHATSAPP_TO
        )
        print(f"[DEBUG] Mensagem enviada com sucesso: SID {message.sid}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar WhatsApp: {e}")
"""
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    try:
        print(f"[DEBUG] Conectando ao banco: {DATABASE_URL}")
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"[ERRO] Falha ao conectar no banco de dados: {e}")
        # send_whatsapp_message("❌ ERRO CRÍTICO: Falha ao conectar no banco de dados SAPPP.")
        raise

app = Flask(__name__)

SORTED_ITEMS_FILE = "sorted_items.json"
DAILY_SORT_FILE = "daily_sorted.json"

def get_valid_csv_data():
    try:
        with open('data/SAPPP_office3.csv', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=';')
            rows = list(reader)

        valid_rows = []
        numbering = 1  

        for row in rows:
            if row and row[0].isdigit():  
                valid_rows.append([numbering] + row[1:])
                numbering += 1

        return valid_rows
    except Exception as e:
        print(f"[ERRO] Falha ao carregar CSV: {e}")
         # send_whatsapp_message("📄 ERRO: Falha ao carregar o arquivo CSV do SAPPP.")
        return []

def is_weekday():
    now = datetime.datetime.now(ZoneInfo("America/Sao_Paulo"))
    return now.weekday() < 5

def get_items_for_today():
    global first_sort_sent

    weekday = datetime.datetime.today().weekday()
    if weekday >= 5:
        print("Hoje é sábado ou domingo, não haverá sorteio.")
        return []

    today = datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    print(f"[DEBUG] Verificando itens para a data: {today}")

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT item_1, item_2, item_3 FROM daily_items WHERE date = %s;", (today,))
        row = cur.fetchone()
        rows = get_valid_csv_data()

        if row:
            selected_ids = [row[0], row[1], row[2]]
            result = [item for item in rows if str(item[0]) in selected_ids]
            conn.close()
            return result

        all_ids = [str(row[0]) for row in rows]
        random.shuffle(all_ids)

        selected_ids = all_ids[:min(3, len(all_ids))]
        item_1 = selected_ids[0] if len(selected_ids) > 0 else None
        item_2 = selected_ids[1] if len(selected_ids) > 1 else None
        item_3 = selected_ids[2] if len(selected_ids) > 2 else None

        cur.execute(
            "INSERT INTO daily_items (date, item_1, item_2, item_3) VALUES (%s, %s, %s, %s);",
            (today, item_1, item_2, item_3)
        )

        conn.commit()

        selected_items = [item for item in rows if str(item[0]) in selected_ids]
        mensagem_itens = "\n".join(
            [f"{item[0]} - {item[1]}" for item in selected_items]
        )
        data_formatada = today.strftime("%d/%m/%Y")

         if not first_sort_sent:
            ''' send_whatsapp_message(
                f"""📅 Itens sorteados para o dia {data_formatada}:
{mensagem_itens}"""
            )
            first_sort_sent = True '''

        cur.close()
        conn.close()

        return selected_items

    except Exception as e:
        print(f"[ERRO] Falha ao sortear itens do dia: {e}")
        # send_whatsapp_message("⚠️ ERRO: Falha ao sortear os itens do dia no SAPPP.")
        return []

@app.route('/')
def index():
    global first_access_sent
    #if not first_access_sent:
    #send_whatsapp_message("⚠️ O sistema SAPPP foi acessado pela primeira vez.")
    first_access_sent = True
    return render_template('index.html')

@app.route('/get_lines')
def get_lines():
    rows_to_show = get_items_for_today()

    formatted_data = [
        {
            "descricao": item[1],
            "numero": item[0],
            "peso": item[2],
            "orientacao": item[5] if len(item) > 5 else "Sem orientação",
            "referencia": item[6] if len(item) > 6 else "Sem referência"
        }
        for item in rows_to_show
    ]

    return jsonify(formatted_data)

@app.route('/get_item_details/<int:item_num>')
def get_item_details(item_num):
    rows = get_valid_csv_data()
    item = next((row for row in rows if row[0] == item_num), None)

    if item:
        details = {
            "descricao": item[1],
            "numero": item[0],
            "peso": item[2],
            "orientacao": item[5] if len(item) > 5 else "Sem orientação",
            "referencia": item[6] if len(item) > 6 else "Sem referência"
        }
        return jsonify(details)

    return jsonify({"error": "Item não encontrado"}), 404

@app.route('/search_items/<search_query>')
def search_items(search_query):
    rows = get_valid_csv_data()
    filtered_items = [
        {
            "descricao": item[1],
            "numero": item[0],
            "peso": item[2],
            "orientacao": item[5] if len(item) > 5 else "Sem orientação",
            "referencia": item[6] if len(item) > 6 else "Sem referência"
        }
        for item in rows if search_query.lower() in item[1].lower()
    ]
    return jsonify(filtered_items)

@app.route('/simulador')
def simulador():
    return render_template('simulador.html')

@app.route('/get_all_items')
def get_all_items():
    """Retorna todos os itens da lista com pesos."""
    rows = get_valid_csv_data()
    items = [
        {
            "descricao": item[1],
            "numero": item[0],
            "peso": int(item[2]) if item[2].isdigit() else 0
        }
        for item in rows
    ]
    return jsonify(items)

@app.route('/test_csv')
def test_csv():
    rows = get_valid_csv_data()
    return f"Total de linhas válidas: {len(rows)}"

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)


