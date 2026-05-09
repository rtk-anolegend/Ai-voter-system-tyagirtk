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
    logout_user
)

from flask_limiter import Limiter

from flask_limiter.util import get_remote_address

from database import Database

from werkzeug.utils import secure_filename

import os
import pandas as pd

from datetime import (
    datetime,
    timedelta
)

# =========================================================
# APP INITIALIZATION
# =========================================================

# =========================================================
# APP INITIALIZATION
# =========================================================

app = Flask(__name__)

# =========================================================
# RATE LIMITER
# =========================================================

limiter = Limiter(

    get_remote_address,

    app=app,

    default_limits=[

        "200 per day",

        "50 per hour"
    ]
)

# =========================================================
# CONFIGURATION
# =========================================================

app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY'
)

if not app.config['SECRET_KEY']:

    raise ValueError(
        'SECRET_KEY not found'
    )

app.config['UPLOAD_FOLDER'] = 'uploads'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

app.config['SESSION_COOKIE_HTTPONLY'] = True

app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

app.config['SESSION_COOKIE_SECURE'] = False

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    hours=1
)
# =========================================================
# ALLOWED FILE TYPES
# =========================================================

ALLOWED_EXTENSIONS = {
    'pdf',
    'png',
    'jpg',
    'jpeg',
    'doc',
    'docx'
}


# =========================================================
# DATABASE
# =========================================================

db = Database('data/voter_system.db')


# =========================================================
# LOGIN MANAGER
# =========================================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = 'login'


# =========================================================
# USER CLASS
# =========================================================

class User(UserMixin):

    def __init__(self, id, username, password):

        self.id = id
        self.username = username
        self.password = password


# =========================================================
# LOAD USER
# =========================================================

@login_manager.user_loader
def load_user(user_id):

    user = db.get_user_by_id(user_id)

    if user:

        return User(
            user['id'],
            user['username'],
            user['password']
        )

    return None


# =========================================================
# FILE VALIDATION
# =========================================================

def allowed_file(filename):

    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# =========================================================
# HOME ROUTE
# =========================================================

@app.route('/')
def index():

    return redirect(
        url_for('login')
    )


