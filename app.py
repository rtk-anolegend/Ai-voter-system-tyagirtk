# ============================================================================
# AI-Voter Management System
# Production-ready Flask application with secure authentication and LAN support
# ============================================================================

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    send_file,
    send_from_directory
)

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# Flask-Talisman is disabled in this project because it enforces HTTPS/CSP policies
# that break development and LAN access for Raspberry Pi/local network usage.
# from flask_talisman import Talisman

from database import Database
from werkzeug.utils import secure_filename

import io
import os
import pandas as pd
import logging
import time
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)

# Initialize rate limiter for security
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Security middleware - Flask-Talisman is intentionally disabled for local LAN
# and mobile development. Enabling Talisman here would enforce HTTPS-related
# headers and CSP rules that break HTTP access on Raspberry Pi and mobile LAN browsers.
# Talisman(
#     app,
#     force_https=False,  # Disabled for LAN access (localhost, 127.0.0.1, local IPs)
#     strict_transport_security=False,
#     content_security_policy={
#         'default-src': "'self'",
#         'script-src': ["'self'", "'unsafe-inline'", "cdnjs.cloudflare.com", "fonts.googleapis.com"],
#         'style-src': ["'self'", "'unsafe-inline'", "fonts.googleapis.com", "cdnjs.cloudflare.com"],
#         'img-src': ["'self'", "data:", "https:"],
#     }
# )

# ============================================================================
# Application Configuration - Session Management & Security
# ============================================================================
# SECRET_KEY: Critical for session security. Change in production!
# Loaded from environment variable or uses fallback (not suitable for production)
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key-change-in-production-tyagi-voter-system')
app.config['SECRET_KEY'] = SECRET_KEY

# Session and Cookie Configuration for LAN/Mobile Access
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ============================================================================
# SESSION PERSISTENCE CONFIGURATION
# ============================================================================
# These settings enable session persistence across different access methods:
# - localhost (127.0.0.1:5000)
# - Direct IP access (192.168.x.x:5000)
# - Mobile browsers and tablets
# - HTTP-only local development and Raspberry Pi LAN usage
# ============================================================================
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript from accessing cookies
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow LAN access while maintaining CSRF protection
app.config['SESSION_COOKIE_SECURE'] = False  # Must remain False for HTTP LAN/mobile access
app.config['SESSION_COOKIE_NAME'] = 'voter_system_session'  # Custom session cookie name
app.config['SESSION_COOKIE_PATH'] = '/'  # Cookie available to all app routes
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # Session expiry for logged in users
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Refresh session lifetime on each request
app.config['REMEMBER_COOKIE_HTTPONLY'] = True  # Protect remember cookies from JavaScript access
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'  # Allow remember cookie on mobile/LAN access
app.config['REMEMBER_COOKIE_SECURE'] = False  # Remember cookie should also work over HTTP locally
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
app.config['JSON_SORT_KEYS'] = False

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
ALLOWED_IMPORT_EXTENSIONS = {'csv', 'xlsx'}

# Database initialization
db = Database('data/voter_system.db')

# ============================================================================
# FLASK-LOGIN CONFIGURATION
# ============================================================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = 'basic'  # Basic protection to keep Flask-Login sessions LAN/mobile friendly
login_manager.login_view = 'login'  # Redirect to login page when @login_required fails
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


