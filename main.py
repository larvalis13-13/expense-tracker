import sqlite3
import os # для проверки информации в сущ. файлах

def show_last_transactions(num_limit=5):
    """Функция выгружает и печатает последние N транзакций"""
    # Делаем запрос к базе через глобальный курсор
    cursor.execute(
        "SELECT id, category, amount, date FROM transactions ORDER BY id DESC LIMIT ?", 
        (num_limit,)
    )
    last_transactions = cursor.fetchall()

    if not last_transactions:
        print(f"\n[История пуста] Транзакций пока нет.")
    else:
        print(f"\n--- ПОСЛЕДНИЕ {len(last_transactions)} ТРАНЗАКЦИЙ ---")
        for row in last_transactions:
            print(f"ID: {row[0]} | Категория: {row[1]} | Сумма: {row[2]:.2f} руб. | Дата: {row[3]}")

def show_today_by_categories():
    """Выводит сегодняшние траты, сгруппированные по категориям"""
    # Выбираем название категории и сумму, фильтруем по дате и группируем
    cursor.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE date(date) = date('now', 'localtime')
        GROUP BY category
""")

    rows = cursor.fetchall() # Забираем список всех найденных категорий с суммами
    print(f"\n{'=' * 40}")
    print("      ТРАТЫ ЗА СЕГОДНЯ ПО КАТЕГОРИЯМ")
    print("=" * 40)
    
    # Если строк нет или первая строка содержит пустую категорию (None)
    if not rows or rows[0][0] is None:
        print("За сегодня расходов еще не было.")
    else:
        # Перебираем каждую пару (категория, сумма)
        for category, total in rows:
            print(f"• {category}: {total:.2f} руб.")
            
    print("=" * 40)

def delete_by_id(trans_id):
    """Удаляет транзакцию по ID и корректирует общую сумму категории"""
    # 1. Сначала ищем транзакцию в истории, чтобы узнать её категорию и сумму
    cursor.execute("SELECT category, amount FROM transactions WHERE id = ?", (trans_id,))
    transaction = cursor.fetchone()

    # если транзакция с таким ид не найдена 
    if transaction is None:
        print(f"\n[Ошибка] Транзакция с ID {trans_id} не найдена!")
        return

    # распаковываем данные найденной транзакции
    category, amount = transaction
    # 2. Уменьшаем общую сумму в таблице expenses для этой категории
    cursor.execute("""
        UPDATE expenses 
        SET sum_value = sum_value - ? 
        WHERE category = ?
    """, (amount, category)) 

    # 3. Удаляем саму транзакцию из таблицы transactions
    cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
    
    # Сохраняем изменения в файл базы данных
    conn.commit()
    
    print(f"\n[Успешно] Транзакция ID {trans_id} удалена.")
    print(f"Из категории '{category}' вычтено {amount:.2f} руб.")



# === 1. ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ===
# Если файла 'expenses.db' нет, Python САМ создаст его в этой строке
conn = sqlite3.connect("expenses.db")
cursor = conn.cursor()


# Создаем таблицу, если программа запускается впервые
cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    category TEXT PRIMARY KEY,
    sum_value REAL
)
""")
conn.commit()

# Шаблон категорий для инициализации пустой базы данных
initial_categories = [
    "На еду", "Одежда", "Развлечение", 
    "Комуналка и содержание жилья", 
    "Заправка авто", "Содержание авто", "Прочие"
]

# Заполняем таблицу базовыми категориями с нулями (только если они еще не добавлены)
for cat in initial_categories:
    cursor.execute("INSERT OR IGNORE INTO expenses (category, sum_value) VALUES (?, 0.0)", (cat,))
conn.commit()

# создаем таблицу "история транзакций"
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, amount REAL, date TEXT
)                    
""")
conn.commit()


# === 2. ОСНОВНОЙ ЦИКЛ ПРОГРАММЫ ===
while True:
    # Загружаем актуальный список категорий и сумм прямо из базы данных
    cursor.execute("SELECT category, sum_value FROM expenses")
    rows = cursor.fetchall()
    
    print("\n--- ДОСТУПНЫЕ КАТЕГОРИИ ---")
    for i, row in enumerate(rows, 1):
        print(f"{i}. {row[0]} (Текущая сумма: {row[1]:.2f} руб.)")
    print("8. Посмотреть текущие расходы за сегодня")
    print("9. Посмотреть последние 5 транзакций")
    print("10. Удалить запись по ID")
    print("0. Выход из программы")
    
    choice = input("\nВыберите номер категории (или 0 для выхода): ")
    
    if choice == "0":
        show_last_transactions(5)
        print("\nЗавершение работы. Все данные уже сохранены в базе!")
        break
    if choice == "8":
        show_today_by_categories()
        continue
    if choice == "9":
        show_last_transactions(5)
        continue
    if choice == "10":
        show_last_transactions(10)
        transaction_id = input("Введите ID транзакции для удаления :")
        try:
            transaction_id = int(transaction_id)
            delete_by_id(transaction_id)
        except ValueError:
            print("Ошибка! ID должен быть числом")
        continue
    
    # проверяем выбор категории
    if not choice.isdigit() or not (1 <= int(choice) <= len(rows)):
        print("Ошибка! Введите корректный номер пункта меню.")
        continue
     
    # Получаем название выбранной категории из выгруженных строк
    selected_category = rows[int(choice) - 1][0]
    
    amount_str = input(f"Введите сумму для категории '{selected_category}': ")
    
    try:
        amount = float(amount_str)
        if amount <= 0:
            print("Расходы не могут быть меньше нуля!")
            continue
    except ValueError:
        print("Ошибка! Вводите только числа. Возврат к началу.")
        continue
        
    # === 3. ОБНОВЛЕНИЕ ДАННЫХ В БАЗЕ ===
    # шаг 1:SQL-запрос: прибавляем сумму к уже существующей в базе
    cursor.execute("""
        UPDATE expenses 
        SET sum_value = sum_value + ? 
        WHERE category = ?
    """, (amount, selected_category))
    
    # Шаг 2: Добавляем новую отдельную запись в историю транзакций
    # Вместо id передаем NULL (он увеличится сам), а вместо даты используем функцию SQLite datetime()
    cursor.execute("""
        INSERT INTO transactions (id, category, amount, date)
        VALUES (NULL, ?, ?, datetime('now', 'localtime'))
    """, (selected_category, amount))
    
    # Сохраняем изменения на жесткий диск сразу же!
    conn.commit()
    print(f"Успешно добавлено {amount} в категорию '{selected_category}'!")

# === 4. ЗАКРЫТИЕ СОЕДИНЕНИЯ ===
# В конце обязательно закрываем соединение с базой данных
conn.close()