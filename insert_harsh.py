import sqlite3

conn = sqlite3.connect("jarvis.db")
cursor = conn.cursor()

# Ensure contacts table exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        relationship TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
""")

# Insert or update Harsh
cursor.execute("""
    INSERT INTO contacts (name, phone, relationship)
    VALUES (?, ?, ?)
    ON CONFLICT(name) DO UPDATE SET
        phone = excluded.phone,
        relationship = excluded.relationship,
        updated_at = CURRENT_TIMESTAMP
""", ("Harsh", "8054840494", "friend"))

# Also save lowercase 'harsh'
cursor.execute("""
    INSERT INTO contacts (name, phone, relationship)
    VALUES (?, ?, ?)
    ON CONFLICT(name) DO UPDATE SET
        phone = excluded.phone,
        relationship = excluded.relationship,
        updated_at = CURRENT_TIMESTAMP
""", ("harsh", "8054840494", "friend"))

conn.commit()

# Verify
cursor.execute("SELECT id, name, phone, relationship FROM contacts")
rows = cursor.fetchall()
print("=== SAVED CONTACTS IN JARVIS DATABASE ===")
for r in rows:
    print(f"ID: {r[0]} | Name: '{r[1]}' | Phone: '{r[2]}' | Rel: '{r[3]}'")

conn.close()
