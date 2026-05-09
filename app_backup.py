from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from database import Database
from werkzeug.utils import secure_filename
from functools import wraps
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# ================= CONFIG =================
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

# ================= DATABASE (FIXED) =================
db = Database('data/voter_system.db')

# ================= LOGIN =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


@login_manager.user_loader
def load_user(user_id):
    user = db.get_user_by_id(user_id)
    if user:
        return User(user['id'], user['username'], user['password'])
    return None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ================= ROUTES =================

@app.route('/')
def index():
    return redirect(url_for('login'))


# -------- LOGIN --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = db.authenticate_user(
            request.form.get('username'),
            request.form.get('password')
        )

        if user:
            login_user(User(user['id'], user['username'], user['password']))
            session['is_admin'] = True
            return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')


# -------- LOGOUT --------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))


# -------- DASHBOARD (FIXED) --------
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


# -------- SEARCH (FIXED SINGLE ROUTE) --------
@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()

    results = db.smart_search(query) if query else []

    return render_template(
        'search.html',
        results=results,
        query=query
    )


# -------- API SEARCH --------
@app.route('/api/search')
@login_required
def api_search():
    query = request.args.get('q', '')
    results = db.smart_search(query) if query else []
    return jsonify({'results': results, 'count': len(results)})


# -------- VOTER PROFILE --------
@app.route('/voter/<int:voter_id>')
@login_required
def voter_profile(voter_id):
    voter = db.get_voter_by_id(voter_id)
    if not voter:
        return redirect(url_for('search'))

    return render_template(
        'profile.html',
        voter=voter,
        family_members=db.get_family_members(voter['house_no']),
        documents=db.get_voter_documents(voter_id)
    )


# -------- EXPORT CSV --------
@app.route('/export/csv')
@login_required
def export_csv():
    df = pd.DataFrame(db.export_to_csv())
    file = 'voter_export.csv'
    df.to_csv(file, index=False)
    return send_file(file, as_attachment=True)


# -------- EXPORT EXCEL --------
@app.route('/export/excel')
@login_required
def export_excel():
    df = pd.DataFrame(db.export_to_csv())
    file = 'voter_export.xlsx'
    df.to_excel(file, index=False)
    return send_file(file, as_attachment=True)


# -------- IMPORT CSV --------
@app.route('/import/csv', methods=['POST'])
@login_required
def import_csv():
    file = request.files.get('csv_file')

    if not file:
        return jsonify({'error': 'No file uploaded'}), 400

    df = pd.read_csv(file)
    count = db.import_from_dataframe(df)

    return jsonify({'success': True, 'imported': count})


# -------- BACKUP --------
@app.route('/backup')
@login_required
def backup():
    file = db.backup_database()
    return send_file(file, as_attachment=True)


# ================= MAIN =================
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.create_admin_user('admin', 'admin123')

    app.run(host='0.0.0.0', port=5000, debug=True)