# =========================================================
# LOGIN
# =========================================================

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():

    if request.method == 'POST':

        username = request.form.get(
            'username',
            ''
        ).strip()

        password = request.form.get(
            'password',
            ''
        ).strip()

        user = db.authenticate_user(
            username,
            password
        )

        # =====================================
        # LOGIN SUCCESS
        # =====================================

        if user:

            login_user(

                User(
                    user['id'],
                    user['username'],
                    user['password']
                ),

                remember=False
            )

            session.permanent = True

            session['is_admin'] = True

            return redirect(
                url_for('dashboard')
            )

        # =====================================
        # LOGIN FAILED
        # =====================================

        print(
            f'Failed login attempt: {username}'
        )

        return render_template(

            'login.html',

            error='Invalid credentials'
        )

    return render_template(
        'login.html'
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route('/logout')
@login_required
def logout():

    logout_user()

    session.clear()

    return redirect(
        url_for('login')
    )
# =========================================================
# DASHBOARD
# =========================================================

@app.route('/dashboard')
@login_required
def dashboard():

    stats = db.get_dashboard_stats()

    age_distribution = db.get_age_distribution()

    gender_ratio = db.get_gender_ratio()

    recent_voters = db.get_recent_voters(10)

    return render_template(

        'dashboard.html',

        stats=stats,

        age_distribution=age_distribution or [],

        gender_ratio=gender_ratio or [],

        recent_voters=recent_voters or []
    )


# =========================================================
# SEARCH PAGE
# =========================================================

@app.route('/search')
@login_required
def search():

    query = request.args.get('q', '').strip()

    results = []

    # Prevent unnecessary heavy queries
    if query and len(query) >= 2:

        results = db.smart_search(query)

    return render_template(

        'search.html',

        results=results,

        query=query
    )


# =========================================================
# LIVE SEARCH API
# =========================================================

@app.route('/api/search')
@login_required
def api_search():

    query = request.args.get('q', '').strip()

    # Minimum query length
    if not query or len(query) < 2:

        return jsonify({

            'results': [],

            'count': 0
        })

    results = db.smart_search(query)

    return jsonify({

        'results': results,

        'count': len(results)
    })


# =========================================================
# VOTER PROFILE
# =========================================================

@app.route('/voter/<int:voter_id>')
@login_required
def voter_profile(voter_id):

    voter = db.get_voter_by_id(voter_id)

    if not voter:

        return redirect(url_for('search'))

    family_members = db.get_family_members(
        voter['house_no']
    )

    documents = db.get_voter_documents(voter_id)

    return render_template(

        'profile.html',

        voter=voter,

        family_members=family_members,

        documents=documents
    )
# =========================================================
# DOCUMENT UPLOAD
# =========================================================

@app.route('/upload/<int:voter_id>', methods=['POST'])
@login_required
def upload_document(voter_id):

    try:

        file = request.files.get('document')

        doc_type = request.form.get(
            'doc_type',
            'other'
        ).strip()

        # =============================================
        # FILE EXIST CHECK
        # =============================================

        if not file:

            return jsonify({

                'success': False,

                'error': 'No file selected'
            }), 400

        # =============================================
        # EMPTY FILE CHECK
        # =============================================

        if file.filename == '':

            return jsonify({

                'success': False,

                'error': 'Empty filename'
            }), 400

        # =============================================
        # EXTENSION VALIDATION
        # =============================================

        if not allowed_file(file.filename):

            return jsonify({

                'success': False,

                'error': 'Invalid file type'
            }), 400

        # =============================================
        # SECURE FILENAME
        # =============================================

        original_filename = secure_filename(
            file.filename
        )

        # =============================================
        # UNIQUE FILENAME
        # =============================================

        timestamp = datetime.now().strftime(
            '%Y%m%d%H%M%S'
        )

        filename = (
            f"{voter_id}_{timestamp}_{original_filename}"
        )

        # =============================================
        # ENSURE UPLOAD FOLDER EXISTS
        # =============================================

        os.makedirs(

            app.config['UPLOAD_FOLDER'],

            exist_ok=True
        )

        # =============================================
        # SAVE PATH
        # =============================================

        save_path = os.path.join(

            app.config['UPLOAD_FOLDER'],

            filename
        )

        # =============================================
        # SAVE FILE
        # =============================================

        file.save(save_path)

        # =============================================
        # SECURE URL
        # =============================================

        file_url = f"/document/{filename}"

        # =============================================
        # SAVE INTO DATABASE
        # =============================================

        db.add_document(

            voter_id,

            file_url,

            doc_type
        )

        # =============================================
        # SUCCESS RESPONSE
        # =============================================

        return jsonify({

            'success': True,

            'message': 'Document uploaded successfully',

            'file_url': file_url,

            'filename': filename
        })

    except Exception as e:

        print('Upload Error:', e)

        return jsonify({

            'success': False,

            'error': str(e)
        }), 500


# =========================================================
# SECURE DOCUMENT VIEW
# =========================================================

@app.route('/document/<filename>')
@login_required
def serve_document(filename):

    try:

        return send_from_directory(

            app.config['UPLOAD_FOLDER'],

            filename,

            as_attachment=False
        )

    except Exception as e:

        print('Document Open Error:', e)

        return render_template(

            '404.html'
        ), 404


# =========================================================
# EXPORT CSV
# =========================================================

@app.route('/export/csv')
@login_required
def export_csv():

    try:

        data = db.export_to_csv()

        df = pd.DataFrame(data)

        filename = f'''

voter_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv

'''.strip()

        df.to_csv(

            filename,

            index=False
        )

        return send_file(

            filename,

            as_attachment=True
        )

    except Exception as e:

        print('CSV Export Error:', e)

        return jsonify({

            'success': False,

            'error': str(e)
        }), 500


# =========================================================
# EXPORT EXCEL
# =========================================================

@app.route('/export/excel')
@login_required
def export_excel():

    try:

        data = db.export_to_csv()

        df = pd.DataFrame(data)

        filename = f'''

voter_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx

'''.strip()

        df.to_excel(

            filename,

            index=False
        )

        return send_file(

            filename,

            as_attachment=True
        )

    except Exception as e:

        print('Excel Export Error:', e)

        return jsonify({

            'success': False,

            'error': str(e)
        }), 500


# =========================================================
# IMPORT CSV
# =========================================================

@app.route('/import/csv', methods=['POST'])
@login_required
def import_csv():

    file = request.files.get('csv_file')

    if not file:

        return jsonify({

            'success': False,

            'error': 'No file uploaded'
        }), 400

    try:

        imported_count = 0

        # =============================================
        # LARGE FILE SAFE IMPORT
        # =============================================

        for chunk in pd.read_csv(

            file,

            chunksize=1000
        ):

            imported_count += db.import_from_dataframe(
                chunk
            )

        return jsonify({

            'success': True,

            'imported': imported_count
        })

    except Exception as e:

        print('CSV Import Error:', e)

        return jsonify({

            'success': False,

            'error': str(e)
        }), 500


# =========================================================
# DATABASE BACKUP
# =========================================================

@app.route('/backup')
@login_required
def backup():

    try:

        backup_file = db.backup_database()

        return send_file(

            backup_file,

            as_attachment=True
        )

    except Exception as e:

        print('Backup Error:', e)

        return jsonify({

            'success': False,

            'error': str(e)
        }), 500


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return render_template(
        '404.html'
    ), 404


@app.errorhandler(500)
def internal_error(error):

    return render_template(
        '500.html'
    ), 500


# =========================================================
# MAIN SERVER
# =========================================================

if __name__ == '__main__':

    # =============================================
    # CREATE REQUIRED FOLDERS
    # =============================================

    os.makedirs(

        app.config['UPLOAD_FOLDER'],

        exist_ok=True
    )

    os.makedirs(

        'data',

        exist_ok=True
    )

    # =============================================
    # CREATE ADMIN USER
    # =============================================

    db.create_admin_user(

        os.environ.get(
            'ADMIN_USER',
            'admin'
        ),

        os.environ.get(
            'ADMIN_PASS',
            'StrongPassword123!'
        )
    )

    # =============================================
    # START SERVER
    # =============================================

    app.run(

        host='0.0.0.0',

        port=5000,

        debug=False,

        threaded=True
    )