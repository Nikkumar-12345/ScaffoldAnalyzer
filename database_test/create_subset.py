try:
    import chembl_downloader
except ImportError:
    print("Error: chembl-downloader package not found.")
    print("Install it using: pip install chembl-downloader")
    exit(1)

print("Downloading ChEMBL SQLite database...")

path = chembl_downloader.download_extract_sqlite()

print("\nDatabase downloaded successfully.")
print("Database path:")
print(path)