from flask import Flask, render_template, jsonify
import csv
import datetime
import random
import json
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    print(f"[DEBUG] Conectando ao banco: {DATABASE_URL}")
    return psycopg2.connect(DATABASE_URL)

app = Flask(__name__)

SORTED_ITEMS_FILE = "sorted_items.json"
DAILY_SORT_FILE = "daily_sorted.json"

def get_valid_csv_data():
    """Lê o arquivo CSV e retorna os itens válidos."""
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

def is_weekday():
    """Verifica se hoje é um dia útil (segunda a sexta)."""
    return datetime.datetime.today().weekday() < 5  # 0 = Segunda, 4 = Sexta

def get_business_day_count():
    """Conta quantos dias úteis já passaram no mês."""
    today = datetime.datetime.today()
    first_day = today.replace(day=1)
    
    business_days = [
        first_day + datetime.timedelta(days=i)
        for i in range((today - first_day).days + 1)
        if (first_day + datetime.timedelta(days=i)).weekday() < 5
    ]
    
    return len(business_days)

def load_sorted_items():
    """Carrega os itens já sorteados do arquivo JSON."""
    if os.path.exists(SORTED_ITEMS_FILE):
        with open(SORTED_ITEMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_sorted_items(sorted_items):
    """Salva os itens sorteados no arquivo JSON."""
    with open(SORTED_ITEMS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_items, f)

def load_daily_sorted_items():
    """Carrega os itens sorteados no dia do arquivo JSON."""
    if os.path.exists(DAILY_SORT_FILE):
        with open(DAILY_SORT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_daily_sorted_items(daily_sorted_items):
    """Salva os itens sorteados no dia no arquivo JSON."""
    with open(DAILY_SORT_FILE, "w", encoding="utf-8") as f:
        json.dump(daily_sorted_items, f)

def get_items_for_today():
    if not is_weekday():
        return []

    today = datetime.date.today()

    # Conecta ao banco
    conn = get_db_connection()
    cur = conn.cursor()

    # Verifica se já existem itens para hoje
    cur.execute("SELECT item_1, item_2, item_3 FROM daily_items WHERE date = %s;", (today,))
    row = cur.fetchone()

    rows = get_valid_csv_data()

    if row:
        # Já existem itens sorteados hoje, retorna os itens correspondentes
        selected_ids = [row[0], row[1], row[2]]
        result = [item for item in rows if str(item[0]) in selected_ids]
        conn.close()
        return result

    # Caso não existam ainda, sorteia
    all_ids = [str(row[0]) for row in rows]
    random.shuffle(all_ids)

    num_to_select = min(3, len(all_ids))  # pega 3 ou menos, dependendo do que tiver
    selected_ids = all_ids[:num_to_select]

    item_1 = selected_ids[0] if len(selected_ids) > 0 else None
    item_2 = selected_ids[1] if len(selected_ids) > 1 else None
    item_3 = selected_ids[2] if len(selected_ids) > 2 else None

     # Salva os itens no banco
    
    cur.execute(
        "INSERT INTO daily_items (date, item_1, item_2, item_3) VALUES (%s, %s, %s, %s);",
        (today, item_1, item_2, item_3)
    )

    conn.commit()
    cur.close()
    conn.close()

    return [item for item in rows if str(item[0]) in selected_ids]


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_lines')
def get_lines():
    """Retorna os itens do dia."""
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
    """Retorna os detalhes de um item específico sem sorteá-lo."""
    rows = get_valid_csv_data()

    # Busca o item pelo número
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
    """Retorna os itens que correspondem à pesquisa."""
    rows = get_valid_csv_data()

    # Filtra os itens com base na pesquisa (ignora maiúsculas/minúsculas)
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

@app.route('/test_csv')
def test_csv():
    rows = get_valid_csv_data()
    return f"Total de linhas válidas: {len(rows)}"




if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