class User(UserMixin):
    """
    User model with Flask-Login integration.
    Represents an authenticated user in the system.
    
    Attributes:
        id: Unique user identifier (from database)
        username: User's login username
        password: Hashed password (never used in login, only for reference)
    
    Note: Do NOT store or use plaintext passwords. Password verification
    happens in database.authenticate_user() using check_password_hash().
    """
    
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password  # This is just a reference; actual password check uses werkzeug
    
    def get_id(self):
        """
        Return the unique identifier for this user.
        CRITICAL: Flask-Login requires this method for session serialization.
        This enables persistence across localhost, 127.0.0.1, and LAN IPs.
        
        Returns:
            str: The user ID as a string (required by Flask-Login)
        """
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login callback to load user from session.
    Called automatically when a user has a valid session.
    
    This function enables session persistence across all access methods:
    - localhost:5000
    - 127.0.0.1:5000
    - LAN IP addresses (e.g., 192.168.1.100:5000)
    - Mobile/tablet browsers
    
    Args:
        user_id: The user ID stored in the session
    
    Returns:
        User object if found, None if user doesn't exist
    """
    user = db.get_user_by_id(user_id)
    if user:
        return User(user['id'], user['username'], user['password'])
    return None


def allowed_file(filename):
    """Check if uploaded file has allowed extension for document upload."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_import_file(filename):
    """Check if uploaded file has allowed import extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMPORT_EXTENSIONS


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Home page redirects to login or dashboard based on authentication."""
    return redirect(url_for('login'))


@app.route('/favicon.ico')
def favicon():
    """Serve favicon from static folder."""
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """
    User authentication endpoint.
    
    GET: Display login form
    POST: Process login credentials
    
    Session Persistence:
    - Sets session.permanent = True for 2-hour persistence
    - Works across: localhost, 127.0.0.1, LAN IPs, mobile browsers
    - Cookies configured for LAN access (not HTTPS/secure required)
    
    Success: Redirects to /dashboard with valid session
    Failure: Returns login form with error message
    
    Security:
    - Rate limited to 5 attempts per minute
    - Passwords hashed with werkzeug.security
    - Session ID serialized by Flask-Login
    """
    # If user is already logged in, redirect to dashboard
    if request.method == 'GET' and current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        # Validate input
        if not username or not password:
            return render_template('login.html', error='Username and password required')
        
        # Authenticate user
        user = db.authenticate_user(username, password)
        if user:
            # Create User object for Flask-Login
            login_user(User(user['id'], user['username'], user['password']), remember=False)
            
            # Enable session persistence (critical for LAN/mobile)
            session.permanent = True
            session['is_admin'] = True
            
            logger.info(f'User {username} logged in from {request.remote_addr}')
            
            # Redirect to dashboard (NOT back to login page)
            return redirect(url_for('dashboard'))
        
        logger.warning(f'Failed login attempt for {username} from {request.remote_addr}')
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """
    Logout user and clear session.
    Clears all session data and destroys the session cookie.
    """
    username = current_user.username if current_user else 'unknown'
    logout_user()
    session.clear()
    logger.info(f'User {username} logged out from {request.remote_addr}')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_dashboard_stats()
    age_distribution = db.get_age_distribution()
    gender_ratio = db.get_gender_ratio()
    recent_voters = db.get_recent_voters(10)
    search_analytics = db.get_search_analytics(days=7)
    
    return render_template(
        'dashboard.html',
        stats=stats,
        age_distribution=age_distribution or [],
        gender_ratio=gender_ratio or [],
        recent_voters=recent_voters or [],
        search_analytics=search_analytics or {}
    )


@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    results = []
    
    if query and len(query) >= 2:
        results = db.smart_search(query)
    
    return render_template('search.html', results=results, query=query)


