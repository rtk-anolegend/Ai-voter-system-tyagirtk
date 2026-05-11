# AI Voter Management System

A secure Flask-based voter management dashboard designed for Raspberry Pi and local network deployment. This version is optimized for LAN/mobile login sessions and development over HTTP.

## 🚀 Key Features

- Flask authentication with `Flask-Login`
- Local network (LAN) and mobile browser compatibility
- User session persistence across `localhost`, local IP, and mobile devices
- Secure file upload and document serving
- Dashboard, search, export, import, and database tools
- Designed to run on Raspberry Pi and small local servers

## 🧩 What Changed

- Disabled `Flask-Talisman` to avoid forced HTTPS/CSP behavior on local networks
- Preserved all app routes and upload/dashboard/search/export features
- Added robust session cookie settings for HTTP LAN development
- Ensured `User.get_id()` returns a string for Flask-Login compatibility
- Kept `login_user()` usage safe and session-permanent for mobile/LAN access

## 📦 Installation

1. Clone the repository:

```bash
git clone https://github.com/<your-org>/Ai-voter-system-tyagirtk.git
cd Ai-voter-system-tyagirtk
```

2. Create and activate a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## ⚙️ Setup

1. Create required folders:

```bash
mkdir -p uploads data
```

2. Set environment variables for production security:

```bash
export SECRET_KEY='your-production-secret'
export ADMIN_USER='admin'
export ADMIN_PASS='TyagiVoter'
```

3. Start the application:

```bash
python app.py
```

## 🔐 Default Login Credentials

- Username: `admin`
- Password: `TyagiVoter`

> Change these immediately in production by setting `ADMIN_USER` and `ADMIN_PASS`.

## 🖥️ Raspberry Pi Setup

1. Update the OS and install Python packages:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv -y
```

2. Clone the repo and install dependencies as above.

3. Run the app:

```bash
python3 app.py
```

4. Access from another device on the same network:

```text
http://<raspberry-pi-ip>:5000
```

## 📱 LAN and Mobile Access

The application is configured for local HTTP use and works on mobile browsers without HTTPS enforcement.

- Access by hostname: `http://localhost:5000`
- Access by LAN IP: `http://192.168.x.x:5000`
- Mobile browsers on the same network can use the same IP and port

## 📸 Screenshots

Add screenshots to this section once available. Example images can be stored in `static/images`.

- Login page
- Dashboard view
- Search results
- Upload progress
- Export/backup screens

## 🛠️ Troubleshooting

### Login fails on LAN/mobile

- Confirm you are using `http://` and not `https://`
- Make sure `SESSION_COOKIE_SECURE` is `False` for local development
- Ensure the browser is not blocking cookies for local IP addresses
- Clear browser cookies and retry

### Static files or upload issues

- Verify `uploads/` exists and is writable
- Confirm `static/` files are present and served from `static/`
- Check app logs for permission errors

### Database issues

- The SQLite database is `data/voter_system.db`
- If missing, the app creates it automatically on startup
- Backup and restore using the dashboard export tools

## 🛡️ Security Notes

- `Flask-Talisman` is intentionally disabled for this repository to support HTTP LAN/mobile sessions.
- In production behind HTTPS, re-enable security middleware and set `SESSION_COOKIE_SECURE=True`.
- Use a strong `SECRET_KEY` in `SECRET_KEY` environment variable.
- Change the default admin account immediately after first login.
- Use a proper WSGI server like `gunicorn` or `waitress` for production deployments.

## 📁 Deployment Steps for GitHub/Open Source

1. Create a new repository on GitHub.
2. Push this project to GitHub:

```bash
git init
git add .
git commit -m "Initial open-source ready commit"
git branch -M main
git remote add origin https://github.com/<your-org>/Ai-voter-system-tyagirtk.git
git push -u origin main
```

3. Add `README.md`, `requirements.txt`, and `app.py` to the repo.
4. Use `.gitignore` to exclude `venv/`, `__pycache__/`, and local files.

## ✅ Open Source Ready

This repository is ready for public sharing:

- Clean installation and setup instructions
- Clear LAN/mobile compatibility notes
- Session fixes for Raspberry Pi/local IP access
- No forced HTTPS or CSP blocking in development mode
- Fixed `Flask-Login` compatibility and cookie settings

## 📌 Notes for Contributors

- Keep the local session behavior HTTP-friendly for LAN testing.
- Preserve `SESSION_COOKIE_SECURE=False` for local/dev mode.
- Re-enable strong security only when deploying behind HTTPS.
- Use `app.py` as the single source of truth for session and login handling.

---

If you want, I can also add a `.gitignore` and a `CONTRIBUTING.md` file for open-source readiness.
