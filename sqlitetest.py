import sqlite3

if __name__ == "__main__":
    conn = sqlite3.connect("test.db")
    cursor = conn.cursor()
    create_table_sql = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    points INTEGER DEFAULT 100,
    email TEXT UNIQUE,
    dick_length REAL
);
"""
    cursor.execute(create_table_sql)
    cursor.execute(
        "INSERT INTO projects (name, points, email, dick_length) VALUES (?, ?, ?, ?)",
        ("Salt", 258, "noreply@example.com", -2.58),
    )
    conn.commit()
    conn.close()