@app.route('/api/search')
@login_required
@limiter.limit("60 per minute")
def api_search():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'general')
    limit = request.args.get('limit', 100, type=int)
    
    if not query or len(query) < 2:
        return jsonify({'results': [], 'count': 0})
    
    if limit > 200:
        limit = 200
    
    try:
        results = db.smart_search(query, search_type=search_type, limit=limit)
        return jsonify({
            'results': results,
            'count': len(results),
            'query': query,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'Search API error: {str(e)}')
        return jsonify({'results': [], 'count': 0, 'error': str(e)}), 500


@app.route('/api/suggestions')
@login_required
@limiter.limit("120 per minute")
def api_suggestions():
    """Live suggestions for autocomplete."""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    
    if not query or len(query) < 1:
        return jsonify({'suggestions': []})
    
    if limit > 50:
        limit = 50
    
    try:
        suggestions = db.live_suggestions(query, limit=limit)
        return jsonify({
            'suggestions': suggestions,
            'count': len(suggestions),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'Suggestions API error: {str(e)}')
        return jsonify({'suggestions': [], 'error': str(e)}), 500


@app.route('/api/analytics')
@login_required
def api_analytics():
    """Search analytics endpoint."""
    days = request.args.get('days', 7, type=int)
    
    if days < 1 or days > 90:
        days = 7
    
    try:
        analytics = db.get_search_analytics(days=days)
        cache_stats = db.get_search_stats()
        
        return jsonify({
            'analytics': analytics,
            'cache': cache_stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f'Analytics API error: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/voter/<int:voter_id>')
@login_required
def voter_profile(voter_id):
    voter = db.get_voter_by_id(voter_id)
    
    if not voter:
        return render_template('404.html'), 404
    
    family_members = db.get_family_members(voter.get('house_no'))
    documents = db.get_voter_documents(voter_id)
    
    return render_template(
        'profile.html',
        voter=voter,
        family_members=family_members,
        documents=documents
    )


@app.route('/upload/<int:voter_id>', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def upload_document(voter_id):
    try:
        file = request.files.get('document')
        doc_type = request.form.get('doc_type', 'other').strip()
        
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{voter_id}_{timestamp}_{original_filename}"
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(save_path)
        
        file_url = f"/document/{filename}"
        db.add_document(voter_id, file_url, doc_type)
        
        logger.info(f'Document uploaded for voter {voter_id}')
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully',
            'file_url': file_url,
            'filename': filename
        })
    
    except Exception as e:
        logger.error(f'Upload error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/document/<filename>')
@login_required
def serve_document(filename):
    try:
        secure_name = secure_filename(filename)
        if secure_name != filename:
            return render_template('404.html'), 404
        
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
    except Exception as e:
        logger.error(f'Document serve error: {str(e)}')
        return render_template('404.html'), 404


@app.route('/image/<path:filename>')
def serve_image(filename):
    """Serve images with fallback to default-avatar."""
    try:
        secure_name = secure_filename(filename)
        image_path = os.path.join('static', 'images', secure_name)
        
        if os.path.exists(image_path):
            return send_from_directory('static/images', secure_name)
        else:
            return send_from_directory('static/images', 'default-avatar.png')
    except:
        return send_from_directory('static/images', 'default-avatar.png')


@app.route('/export/csv')
@login_required
@limiter.limit("5 per hour")
def export_csv():
    try:
        data = db.export_to_csv()
        df = pd.DataFrame(data)
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)

        filename = f"voter_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        logger.info(f'CSV exported: {filename}')

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv; charset=utf-8'
        )
    except Exception as e:
        logger.error(f'CSV export error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/export/excel')
@login_required
@limiter.limit("5 per hour")
def export_excel():
    try:
        data = db.export_to_csv()
        df = pd.DataFrame(data)
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        filename = f"voter_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        logger.info(f'Excel exported: {filename}')

        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f'Excel export error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/import/csv', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def import_csv():
    file = request.files.get('csv_file')
    
    if not file or file.filename == '':
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    filename = secure_filename(file.filename)
    if not allowed_import_file(filename):
        return jsonify({'success': False, 'error': 'Only CSV and XLSX files are allowed for import'}), 400

    file_ext = filename.rsplit('.', 1)[1].lower()

    try:
        imported_count = 0
        if file_ext == 'csv':
            reader = pd.read_csv(
                file,
                encoding='utf-8-sig',
                dtype=str,
                keep_default_na=False,
                on_bad_lines='skip',
                chunksize=1000
            )
            for chunk in reader:
                imported_count += db.import_from_dataframe(chunk)
        else:
            df = pd.read_excel(file, engine='openpyxl', dtype=str)
            imported_count = db.import_from_dataframe(df)

        logger.info(f'File imported: {filename} ({imported_count} records)')

        return jsonify({
            'success': True,
            'imported': imported_count,
            'message': f'Successfully imported {imported_count} voters from {filename}'
        })
    except Exception as e:
        logger.error(f'CSV import error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/backup')
