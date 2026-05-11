import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

# ===== PATHS =====
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DB_PATH = DATA_DIR / "voter_system.db"
CSV_PATH = DATA_DIR / "voters.csv"

# ===== CREATE DATA DIR =====
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ===== COLORS =====
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

print(f"{YELLOW}🚀 SAFE VOTER IMPORT STARTED{RESET}")

# =========================================================
# AUTO DATABASE BACKUP
# =========================================================
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = DATA_DIR / f"backup_{timestamp}.db"

if DB_PATH.exists():
    shutil.copy(DB_PATH, backup_path)
    print(f"{GREEN}✅ Backup Created:{RESET} {backup_path.name}")

# =========================================================
# DATABASE CONNECT
# =========================================================
conn = sqlite3.connect(str(DB_PATH), timeout=15)

# Raspberry Pi optimization
conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")

cur = conn.cursor()

# =========================================================
# CREATE TABLE IF NOT EXISTS
# =========================================================
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

print(f"{GREEN}✅ Database Ready{RESET}")

# =========================================================
# LOAD CSV
# =========================================================
if not CSV_PATH.exists():
    print(f"{RED}❌ voters.csv NOT FOUND inside data folder{RESET}")
    exit()

try:
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
except Exception as e:
    print(f"{RED}❌ CSV READ ERROR:{RESET} {e}")
    exit()

# =========================================================
# CLEAN COLUMN NAMES
# =========================================================
df.columns = df.columns.str.strip()

print(f"{GREEN}✅ CSV Loaded:{RESET} {len(df)} rows")

# =========================================================
# REQUIRED COLUMNS CHECK
# =========================================================
required_columns = [
    "Serial_Number",
    "EPIC_Number",
    "Name"
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    print(f"{RED}❌ Missing Columns:{RESET} {missing}")
    exit()

# =========================================================
# REMOVE CSV DUPLICATES
# =========================================================
before = len(df)

df = df.drop_duplicates(subset=["EPIC_Number"])

after = len(df)

removed = before - after

print(f"{CYAN}🧹 CSV Duplicate Removed:{RESET} {removed}")

# =========================================================
# CLEAN FUNCTION
# =========================================================
def clean(v):
    if pd.isna(v):
        return ""

    v = str(v).strip()

    if v.lower() in ["nan", "none", "null"]:
        return ""

    return v

# =========================================================
# IMPORT PROCESS
# =========================================================
success = 0
duplicate = 0
failed = 0

for _, row in df.iterrows():

    try:
        epic = clean(row.get("EPIC_Number"))

        if not epic:
            failed += 1
            continue

        # ==========================================
        # CHECK DUPLICATE EPIC
        # ==========================================
        existing_epic = cur.execute(
            "SELECT id FROM voters WHERE epic = ?",
            (epic,)
        ).fetchone()

        if existing_epic:
            duplicate += 1
            continue

        serial_no = clean(row.get("Serial_Number"))

        # ==========================================
        # CHECK DUPLICATE SERIAL
        # ==========================================
        if serial_no:
            existing_serial = cur.execute(
                "SELECT id FROM voters WHERE serial_no = ?",
                (serial_no,)
            ).fetchone()

            if existing_serial:
                duplicate += 1
                continue

        # ==========================================
        # INSERT SAFE
        # ==========================================
        cur.execute("""
        INSERT INTO voters (
            serial_no,
            epic,
            name,
            relation_type,
            relation_name,
            house_no,
            age,
            gender,
            mobile,
            category,
            village,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            serial_no,
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

        success += 1

    except Exception as e:
        failed += 1
        print(f"{RED}❌ Row Failed:{RESET}", e)

# =========================================================
# SAVE
# =========================================================
conn.commit()

# =========================================================
# FINAL COUNT
# =========================================================
total = cur.execute(
    "SELECT COUNT(*) FROM voters"
).fetchone()[0]

conn.close()

# =========================================================
# REPORT
# =========================================================
print()
print(f"{GREEN}🎉 IMPORT FINISHED{RESET}")
print(f"{GREEN}✔ New Imported:{RESET} {success}")
print(f"{YELLOW}⚠ Duplicates Skipped:{RESET} {duplicate}")
print(f"{RED}✖ Failed Rows:{RESET} {failed}")
print(f"{CYAN}📦 Total Database Records:{RESET} {total}")
print()
print(f"{GREEN}✅ Database Safe")
print("✅ Existing Users Safe")
print("✅ Existing Passwords Safe")
print("✅ Existing Tokens Safe")
print("✅ No Delete Performed")
print("✅ No Overwrite Performed")
print(f"{RESET}")
