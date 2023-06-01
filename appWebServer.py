from flask import Flask, render_template, request, redirect, session
import uuid
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret'  # Brug en sikker hemmelig nøgle til sessions

queue = []  # Liste til at gemme kødata

idag = datetime(2020, 1, 1).date()
table_name = ""

if not idag == datetime.now().date():
    idag = datetime.now().date().strftime("%Y%m%d")

    # Opret forbindelse til databasen
    conn = sqlite3.connect('kin_database.db')

    # Opret en cursor
    cursor = conn.cursor()

    # Opret tabellen med variablen 'idag' som navn
    table_name = f"table_{idag}"  # Tilføjer et præfiks til tabelnavnet
    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, værdi INTEGER, ventetid INTEGER)"
    cursor.execute(create_table_query)

    # Gem ændringerne og luk forbindelsen til databasen
    conn.commit()
    conn.close()
    idag = datetime.now().date()

def opdater_data(ventetid):

    conn = sqlite3.connect('kin_database.db')
    cursor = conn.cursor()

    # Hent den nuværende værdi for den pågældende ugedag
    cursor.execute(f"SELECT værdi FROM {table_name} ORDER BY id DESC LIMIT 1")
    result = cursor.fetchone()
    værdi = 1 if result is None else result[0] + 1

    # Tilføj en ny række med den opdaterede værdi og timestamp
    cursor.execute(f"INSERT INTO {table_name} (værdi, ventetid) VALUES (?, ?)", (værdi, ventetid))
    conn.commit()
    conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session or session['user_id'] not in queue:
        session['user_id'] = str(uuid.uuid4())  # Generer en unik bruger-id
        session['timestamp'] = datetime.now()  # Tilføj timestamp til session
        queue.append(session['user_id'])  # Tilføj brugeren til køen
    
    conn = sqlite3.connect('kin_database.db')
    cursor = conn.cursor()

    cursor.execute(f"SELECT AVG(ventetid) FROM {table_name} ORDER BY id DESC LIMIT 10")
    result = cursor.fetchall()

    # Hvis der er data tilgængelig
    if result and result[0][0] is not None:
        aktuel_ventetid = round((result[0][0]), 2)
    else:
        aktuel_ventetid = "0.0"
    conn.close()
        #return aktuel_ventetid

    position = queue.index(session['user_id']) + 1  # Find brugerens position i køen
    return render_template('index.html', position=position, aktuel_ventetid=aktuel_ventetid)

@app.route('/update', methods=['GET'])
def update():
    if 'user_id' in session:
        if session['user_id'] in queue:
            position = queue.index(session['user_id']) + 1  # Find brugerens position i køen
            return str(position)
        else:
            return '0'  # Brugeren er ikke længere i køen

    return '0'  # Hvis brugeren ikke har et bruger-id, betyder det, at de ikke er i køen

@app.route('/remove', methods=['POST'])
def remove():
    if 'remove_button' in request.form:
        if len(queue) > 0:

            queue.pop(0)  # Fjern den første bruger fra køen

    elif 'upload_button' in request.form:
        if len(queue) > 0:
            first_timestamp = session['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(first_timestamp, current_timestamp)

            # Beregn tidsforskellen i minutter
            first_timestamp = datetime.strptime(first_timestamp, '%Y-%m-%d %H:%M:%S')
            current_timestamp = datetime.strptime(current_timestamp, '%Y-%m-%d %H:%M:%S')
            waiting_time = current_timestamp - first_timestamp
            ventetid = round(waiting_time.total_seconds() / 60)
            opdater_data(ventetid)
            queue.pop(0)  # Fjern den første bruger fra køen

    return redirect('/employee')

@app.route('/admin')
def admin():
    # Opret forbindelse til databasen
    conn = sqlite3.connect('kin_database.db')

    # Opret en cursor
    cursor = conn.cursor()

    # Hent alle tabeller i databasen
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'table_%';")
    tables = cursor.fetchall()

    # Opret en liste til at gemme tabeller og deres data
    table_data = []

    # Loop gennem hver tabel
    for table in tables:
        table_name = table[0]

        # Hent maksimale kunder for den pågældende tabel
        cursor.execute(f"SELECT MAX(værdi) FROM {table_name};")
        max_customers = cursor.fetchone()[0]

        # Beregn gennemsnitlig ventetid for den pågældende tabel
        cursor.execute(f"SELECT AVG(ventetid) FROM {table_name};")
        avg_wait_time = cursor.fetchone()[0]

        # Tilføj tabellens data til listen
        table_data.append({
            'name': table_name,
            'max_customers': max_customers,
            'avg_wait_time': avg_wait_time
        })

    # Luk forbindelsen til databasen
    conn.close()

    # Render admin.html-skabelonen med tabellens data
    return render_template('admin.html', tables=table_data)

@app.route('/employee', methods=['GET'])
def employee():
    return render_template('employee.html', queue=queue)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80)