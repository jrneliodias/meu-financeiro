sqlite3 db.sqlite3 "SELECT name FROM registers_category WHERE type = 'expense' ORDER BY name;"


# Process January (month 1)
python manage.py recurrence_payment --month 1


