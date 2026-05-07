from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database import Database
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd
from datetime import datetime
import hashlib
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

# Initialize database
db = Database()

# Setup login manager
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
    user_data = db.get_user_by_id(user_id)
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = db.authenticate_user(username, password)
        if user:
            user_obj = User(user[0], user[1], user[2])
            login_user(user_obj)
            session['is_admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required

@login_required
def dashboard():
    stats = db.get_dashboard_stats()
    age_distribution = db.get_age_distribution()
    gender_ratio = db.get_gender_ratio()
    recent_voters = db.get_recent_voters(10)

    print("STATS:", stats)
    print("GENDER:", gender_ratio)
    print("AGE:", age_distribution)

    return render_template(
        'dashboard.html',
        stats=stats,
        age_distribution=list(age_distribution),
        gender_ratio=list(gender_ratio),
        recent_voters=list(recent_voters)
    )

if __name__ == '__main__':
    import os
    os.makedirs('static/uploads', exist_ok=True)
    db.create_admin_user('admin', 'admin123')
    app.run(host='0.0.0.0', port=5000, debug=True)

    else:
        results = []
    return render_template('search.html', results=results, query=query)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    results = []

    if query:
        results = db.smart_search(query)

    return render_template('search.html', results=results, query=query)
