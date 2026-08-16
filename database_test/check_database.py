import sqlite3
import os


DB_PATH = r"C:\Users\Nikhil\.data\chembl\37\chembl_37.db"


print("=" * 60)
print("ChEMBL DATABASE INTEGRITY CHECK")
print("=" * 60)

print("\nFile exists:", os.path.exists(DB_PATH))

if os.path.exists(DB_PATH):

    size_gb = os.path.getsize(DB_PATH) / (1024 ** 3)

    print(f"File size: {size_gb:.2f} GB")


try:

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    print("\nRunning SQLite integrity check...")
    print("This can take some time for a 15 GB database.\n")

    cursor.execute("PRAGMA integrity_check;")

    result = cursor.fetchone()[0]

    print("Integrity check result:")
    print(result)

    cursor.close()
    conn.close()

except Exception as e:

    print("\nDATABASE ERROR:")
    print(type(e).__name__)
    print(e)