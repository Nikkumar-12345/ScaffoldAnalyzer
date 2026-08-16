import sqlite3


DB_PATH = r"C:\Users\Nikhil\.data\chembl\37\chembl_37.db"


print("=" * 70)
print("CONNECTING TO ChEMBL DATABASE")
print("=" * 70)


conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()


# ------------------------------------------------------------
# SHOW ALL TABLES
# ------------------------------------------------------------

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""")

tables = cursor.fetchall()


print("\nTOTAL TABLES:", len(tables))

print("\nTABLES:\n")

for index, (table_name,) in enumerate(tables, start=1):

    print(f"{index}. {table_name}")


# ------------------------------------------------------------
# SHOW COLUMNS FOR IMPORTANT TABLES
# ------------------------------------------------------------

important_tables = [
    "target_dictionary",
    "target_components",
    "component_sequences",
    "activities",
    "molecule_dictionary",
    "compound_structures",
    "assays",
    "docs"
]


print("\n" + "=" * 70)
print("IMPORTANT TABLE SCHEMAS")
print("=" * 70)


for table_name in important_tables:

    print(f"\n--- {table_name} ---")

    cursor.execute(
        f"SELECT name FROM sqlite_master "
        f"WHERE type='table' AND name=?",
        (table_name,)
    )

    exists = cursor.fetchone()

    if not exists:

        print("TABLE NOT FOUND")
        continue


    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = cursor.fetchall()


    for column in columns:

        column_name = column[1]
        column_type = column[2]

        print(
            f"{column_name:<35} {column_type}"
        )


# ------------------------------------------------------------
# SHOW DATABASE SIZE
# ------------------------------------------------------------

cursor.close()
conn.close()


print("\n" + "=" * 70)
print("DONE")
print("=" * 70)