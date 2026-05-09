import pandas as pd
import sqlite3
from datetime import datetime
import hashlib
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, db_path='voter_system.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Voters table
        cursor.execute('''
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
        ''')
        
        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voter_id INTEGER,
                file_path TEXT,
                doc_type TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (voter_id) REFERENCES voters (id)
            )
        ''')
        
        # Families table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS families (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_code TEXT UNIQUE,
                house_no TEXT,
                total_members INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Users table for authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_admin_user(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)',
                         (username, hashed_password))
            conn.commit()
        except:
            pass
        finally:
            conn.close()
    
    def authenticate_user(self, username, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            return user
        return None
    
    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def smart_search(self, query, search_type='all'):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        search_terms = query.lower().split()
        
        # Build search conditions
        conditions = []
        params = []
        
        # Handle special search patterns
        if ':' in query:
            field, value = query.split(':', 1)
            if field == 'house':
                conditions.append('house_no = ?')
                params.append(value.strip())
            elif field == 'age':
                conditions.append('age = ?')
                params.append(int(value.strip()))
            elif field == 'village':
                conditions.append('village LIKE ?')
                params.append(f'%{value.strip()}%')
        else:
            # General search across multiple fields
            search_fields = ['name', 'epic', 'house_no', 'relation_name', 'mobile']
            for term in search_terms:
                term_conditions = []
                for field in search_fields:
                    term_conditions.append(f"LOWER({field}) LIKE ?")
                    params.append(f'%{term}%')
                conditions.append(f"({' OR '.join(term_conditions)})")
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        
        query_sql = f'''
            SELECT v.*, COUNT(d.id) as doc_count 
            FROM voters v
            LEFT JOIN documents d ON v.id = d.voter_id
            WHERE {where_clause}
            GROUP BY v.id
            ORDER BY v.name
            LIMIT 100
        '''
        
        cursor.execute(query_sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_voter_by_id(self, voter_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM voters WHERE id = ?', (voter_id,))
        voter = cursor.fetchone()
        conn.close()
        return dict(voter) if voter else None
    
    def get_family_members(self, house_no):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM voters WHERE house_no = ? ORDER BY age DESC', (house_no,))
        members = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return members
    
    def get_voter_documents(self, voter_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM documents WHERE voter_id = ? ORDER BY uploaded_at DESC', (voter_id,))
        documents = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return documents
    
    def add_document(self, voter_id, file_path, doc_type):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO documents (voter_id, file_path, doc_type)
            VALUES (?, ?, ?)
        ''', (voter_id, file_path, doc_type))
        conn.commit()
        doc_id = cursor.lastrowid
        conn.close()
        return doc_id
    
    def get_dashboard_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total voters
        cursor.execute('SELECT COUNT(*) as count FROM voters')
        total_voters = cursor.fetchone()['count']
        
        # Male count
        cursor.execute('SELECT COUNT(*) as count FROM voters WHERE gender = "पुरुष"')
        male_count = cursor.fetchone()['count']
        
        # Female count
        cursor.execute('SELECT COUNT(*) as count FROM voters WHERE gender = "महिला"')
        female_count = cursor.fetchone()['count']
        
        # Senior citizens (age >= 60)
        cursor.execute('SELECT COUNT(*) as count FROM voters WHERE age >= 60')
        senior_count = cursor.fetchone()['count']
        
        # Unique families (unique house numbers)
        cursor.execute('SELECT COUNT(DISTINCT house_no) as count FROM voters WHERE house_no IS NOT NULL')
        families_count = cursor.fetchone()['count']
        
        # Total documents
        cursor.execute('SELECT COUNT(*) as count FROM documents')
        doc_count = cursor.fetchone()['count']
        
        conn.close()
        
        return {
            'total_voters': total_voters,
            'male_count': male_count,
            'female_count': female_count,
            'senior_count': senior_count,
            'families_count': families_count,
            'doc_count': doc_count
        }
    
    def get_age_distribution(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN age < 18 THEN 'Under 18'
                    WHEN age BETWEEN 18 AND 30 THEN '18-30'
                    WHEN age BETWEEN 31 AND 45 THEN '31-45'
                    WHEN age BETWEEN 46 AND 60 THEN '46-60'
                    ELSE '60+'
                END as age_group,
                COUNT(*) as count
            FROM voters
            WHERE age IS NOT NULL
            GROUP BY age_group
            ORDER BY MIN(age)
        ''')
        
        distribution = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return distribution
    
    def get_gender_ratio(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                gender,
                COUNT(*) as count
            FROM voters
            WHERE gender IS NOT NULL
            GROUP BY gender
        ''')
        
        ratio = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return ratio
    
    def get_recent_voters(self, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM voters 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        recent = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return recent
    
    def export_to_csv(self):
        conn = self.get_connection()
        df = pd.read_sql_query('SELECT * FROM voters', conn)
        conn.close()
        return df.to_dict('records')
    
    def import_from_dataframe(self, df):
        conn = self.get_connection()
        cursor = conn.cursor()
        count = 0
        
        for _, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO voters 
                    (serial_no, epic, name, name_hindi, relation_type, relation_name, 
                     house_no, age, gender, mobile, category, village, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('serial_no'), row.get('epic'), row.get('name'), 
                    row.get('name_hindi'), row.get('relation_type'), row.get('relation_name'),
                    row.get('house_no'), row.get('age'), row.get('gender'), 
                    row.get('mobile'), row.get('category'), row.get('village'), row.get('notes')
                ))
                count += 1
            except:
                continue
        
        conn.commit()
        conn.close()
        return count
    
    def backup_database(self):
        import shutil
        from datetime import datetime
        
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(self.db_path, backup_name)
        return backup_name
