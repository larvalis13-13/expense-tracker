import sqlite3
from flask import Flask, render_template, request, redirect, url_for, make_response
from datetime import datetime, timedelta
import csv
import io

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('expenses.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    
    # Получаем категории
    categories = conn.execute('SELECT category, sum_value FROM expenses ORDER BY category').fetchall()
    
    # Считаем статистику
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # За сегодня
    today_sum = conn.execute(
        'SELECT SUM(amount) FROM transactions WHERE date(date) >= ?', 
        (today,)
    ).fetchone()[0] or 0
    
    # За неделю
    week_sum = conn.execute(
        'SELECT SUM(amount) FROM transactions WHERE date(date) >= ?', 
        (week_ago,)
    ).fetchone()[0] or 0
    
    # Всего
    total_sum = conn.execute('SELECT SUM(sum_value) FROM expenses').fetchone()[0] or 0
    
    conn.close()
    
    stats = {
        'today': round(today_sum, 2),
        'week': round(week_sum, 2),
        'total': round(total_sum, 2)
    }
    
    return render_template('index.html', categories=categories, stats=stats)

@app.route('/add', methods=['POST'])
def add_expense():
    category = request.form['category']
    amount = float(request.form['amount'])
    
    conn = get_db_connection()
    conn.execute('UPDATE expenses SET sum_value = sum_value + ? WHERE category = ?', 
                 (amount, category))
    conn.execute('INSERT INTO transactions (category, amount, date) VALUES (?, ?, datetime("now", "localtime"))',
                 (category, amount))
    conn.commit()
    conn.close()
    
    return redirect(url_for('index'))

@app.route('/history')
def history():
    conn = get_db_connection()
    transactions = conn.execute(
        'SELECT id, category, amount, date FROM transactions ORDER BY id DESC LIMIT 20'
    ).fetchall()
    conn.close()
    return render_template('history.html', transactions=transactions)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_transaction(id):
    conn = get_db_connection()
    transaction = conn.execute('SELECT category, amount FROM transactions WHERE id = ?', (id,)).fetchone()
    
    if transaction:
        conn.execute('UPDATE expenses SET sum_value = sum_value - ? WHERE category = ?', 
                     (transaction['amount'], transaction['category']))
        conn.execute('DELETE FROM transactions WHERE id = ?', (id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('history'))

@app.route('/export')
def export_csv():
    conn = get_db_connection()
    transactions = conn.execute(
        'SELECT id, category, amount, date FROM transactions ORDER BY id DESC'
    ).fetchall()
    conn.close()
    
    # Создаем CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Категория', 'Сумма', 'Дата'])
    
    for t in transactions:
        writer.writerow([t['id'], t['category'], t['amount'], t['date']])
    
    # Создаем ответ с CSV
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = f'attachment; filename=expenses_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return response

if __name__ == '__main__':
    app.run(debug=True)