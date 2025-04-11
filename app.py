from flask import Flask, render_template, jsonify, request, redirect, session, url_for
import csv
import datetime
import random
import json
import os

import psycopg2
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv(dotenv_path=".env.local")

DATABASE_URL = os.getenv("DATABASE_URL")

app = Flask(__name__)
app.secret_key = 'chave-super-secreta'

MATRICULAS_AUTORIZADAS = {'81111045', '81143494', '88942872', '89090489', '89114051', '86518496', '89166078'}

first_access_sent = False
first_sort_sent = False

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"[ERRO] Falha ao conectar no banco de dados: {e}")
        raise

def get_valid_csv_data():
    try:
        with open('data/SAPPP_lista.csv', newline='', encoding='windows-1252') as csvfile:
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
        return []

def is_weekday():
    now = datetime.datetime.now(ZoneInfo("America/Sao_Paulo"))
    return now.weekday() < 5

def get_items_for_today():
    global first_sort_sent

    today = datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    if today.weekday() >= 5:
        print("Hoje é sábado ou domingo, não haverá sorteio.")
        return []

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verifica se já há sorteio para hoje
        cur.execute("SELECT item_1, item_2, item_3 FROM daily_items WHERE date = %s;", (today,))
        row = cur.fetchone()
        rows = get_valid_csv_data()

        if row:
            selected_ids = [id for id in row if id is not None]
            result = [item for item in rows if str(item[0]) in selected_ids]
            conn.close()
            return result

        # Lista todos os IDs disponíveis
        all_ids = [str(row[0]) for row in rows]

        # Busca os IDs já utilizados
        cur.execute("SELECT item_id FROM used_items;")
        used_ids = {str(row[0]) for row in cur.fetchall()}

        available_ids = [i for i in all_ids if i not in used_ids]
        random.shuffle(available_ids)

        # Se não houver itens suficientes, reinicia o ciclo
        if len(available_ids) == 0:
            print("[INFO] Reiniciando ciclo de sorteio.")
            cur.execute("DELETE FROM used_items;")
            conn.commit()
            available_ids = all_ids.copy()
            used_ids.clear()
            random.shuffle(available_ids)

        # Sorteia até 3, mas respeita o restante do ciclo
        selected_ids = available_ids[:min(3, len(available_ids))]

        item_1 = selected_ids[0] if len(selected_ids) > 0 else None
        item_2 = selected_ids[1] if len(selected_ids) > 1 else None
        item_3 = selected_ids[2] if len(selected_ids) > 2 else None

        # Salva sorteio do dia
        cur.execute(
            "INSERT INTO daily_items (date, item_1, item_2, item_3) VALUES (%s, %s, %s, %s);",
            (today, item_1, item_2, item_3)
        )

        # Salva os itens usados
        for item_id in selected_ids:
            cur.execute("INSERT INTO used_items (item_id, used_on) VALUES (%s, %s);", (item_id, today))

        conn.commit()

        selected_items = [item for item in rows if str(item[0]) in selected_ids]
        cur.close()
        conn.close()
        return selected_items

    except Exception as e:
        print(f"[ERRO] Falha ao sortear itens do dia: {e}")
        return []

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        matricula = request.form.get('matricula')
        session['matricula'] = matricula
        session['acesso_completo'] = matricula in MATRICULAS_AUTORIZADAS
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/')
def index():
    if 'matricula' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', acesso_completo=session.get('acesso_completo', False))

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
    rows = get_valid_csv_data()
    items = [
        {
            "descricao": item[1],
            "numero": item[0],
            "peso": int(item[2]) if item[2].isdigit() else 0,
            "na": item[4]
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
