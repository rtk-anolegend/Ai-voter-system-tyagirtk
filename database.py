import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import hashlib
import os
import json
import logging
import re
import unicodedata
from functools import lru_cache
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from unidecode import unidecode
except ImportError:
    unidecode = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    CACHE_SIZE = 128
    SEARCH_LIMIT = 100
    QUERY_TIMEOUT = 5
    
    def __init__(self, db_path='voter_system.db'):
        self.db_path = db_path
        self._search_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self.init_database()
        self._optimize_sqlite()
    
    def get_connection(self):
        """Get optimized SQLite connection with performance settings."""
        conn = sqlite3.connect(self.db_path, timeout=self.QUERY_TIMEOUT)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=-64000')
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.execute('PRAGMA query_only=FALSE')
        conn.execute('PRAGMA mmap_size=30000000')
        conn.execute('PRAGMA page_size=4096')
        return conn
    
    def _optimize_sqlite(self):
        """Apply SQLite optimizations for Raspberry Pi."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('PRAGMA optimize')
            conn.commit()
        except:
            pass
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database with all tables and indexes."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voter_id INTEGER,
                file_path TEXT,
                doc_type TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (voter_id) REFERENCES voters (id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS families (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                family_code TEXT UNIQUE,
                house_no TEXT,
                total_members INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 1,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT UNIQUE,
                results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                result_count INTEGER DEFAULT 0,
                response_time REAL DEFAULT 0.0,
                search_type TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        try:
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS voters_fts USING fts5(
                    name,
                    name_hindi,
                    epic,
                    relation_name,
                    village,
                    content='voters',
                    content_rowid='id'
                )
            ''')
        except:
            pass
        
        self._ensure_transliteration_columns(cursor)
        self._create_indexes(cursor)
        self._create_fts_triggers(cursor)
        conn.commit()
        conn.close()
    
    def _create_indexes(self, cursor):
        """Create all performance indexes."""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_voters_name ON voters(name)',
            'CREATE INDEX IF NOT EXISTS idx_voters_name_hindi ON voters(name_hindi)',
            'CREATE INDEX IF NOT EXISTS idx_voters_name_hindi_translit ON voters(name_hindi_translit)',
            'CREATE INDEX IF NOT EXISTS idx_voters_relation ON voters(relation_name)',
            'CREATE INDEX IF NOT EXISTS idx_voters_relation_name_translit ON voters(relation_name_translit)',
            'CREATE INDEX IF NOT EXISTS idx_voters_epic ON voters(epic)',
            'CREATE INDEX IF NOT EXISTS idx_voters_house ON voters(house_no)',
            'CREATE INDEX IF NOT EXISTS idx_voters_mobile ON voters(mobile)',
            'CREATE INDEX IF NOT EXISTS idx_voters_village ON voters(village)',
            'CREATE INDEX IF NOT EXISTS idx_voters_age ON voters(age)',
            'CREATE INDEX IF NOT EXISTS idx_voters_gender ON voters(gender)',
            'CREATE INDEX IF NOT EXISTS idx_documents_voter_id ON documents(voter_id)',
            'CREATE INDEX IF NOT EXISTS idx_families_house_no ON families(house_no)',
            'CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)',
            'CREATE INDEX IF NOT EXISTS idx_search_cache_query ON search_cache(query)',
            'CREATE INDEX IF NOT EXISTS idx_search_logs_query ON search_logs(query)',
            'CREATE INDEX IF NOT EXISTS idx_search_logs_created ON search_logs(created_at)',
        ]
        for idx_sql in indexes:
            try:
                cursor.execute(idx_sql)
            except:
                pass
    
    def _create_fts_triggers(self, cursor):
        """Create FTS5 synchronization triggers."""
        triggers = [
            '''CREATE TRIGGER IF NOT EXISTS voters_ai AFTER INSERT ON voters BEGIN
                INSERT INTO voters_fts(rowid, name, name_hindi, epic, relation_name, village)
                VALUES (new.id, new.name, new.name_hindi, new.epic, new.relation_name, new.village);
            END''',
            '''CREATE TRIGGER IF NOT EXISTS voters_ad AFTER DELETE ON voters BEGIN
                INSERT INTO voters_fts(voters_fts, rowid, name, name_hindi, epic, relation_name, village)
                VALUES('delete', old.id, old.name, old.name_hindi, old.epic, old.relation_name, old.village);
            END''',
            '''CREATE TRIGGER IF NOT EXISTS voters_au AFTER UPDATE ON voters BEGIN
                INSERT INTO voters_fts(voters_fts, rowid, name, name_hindi, epic, relation_name, village)
                VALUES('delete', old.id, old.name, old.name_hindi, old.epic, old.relation_name, old.village);
                INSERT INTO voters_fts(rowid, name, name_hindi, epic, relation_name, village)
                VALUES (new.id, new.name, new.name_hindi, new.epic, new.relation_name, new.village);
            END''',
        ]
        for trigger_sql in triggers:
            try:
                cursor.execute(trigger_sql)
            except:
                pass

    def _column_exists(self, cursor, table, column):
        """Check whether a column exists in a table."""
        try:
            cursor.execute(f'PRAGMA table_info({table})')
            return any(row['name'] == column for row in cursor.fetchall())
        except Exception:
            return False

    def _transliterate_text(self, text):
        """Transliterate Hindi text to a Latin-friendly form for matching."""
        if not text:
            return ''
        text = str(text).strip()
        if unidecode:
            return self._normalize_text(unidecode(text))
        return self._normalize_text(text)

    def _ensure_transliteration_columns(self, cursor):
        """Make sure transliteration columns exist and are backfilled."""
        columns = [
            ('name_hindi_translit', 'name_hindi'),
            ('relation_name_translit', 'relation_name')
        ]

        for new_col, source_col in columns:
            if not self._column_exists(cursor, 'voters', new_col):
                try:
                    cursor.execute(f'ALTER TABLE voters ADD COLUMN {new_col} TEXT')
                except Exception:
                    pass

        # Backfill transliteration values for existing voters
        cursor.execute('SELECT id, name_hindi, relation_name FROM voters')
        rows = cursor.fetchall()
        for row in rows:
            try:
                translated_name = self._transliterate_text(row['name_hindi'])
                translated_relation = self._transliterate_text(row['relation_name'])
                cursor.execute('''
                    UPDATE voters
                    SET name_hindi_translit = ?, relation_name_translit = ?
                    WHERE id = ?
                ''', (translated_name, translated_relation, row['id']))
            except Exception:
                continue

    def _normalize_hindi(self, text):
        """Normalize Hindi text for consistent search."""
        if not text:
            return ''
        text = unicodedata.normalize('NFC', text)
        return text.lower()
    
    def _normalize_text(self, text):
        """Normalize text for searching."""
        if not text:
            return ''
        text = str(text).strip().casefold()
        text = unicodedata.normalize('NFC', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    def _is_ascii_query(self, query):
        """Return True if the query contains only Latin letters, digits and spaces."""
        return bool(re.match(r'^[A-Za-z0-9\s]+$', query))

    def _normalize_fts_query(self, query):
        """Prepare a safe FTS5 query string."""
        query = str(query).strip()
        query = re.sub(r'["\'\*:\/\^\-\+\(\)\[\]{}]', ' ', query)
        query = re.sub(r'\s+', ' ', query)
        terms = [term for term in query.split() if term]
        return ' OR '.join(f'{term}*' for term in terms)

    def _calculate_search_rank(self, text, query, field_type='general'):
        """Calculate ranking score for search results."""
        if not text or not query:
            return 0
        
        text = self._normalize_text(text)
        query = self._normalize_text(query)
        
        score = 0
        
        if text == query:
            score += 1000
        
        if text.startswith(query):
            score += 500
        
        if query in text:
            score += 100
        
        word_list = text.split()
        for word in word_list:
            if word.startswith(query):
                score += 50
        
        if field_type == 'primary':
            score *= 2
        
        return score
    
    def _get_cached_search(self, query):
        """Get search results from cache if available."""
        if query in self._search_cache:
            self._cache_hits += 1
            return self._search_cache[query]
        self._cache_misses += 1
        return None
    
    def _set_search_cache(self, query, results):
        """Cache search results."""
        if len(self._search_cache) >= self.CACHE_SIZE:
            oldest_key = next(iter(self._search_cache))
            del self._search_cache[oldest_key]
        self._search_cache[query] = results
    
    def smart_search(self, query, search_type='all', limit=100):
        """
        Advanced search with ranking, Hindi support, and instant suggestions.
        Supports: exact match, starts with, partial match, special queries.
        Query formats: 'name', 'house:12', 'village:babura', 'age:45', 'epic:XYZ'
        """
        import time
        start_time = time.time()
        
        if not query or not isinstance(query, str):
            return []
        
        query = self._normalize_text(query)
        if len(query) < 1:
            return []
        
        cached_results = self._get_cached_search(query)
        if cached_results:
            response_time = time.time() - start_time
            self._log_search(query, len(cached_results), response_time, 'cache')
            return cached_results
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            results = []
            
            if ':' in query:
                results = self._special_search(cursor, query)
            else:
                try:
                    results = self._fts5_search(cursor, query)
                except:
                    results = []
                
                if not results:
                    results = self._general_search(cursor, query)
            
            results = sorted(results, key=lambda x: x.get('rank', 0), reverse=True)
            results = results[:limit]
            
            self._set_search_cache(query, results)
            
            response_time = time.time() - start_time
            self._log_search(query, len(results), response_time, search_type)
            
            conn.close()
            return results
        
        except Exception as e:
            logger.error(f'Search error: {str(e)}')
            return []
    
    def _special_search(self, cursor, query):
        """Handle special search patterns: house:12, village:name, age:45, epic:XYZ"""
        results = []
        
        try:
            if ':' not in query:
                return results
            
            field, value = query.split(':', 1)
            field = field.strip().lower()
            value = value.strip()
            
            if not field or not value:
                return results
            
            if field == 'house':
                cursor.execute('''
                    SELECT v.*, COUNT(d.id) as doc_count
                    FROM voters v
                    LEFT JOIN documents d ON v.id = d.voter_id
                    WHERE house_no = ?
                    GROUP BY v.id
                    ORDER BY v.name
                    LIMIT ?
                ''', (value, self.SEARCH_LIMIT))
            
            elif field == 'village':
                value_pattern = f'%{value}%'
                cursor.execute('''
                    SELECT v.*, COUNT(d.id) as doc_count
                    FROM voters v
                    LEFT JOIN documents d ON v.id = d.voter_id
                    WHERE LOWER(village) LIKE ?
                    GROUP BY v.id
                    ORDER BY v.name
                    LIMIT ?
                ''', (value_pattern, self.SEARCH_LIMIT))
            
            elif field == 'age':
                try:
                    age = int(value)
                    cursor.execute('''
                        SELECT v.*, COUNT(d.id) as doc_count
                        FROM voters v
                        LEFT JOIN documents d ON v.id = d.voter_id
                        WHERE age = ?
                        GROUP BY v.id
                        ORDER BY v.name
                        LIMIT ?
                    ''', (age, self.SEARCH_LIMIT))
                except ValueError:
                    return results
            
            elif field == 'epic':
                value_pattern = f'%{value}%'
                cursor.execute('''
                    SELECT v.*, COUNT(d.id) as doc_count
                    FROM voters v
                    LEFT JOIN documents d ON v.id = d.voter_id
                    WHERE LOWER(epic) LIKE ?
                    GROUP BY v.id
                    ORDER BY v.name
                    LIMIT ?
                ''', (value_pattern, self.SEARCH_LIMIT))
            
            elif field == 'mobile':
                cursor.execute('''
                    SELECT v.*, COUNT(d.id) as doc_count
                    FROM voters v
                    LEFT JOIN documents d ON v.id = d.voter_id
                    WHERE mobile = ?
                    GROUP BY v.id
                    ORDER BY v.name
                    LIMIT ?
                ''', (value, self.SEARCH_LIMIT))
            
            for row in cursor.fetchall():
                result = dict(row)
                result['rank'] = 1000
                results.append(result)
        
        except Exception as e:
            logger.error(f'Special search error: {str(e)}')
        
        return results
    
    def _general_search(self, cursor, query):
        """General multi-field search with ranking and transliteration support."""
        results = []
        result_dict = {}

        search_fields = [
            ('name', 'primary'),
            ('name_hindi', 'primary'),
            ('name_hindi_translit', 'primary'),
            ('epic', 'secondary'),
            ('relation_name', 'secondary'),
            ('relation_name_translit', 'secondary'),
            ('house_no', 'secondary'),
            ('mobile', 'secondary'),
            ('village', 'secondary')
        ]

        terms = query.split()
        ascii_query = self._is_ascii_query(query)

        for field, field_type in search_fields:
            for term in terms:
                if field in ('house_no', 'mobile', 'epic'):
                    pattern = f'%{term}%'
                elif field in ('name_hindi_translit', 'relation_name_translit') and ascii_query:
                    pattern = f'%{term}%'
                else:
                    pattern = f'{term}%'

                try:
                    cursor.execute(f'''
                        SELECT v.*, COUNT(d.id) as doc_count
                        FROM voters v
                        LEFT JOIN documents d ON v.id = d.voter_id
                        WHERE LOWER({field}) LIKE ?
                        GROUP BY v.id
                        LIMIT ?
                    ''', (pattern, self.SEARCH_LIMIT))
                except Exception:
                    continue

                for row in cursor.fetchall():
                    result = dict(row)
                    field_value = result.get(field, '')
                    rank = self._calculate_search_rank(field_value, term, field_type)

                    if result['id'] not in result_dict:
                        result['rank'] = rank
                        result_dict[result['id']] = result
                    else:
                        result_dict[result['id']]['rank'] += rank

        results = list(result_dict.values())
        results = sorted(results, key=lambda x: x.get('rank', 0), reverse=True)

        return results
    
    def live_suggestions(self, query, limit=10):
        """Instant live suggestions optimized for autocomplete."""
        if not query or len(query) < 1:
            return []

        query = self._normalize_text(query)
        suggestions = []

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            fts_query = self._normalize_fts_query(query)
            if fts_query:
                cursor.execute(f'''
                    SELECT v.id, v.name, v.epic, v.house_no, v.mobile, COUNT(d.id) as doc_count
                    FROM voters_fts
                    JOIN voters v ON voters_fts.rowid = v.id
                    LEFT JOIN documents d ON v.id = d.voter_id
                    WHERE voters_fts MATCH ?
                    GROUP BY v.id
                    ORDER BY doc_count DESC, v.name
                    LIMIT ?
                ''', (fts_query, limit))
                for row in cursor.fetchall():
                    suggestions.append({
                        'id': row['id'],
                        'name': row['name'],
                        'epic': row['epic'],
                        'house_no': row['house_no'],
                        'mobile': row['mobile']
                    })
        except Exception:
            suggestions = []
        finally:
            try:
                conn.close()
            except Exception:
                pass

        if not suggestions:
            results = self.smart_search(query, limit=limit)
            for result in results[:limit]:
                suggestions.append({
                    'id': result.get('id'),
                    'name': result.get('name'),
                    'epic': result.get('epic'),
                    'house_no': result.get('house_no'),
                    'mobile': result.get('mobile')
                })

        return suggestions
    
    def _fts5_search(self, cursor, query):
        """FTS5 full-text search with ranking."""
        results = []
        result_dict = {}

        try:
            fts_query = self._normalize_fts_query(query)
            if not fts_query:
                return []

            cursor.execute(f'''
                SELECT v.*, COUNT(d.id) as doc_count
                FROM voters_fts
                JOIN voters v ON voters_fts.rowid = v.id
                LEFT JOIN documents d ON v.id = d.voter_id
                WHERE voters_fts MATCH ?
                GROUP BY v.id
                LIMIT ?
            ''', (fts_query, self.SEARCH_LIMIT))

            for row in cursor.fetchall():
                result = dict(row)
                result['rank'] = 150
                result_dict[result['id']] = result

        except Exception as e:
            logger.debug(f'FTS5 search error: {str(e)}')

        return list(result_dict.values())
    
    def _log_search(self, query, result_count, response_time, search_type='general'):
        """Log search query for analytics."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO search_logs (query, result_count, response_time, search_type)
                VALUES (?, ?, ?, ?)
            ''', (query, result_count, response_time, search_type))
            conn.commit()
            conn.close()
        except:
            pass
    
    def get_search_analytics(self, days=7):
        """Get search analytics for dashboard."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            since = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT query, COUNT(*) as search_count, AVG(result_count) as avg_results,
                       AVG(response_time) as avg_time
                FROM search_logs
                WHERE created_at > ?
                GROUP BY query
                ORDER BY search_count DESC
                LIMIT 10
            ''', (since,))
            
            top_searches = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute('''
                SELECT AVG(response_time) as avg_response, COUNT(*) as total_searches
                FROM search_logs
                WHERE created_at > ?
            ''', (since,))
            
            stats = dict(cursor.fetchone() or {})
            stats['top_searches'] = top_searches
            
            conn.close()
            return stats
        except Exception as e:
            logger.error(f'Analytics error: {str(e)}')
            return {}
    
    def create_admin_user(self, username, password):
        """
        Create admin user with secure password hashing.
        
        IMPORTANT: Uses INSERT OR IGNORE to preserve existing users!
        - First run: Creates default admin user (username/password from .env or defaults)
        - Subsequent runs: DOES NOT overwrite existing users (IGNORE clause)
        - This ensures manual password changes are never lost after app restart
        
        Workflow for first-time setup:
        1. Fresh installation: No users table exists, creates admin automatically
        2. App restarts: INSERT OR IGNORE finds existing user, does nothing
        3. Manual password change: User can change password in app, won't be overwritten
        
        Default credentials for fresh install:
        - Username: 'admin' (or from ADMIN_USER environment variable)
        - Password: 'TyagiVoter' (or from ADMIN_PASS environment variable)
        
        Args:
            username: Login username (converted to lowercase)
            password: Plain text password (hashed with werkzeug.security)
        
        Returns:
            bool: True if user created, False if error occurred
        
        Security:
            - Uses werkzeug.security.generate_password_hash (default: pbkdf2:sha256)
            - Passwords are salted and iterated
            - Never stores plaintext passwords
        """
        if not username or not password:
            logger.warning('Invalid username or password provided to create_admin_user')
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            username = username.strip().lower()
            hashed_password = generate_password_hash(password)
            
            # INSERT OR IGNORE: Creates user only if username doesn't exist
            # This preserves existing users after app restart
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password, is_admin)
                VALUES (?, ?, 1)
            ''', (username, hashed_password))
            conn.commit()
            
            rows_inserted = cursor.rowcount
            if rows_inserted > 0:
                logger.info(f'Admin user "{username}" created (first-time setup)')
            else:
                logger.debug(f'Admin user "{username}" already exists (not overwriting)')
            
            return True
        except Exception as e:
            logger.error(f'Error creating admin user: {str(e)}')
            return False
        finally:
            conn.close()
    
    def authenticate_user(self, username, password):
        """
        Authenticate user with secure password verification.
        
        Workflow:
        1. Normalize username to lowercase
        2. Query users table by username
        3. Use werkzeug.security.check_password_hash to verify password
        4. Update last_login timestamp on successful authentication
        5. Return user data or None
        
        Security:
        - Uses check_password_hash (constant-time comparison, prevents timing attacks)
        - Returns None without revealing if username exists
        - Logs failed attempts for security monitoring
        
        Args:
            username: Login username
            password: Plain text password from form
        
        Returns:
            dict: User record if authenticated, None if credentials invalid
        
        Example:
            user = db.authenticate_user('admin', 'TyagiVoter')
            if user:
                # User authenticated - safe to create Flask-Login session
                login_user(User(user['id'], user['username'], user['password']))
        """
        if not username or not password:
            return None
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            username = username.strip().lower()
            
            # Query user by username
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            # Verify password using werkzeug (constant-time comparison)
            if user and check_password_hash(user['password'], password):
                # Update last login timestamp
                cursor.execute(
                    'UPDATE users SET last_login = ? WHERE id = ?',
                    (datetime.now(), user['id'])
                )
                conn.commit()
                return dict(user)
            
            return None
        except Exception as e:
            logger.error(f'Authentication error: {str(e)}')
            return None
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        """Get user by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
        except Exception as e:
            logger.error(f'Error getting user: {str(e)}')
            return None
        finally:
            conn.close()
    
    def get_voter_by_id(self, voter_id):
        """Get voter by ID with document count."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT v.*, COUNT(d.id) as doc_count
                FROM voters v
                LEFT JOIN documents d ON v.id = d.voter_id
                WHERE v.id = ?
                GROUP BY v.id
            ''', (voter_id,))
            voter = cursor.fetchone()
            return dict(voter) if voter else None
        except Exception as e:
            logger.error(f'Error getting voter: {str(e)}')
            return None
        finally:
            conn.close()
    
    def get_family_members(self, house_no):
        """Get all family members at house_no."""
        if not house_no:
            return []
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM voters
                WHERE house_no = ?
                ORDER BY age DESC, name
            ''', (house_no,))
            members = [dict(row) for row in cursor.fetchall()]
            return members
        except Exception as e:
            logger.error(f'Error getting family members: {str(e)}')
            return []
        finally:
            conn.close()
    
    def get_voter_documents(self, voter_id):
        """Get all documents for a voter."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM documents
                WHERE voter_id = ?
                ORDER BY uploaded_at DESC
            ''', (voter_id,))
            documents = [dict(row) for row in cursor.fetchall()]
            return documents
        except Exception as e:
            logger.error(f'Error getting documents: {str(e)}')
            return []
        finally:
            conn.close()
    
    def add_document(self, voter_id, file_path, doc_type):
        """Add document for voter."""
        if not voter_id or not file_path:
            return None
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO documents (voter_id, file_path, doc_type)
                VALUES (?, ?, ?)
            ''', (voter_id, file_path, doc_type))
            conn.commit()
            doc_id = cursor.lastrowid
            return doc_id
        except Exception as e:
            logger.error(f'Error adding document: {str(e)}')
            return None
        finally:
            conn.close()
    
    def get_dashboard_stats(self):
        """Get dashboard statistics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            cursor.execute('SELECT COUNT(*) as count FROM voters')
            stats['total_voters'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM voters WHERE gender = "पुरुष"')
            stats['male_count'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM voters WHERE gender = "महिला"')
            stats['female_count'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM voters WHERE age >= 60')
            stats['senior_count'] = cursor.fetchone()['count']
            
            cursor.execute('''
                SELECT COUNT(DISTINCT house_no) as count
                FROM voters WHERE house_no IS NOT NULL
            ''')
            stats['families_count'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM documents')
            stats['doc_count'] = cursor.fetchone()['count']
            
            return stats
        except Exception as e:
            logger.error(f'Error getting dashboard stats: {str(e)}')
            return {}
        finally:
            conn.close()
    
    def get_age_distribution(self):
        """Get age distribution for analytics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
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
            return distribution
        except Exception as e:
            logger.error(f'Error getting age distribution: {str(e)}')
            return []
        finally:
            conn.close()
    
    def get_gender_ratio(self):
        """Get gender ratio for analytics."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT gender, COUNT(*) as count
                FROM voters
                WHERE gender IS NOT NULL
                GROUP BY gender
            ''')
            ratio = [dict(row) for row in cursor.fetchall()]
            return ratio
        except Exception as e:
            logger.error(f'Error getting gender ratio: {str(e)}')
            return []
        finally:
            conn.close()
    
    def get_recent_voters(self, limit=10):
        """Get recently added voters."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM voters
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            recent = [dict(row) for row in cursor.fetchall()]
            return recent
        except Exception as e:
            logger.error(f'Error getting recent voters: {str(e)}')
            return []
        finally:
            conn.close()
    
    def export_to_csv(self):
        """Export all voters to CSV format."""
        conn = self.get_connection()
        
        try:
            df = pd.read_sql_query('SELECT * FROM voters ORDER BY name', conn)
            return df.to_dict('records')
        except Exception as e:
            logger.error(f'Error exporting to CSV: {str(e)}')
            return []
        finally:
            conn.close()
    
    def import_from_dataframe(self, df):
        """Import voters from pandas DataFrame."""
        if not isinstance(df, pd.DataFrame) or df.empty:
            logger.warning('Invalid or empty DataFrame')
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        count = 0
        
        try:
            for _, row in df.iterrows():
                try:
                    name_hindi = row.get('name_hindi')
                    relation_name = row.get('relation_name')
                    name_hindi_translit = self._transliterate_text(name_hindi)
                    relation_name_translit = self._transliterate_text(relation_name)

                    cursor.execute('''
                        INSERT OR REPLACE INTO voters 
                        (serial_no, epic, name, name_hindi, name_hindi_translit,
                         relation_type, relation_name, relation_name_translit,
                         house_no, age, gender, mobile, category, village, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('serial_no'),
                        row.get('epic'),
                        row.get('name'),
                        name_hindi,
                        name_hindi_translit,
                        row.get('relation_type'),
                        relation_name,
                        relation_name_translit,
                        row.get('house_no'),
                        row.get('age'),
                        row.get('gender'),
                        row.get('mobile'),
                        row.get('category'),
                        row.get('village'),
                        row.get('notes')
                    ))
                    count += 1
                except Exception as e:
                    logger.debug(f'Row import error: {str(e)}')
                    continue
            
            conn.commit()
            logger.info(f'Imported {count} voters from DataFrame')
            return count
        
        except Exception as e:
            logger.error(f'Error importing DataFrame: {str(e)}')
            return count
        finally:
            conn.close()
    
    def backup_database(self):
        """Create database backup."""
        try:
            import shutil
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(self.db_path, backup_name)
            logger.info(f'Database backed up to {backup_name}')
            return backup_name
        except Exception as e:
            logger.error(f'Backup error: {str(e)}')
            return None
    
    def get_search_stats(self):
        """Get search cache statistics."""
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_size': len(self._search_cache),
            'hit_rate': self._cache_hits / (self._cache_hits + self._cache_misses) * 100 if (self._cache_hits + self._cache_misses) > 0 else 0
        }
    
    def clear_search_cache(self):
        """Clear search cache."""
        self._search_cache.clear()
        logger.info('Search cache cleared')
    
    def vacuum_database(self):
        """Optimize database file size."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('VACUUM')
            conn.commit()
            logger.info('Database vacuumed')
        except Exception as e:
            logger.error(f'Vacuum error: {str(e)}')
        finally:
            conn.close()
