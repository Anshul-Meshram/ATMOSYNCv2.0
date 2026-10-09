import sqlite3

db_path = r"M:/sem7/Major Project/ATMOSYNCv2.0/rag_pipeline/qdrant_storage/collection/climate_documents\storage.sqlite"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

#List all tables
cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type = 'table';
""")

tables = cursor.fetchall()

for (table,) in tables:
    print(f"\n{'='*40}")
    print("TABLE",table)

    #Display columns
    cursor.execute(f'PRAGMA table_info("{table}")')
    print("COLUMNS:",[column[1] for column in cursor.fetchall()])

    #Display a few records 
    cursor.execute(f'SELECT * FROM "{table}" LIMIT 3')
    for row in cursor.fetchall():
        print(row)

conn.close()
    