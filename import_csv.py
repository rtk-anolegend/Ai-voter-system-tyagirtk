import pandas as pd
import sqlite3
from pathlib import Path

# ===== PATHS =====
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "voter_system.db"
CSV_PATH = DATA_DIR / "voters.csv"

# ===== ENSURE FOLDER EXISTS (VERY IMPORTANT) =====
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ===== COLORS =====
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

print(f"{YELLOW}🚀 Starting Import (STABLE MODE)...{RESET}")

# ===== SAFE DB CONNECT (IMPORTANT FIX) =====
conn = sqlite3.connect(str(DB_PATH), timeout=10)
conn.execute("PRAGMA journal_mode=WAL;")  # Raspberry Pi stability boost
cur = conn.cursor()

# ===== TABLE (MATCH database.py EXACTLY) =====
cur.execute("""
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_no TEXT UNIQUE,
    epic TEXT,
    name TEXT NOT NULL,
    name_hindi TEXT,
    relation_type TEXT,
    relation_name TEXT,
    house_no TEXT,
    age INTEGER,
    gender TEXT,
    mobile TEXT,
    category TEXT,
    village TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

print(f"{GREEN}✅ DB Ready & Synced{RESET}")

# ===== LOAD CSV SAFE =====
try:
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
except Exception as e:
    print(f"{RED}❌ CSV ERROR:{RESET}", e)
    exit()

df.columns = df.columns.str.strip()
print(f"{GREEN}✅ CSV Loaded: {len(df)} rows{RESET}")

# ===== CLEAN FUNCTION =====
def clean(v):
    if v is None:
        return ""
    v = str(v).strip()
    if v.lower() in ["nan", "none", "null"]:
        return ""
    return v

# ===== IMPORT =====
success = 0
failed = 0

for _, row in df.iterrows():
    try:
        epic = clean(row.get("EPIC_Number"))

        if not epic:
            failed += 1
            continue

        cur.execute("""
        INSERT OR IGNORE INTO voters (
            serial_no, epic, name, relation_type, relation_name,
            house_no, age, gender, mobile, category, village, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            clean(row.get("Serial_Number")),
            epic,
            clean(row.get("Name")),
            clean(row.get("Relation_Type")),
            clean(row.get("Relation_Name")),
            clean(row.get("House_Number")),
            int(row.get("Age")) if str(row.get("Age")).isdigit() else None,
            clean(row.get("Gender")),
            clean(row.get("Mobile")),
            clean(row.get("Category")),
            clean(row.get("Village")),
            clean(row.get("Notes"))
        ))

        if cur.rowcount > 0:
            success += 1
        else:
            failed += 1

    except Exception as e:
        failed += 1
        print(f"{RED}❌ Row Error:{RESET}", e)

# ===== SAVE =====
conn.commit()
conn.close()

print(f"{GREEN}🎉 IMPORT COMPLETE{RESET}")
print(f"{GREEN}✔ Success: {success}{RESET}")
print(f"{RED}✖ Failed: {failed}{RESET}")