@login_required
@limiter.limit("5 per hour")
def backup():
    try:
        backup_file = db.backup_database()
        if backup_file:
            logger.info(f'Database backed up: {backup_file}')
            return send_file(backup_file, as_attachment=True, download_name=backup_file)
        return jsonify({'success': False, 'error': 'Backup failed'}), 500
    except Exception as e:
        logger.error(f'Backup error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/vacuum')
@login_required
def vacuum_database():
    """Optimize database."""
    try:
        db.vacuum_database()
        logger.info('Database vacuumed')
        return jsonify({'success': True, 'message': 'Database optimized'})
    except Exception as e:
        logger.error(f'Vacuum error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/cache-clear')
@login_required
def clear_cache():
    """Clear search cache."""
    try:
        db.clear_search_cache()
        logger.info('Search cache cleared')
        return jsonify({'success': True, 'message': 'Cache cleared'})
    except Exception as e:
        logger.error(f'Cache clear error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors."""
    logger.error(f'Internal error: {str(error)}')
    return render_template('500.html'), 500


@app.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors."""
    return jsonify({'error': 'Forbidden'}), 403


@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded (429 Too Many Requests)."""
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429


@app.before_request
def before_request():
    """
    Hook executed before every request.
    Ensures session persistence settings are applied consistently.
    """
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=2)


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    """
    Application initialization and startup.
    
    Workflow:
    1. Create required directories (uploads, data)
    2. Initialize database with tables and indexes
    3. Create default admin user (first-time setup only, INSERT OR IGNORE)
    4. Start Flask development server
    
    Important Notes:
    ----------------
    - This runs in PRODUCTION MODE (debug=False, threaded=True)
    - Listens on 0.0.0.0:5000 (accessible from all IPs on network)
    - Default admin credentials: admin / TyagiVoter
    - Change SECRET_KEY in production via environment variable
    
    Deployment:
    -----------
    - Raspberry Pi: Run with python3 app.py
    - Production: Use WSGI server (gunicorn, waitress, etc.)
    - LAN Access: http://192.168.x.x:5000 (or local IP)
    - Mobile: Use same IP and port from tablet/phone browser
    
    Database Path:
    ---------------
    Database file: data/voter_system.db
    Checked automatically at startup, created if missing
    
    Environment Variables:
    ----------------------
    - SECRET_KEY: Session encryption key (change in production!)
    - ADMIN_USER: Default admin username (default: 'admin')
    - ADMIN_PASS: Default admin password (default: 'TyagiVoter')
    - FLASK_ENV: Set to 'production' in production
    """
    
    # Create required directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # Initialize default admin user (first-time setup only)
    # Uses INSERT OR IGNORE - does NOT overwrite existing users
    db.create_admin_user(
        os.environ.get('ADMIN_USER', 'admin'),
        os.environ.get('ADMIN_PASS', 'TyagiVoter')
    )
    
    logger.info('=' * 70)
    logger.info('Starting AI-Voter Management System')
    logger.info('=' * 70)
    logger.info(f'Database: data/voter_system.db')
    logger.info(f'Listening on: 0.0.0.0:5000')
    logger.info(f'LAN Access: http://<your-local-ip>:5000')
    logger.info(f'First-time credentials: admin / TyagiVoter')
    logger.info('=' * 70)
    
    # Start Flask application
    app.run(
        host='0.0.0.0',  # Listen on all network interfaces
        port=5000,
        debug=False,  # Production mode
        threaded=True  # Enable threading for concurrent requests
    )
