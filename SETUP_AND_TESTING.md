# 🚀 Setup, Testing & Verification Guide

Complete guide for setting up, testing, and verifying the AI-Voter Management System.

---

## 📋 Table of Contents

1. [Initial Setup](#initial-setup)
2. [Database Management](#database-management)
3. [Starting the Application](#starting-the-application)
4. [Testing & Verification](#testing--verification)
5. [LAN & Mobile Access](#lan--mobile-access)
6. [Troubleshooting](#troubleshooting)
7. [Performance Testing](#performance-testing)

---

## Initial Setup

### 1. First-Time Installation (Clean Setup)

```bash
# Step 1: Navigate to project directory
cd /home/tyagi/3.ovoter/Ai-voter-system-tyagirtk

# Step 2: Create Python virtual environment
python3 -m venv venv

# Step 3: Activate virtual environment
source venv/bin/activate

# Step 4: Upgrade pip
pip install --upgrade pip

# Step 5: Install all dependencies
pip install -r requirements.txt

# Step 6: Create necessary directories
mkdir -p data uploads backups

# Step 7: Run the application (database will auto-initialize)
python app.py
```

### 2. Verify Installation Success

After running `python app.py`, you should see:

```
======================================================================
Starting AI-Voter Management System
======================================================================
Database: data/voter_system.db
Listening on: 0.0.0.0:5000
LAN Access: http://<your-local-ip>:5000
First-time credentials: admin / TyagiVoter
======================================================================
```

✅ **Success Indicators:**
- No Python errors in console
- Server listening message displayed
- Database file created: `data/voter_system.db`
- Admin user created in database

---

## Database Management

### ⚠️ IMPORTANT: Safe Database Operations

Always backup your database before making changes:

```bash
# Before doing anything destructive, CREATE A BACKUP
cp data/voter_system.db data/voter_system.db.backup.$(date +%Y%m%d_%H%M%S)
```

### Delete Old Database Safely

Use these commands ONLY if you need a fresh start:

```bash
# ============================================================
# SAFE DATABASE DELETION
# ============================================================

# Step 1: STOP the running application
# (Press Ctrl+C in the terminal where app is running)

# Step 2: Verify app is stopped
ps aux | grep python | grep app.py
# If app is running, kill it:
killall python3
# OR
pkill -f "python app.py"

# Step 3: BACKUP the current database (CRITICAL!)
cp data/voter_system.db data/voter_system.db.old.$(date +%Y%m%d_%H%M%S)

# Step 4: Delete the old database
rm data/voter_system.db

# Step 5: Verify deletion
ls -la data/voter_system.db
# You should see "No such file or directory" - this is CORRECT

# Step 6: Verify backup exists
ls -la data/voter_system.db.old.*

# Step 7: RESTART the application
python app.py
# Database will be recreated automatically!
```

### Restore from Backup

If you need to restore a previous version:

```bash
# ============================================================
# RESTORE FROM BACKUP
# ============================================================

# Step 1: STOP the running application
# (Press Ctrl+C in terminal)

# Step 2: Find your backups
ls -la data/voter_system.db.*

# Step 3: Choose which backup to restore and copy it
cp data/voter_system.db.backup.20240115_143022 data/voter_system.db

# Step 4: Verify restoration
ls -la data/voter_system.db
# You should see the file with today's date

# Step 5: RESTART the application
python app.py
```

### Database Inspection (While Running)

You can inspect the database while the app is running:

```bash
# ============================================================
# VIEW DATABASE CONTENTS (Safe - read-only)
# ============================================================

# List all tables
sqlite3 data/voter_system.db ".tables"

# Count total voters
sqlite3 data/voter_system.db "SELECT COUNT(*) as total_voters FROM voters;"

# List all users
sqlite3 data/voter_system.db "SELECT id, username, last_login FROM users;"

# Check database size
du -h data/voter_system.db

# View database schema
sqlite3 data/voter_system.db ".schema voters"

# Export to CSV for inspection
sqlite3 data/voter_system.db \
    "SELECT serial_no, name, age, mobile FROM voters LIMIT 10;" \
    --csv > voter_sample.csv

# View search logs (analytics)
sqlite3 data/voter_system.db \
    "SELECT query, COUNT(*) as searches FROM search_logs GROUP BY query ORDER BY searches DESC LIMIT 10;"
```

---

## Starting the Application

### Start in Development Mode

```bash
# ============================================================
# START APPLICATION - DEVELOPMENT
# ============================================================

# Step 1: Navigate to project directory
cd /home/tyagi/3.ovoter/Ai-voter-system-tyagirtk

# Step 2: Activate virtual environment
source venv/bin/activate

# Step 3: Start the application
python app.py

# Expected output:
# ======================================================================
# Starting AI-Voter Management System
# ======================================================================
# Database: data/voter_system.db
# Listening on: 0.0.0.0:5000
# LAN Access: http://192.168.x.x:5000
# First-time credentials: admin / TyagiVoter
# ======================================================================

# ✅ Application is now running!
# Access it at: http://localhost:5000
```

### Start in Background (Detached)

```bash
# ============================================================
# START APPLICATION IN BACKGROUND
# ============================================================

# Using nohup (output goes to nohup.out)
nohup python app.py > app.log 2>&1 &

# Using screen (create a new terminal session)
screen -S voter-app
python app.py
# (Press Ctrl+A then D to detach without stopping the app)

# Using tmux
tmux new-session -d -s voter-app "python app.py"

# To check if app is running:
ps aux | grep python | grep app.py

# To view the log:
tail -f app.log
```

### Stop the Application

```bash
# ============================================================
# STOP APPLICATION SAFELY
# ============================================================

# Method 1: If running in foreground terminal
# Press: Ctrl+C

# Method 2: If running in background
pkill -f "python app.py"

# Method 3: More forceful termination
killall python3

# Method 4: Using process ID (PID)
ps aux | grep python | grep app.py
# Note the PID (second column)
kill -9 <PID>

# Verify it's stopped
ps aux | grep python | grep app.py
# Should return nothing if stopped successfully
```

---

## Testing & Verification

### ✅ Complete Verification Checklist

Run these tests after startup:

```bash
# ============================================================
# VERIFICATION TEST 1: Server is Running
# ============================================================

# Test local access
curl http://localhost:5000/
# Should show HTML content (login page)

# Test from different localhost
curl http://127.0.0.1:5000/
# Should show HTML content

# Check response code (should be 200 or 302 for redirects)
curl -I http://localhost:5000/login
# Should show "200 OK"
```

```bash
# ============================================================
# VERIFICATION TEST 2: Database Initialization
# ============================================================

# Verify database file exists
ls -la data/voter_system.db

# Verify database is accessible
sqlite3 data/voter_system.db "SELECT 1;"
# Should output: 1

# Verify tables exist
sqlite3 data/voter_system.db ".tables"
# Should show: documents families search_cache search_logs users voters voters_fts

# Verify admin user was created
sqlite3 data/voter_system.db "SELECT COUNT(*) FROM users WHERE username='admin';"
# Should output: 1
```

```bash
# ============================================================
# VERIFICATION TEST 3: Login Functionality
# ============================================================

# Test login with curl (simulating form submission)
curl -c cookies.txt \
  -d "username=admin&password=TyagiVoter" \
  http://localhost:5000/login

# You should get a redirect (302 or 303 response code)
# Sessions are now in cookies.txt

# Test accessing protected page with session
curl -b cookies.txt http://localhost:5000/dashboard
# Should show dashboard HTML (not login page)
```

```bash
# ============================================================
# VERIFICATION TEST 4: API Endpoints
# ============================================================

# Test search API
curl -b cookies.txt "http://localhost:5000/api/search?q=test&limit=10"
# Should return JSON with results array

# Test suggestions API
curl -b cookies.txt "http://localhost:5000/api/suggestions?q=raj&limit=5"
# Should return JSON with suggestions array

# Test analytics API
curl -b cookies.txt "http://localhost:5000/api/analytics?days=7"
# Should return JSON with analytics data
```

```bash
# ============================================================
# VERIFICATION TEST 5: Static Files
# ============================================================

# Test CSS loading
curl -I http://localhost:5000/static/css/style.css
# Should return "200 OK"

# Test JavaScript loading
curl -I http://localhost:5000/static/js/main.js
# Should return "200 OK"

# Test logo image
curl -I http://localhost:5000/static/images/logo.png
# Should return "200 OK"

# Verify files exist
ls -la static/css/style.css
ls -la static/js/main.js
ls -la static/images/logo.png
```

### Manual Testing (Browser)

Open your browser and test:

1. **Login Page** (`http://localhost:5000`)
   - [ ] Page loads without errors
   - [ ] Logo image displays correctly
   - [ ] Footer shows security info
   - [ ] Error message area is visible

2. **Login** with `admin` / `TyagiVoter`
   - [ ] Login successful, redirects to dashboard
   - [ ] Does NOT redirect back to login page
   - [ ] Session persists when refreshing

3. **Dashboard**
   - [ ] Statistics display correctly
   - [ ] Charts load if you have data
   - [ ] All buttons are clickable
   - [ ] Mobile view is responsive

4. **Search Page**
   - [ ] Search bar accepts input
   - [ ] Live suggestions appear
   - [ ] Search results display
   - [ ] Results responsive on mobile

5. **Error Pages**
   - Visit `http://localhost:5000/nonexistent` to test 404
   - Should display 404.html page

---

## LAN & Mobile Access

### 🌐 Get Your Local IP Address

```bash
# ============================================================
# FIND RASPBERRY PI IP ADDRESS
# ============================================================

# Method 1: Using hostname (Linux/Raspberry Pi)
hostname -I
# Output: 192.168.1.100 (your IP)

# Method 2: Using ifconfig
ifconfig
# Look for "inet" address under "eth0" or "wlan0"

# Method 3: Using ip command
ip addr show | grep "inet "
# Look for 192.168.x.x or 10.0.x.x

# Method 4: Using router (if you can access it)
# Log into your WiFi router admin panel
# Find device list and look for "Raspberry Pi" or hostname
```

### 🔗 Test LAN Access

```bash
# ============================================================
# TEST LAN ACCESS FROM DIFFERENT DEVICES
# ============================================================

# From Raspberry Pi itself
curl http://localhost:5000/login
curl http://127.0.0.1:5000/login
curl http://192.168.1.100:5000/login  # Replace with YOUR IP

# From another Linux/Mac machine on same network
curl http://192.168.1.100:5000/login  # Replace with Pi's IP

# From Windows command prompt
curl http://192.168.1.100:5000/login

# Or use PowerShell (Windows)
Invoke-WebRequest -Uri "http://192.168.1.100:5000/login" -UseBasicParsing
```

### 📱 Test on Mobile/Tablet

1. **Connect to same WiFi as Raspberry Pi**
2. **Open browser on mobile device**
3. **Navigate to:** `http://192.168.1.100:5000` (replace IP with yours)
4. **Verify:**
   - [ ] Login page loads
   - [ ] Layout is responsive
   - [ ] Touch controls work
   - [ ] Keyboard appears for text input
   - [ ] Login successful with credentials
   - [ ] Dashboard is usable on small screen

### 📡 Session Persistence Testing

```bash
# ============================================================
# TEST SESSION PERSISTENCE ACROSS DIFFERENT ACCESS METHODS
# ============================================================

# Login from localhost
echo "1. Logging in from localhost..."
curl -c session.txt \
  -d "username=admin&password=TyagiVoter" \
  http://localhost:5000/login

# Access dashboard (verify session works)
echo "2. Accessing dashboard from localhost..."
curl -b session.txt http://localhost:5000/dashboard | grep -c "dashboard"

# Access same session from 127.0.0.1
echo "3. Accessing from 127.0.0.1..."
curl -b session.txt http://127.0.0.1:5000/dashboard | grep -c "dashboard"

# Access same session from local IP
echo "4. Accessing from local IP..."
curl -b session.txt http://192.168.1.100:5000/dashboard | grep -c "dashboard"

# All should work - session persists across different access methods!
```

### Firewall Configuration (if needed)

```bash
# ============================================================
# FIREWALL - ALLOW PORT 5000
# ============================================================

# For UFW (Ubuntu/Raspberry Pi)
sudo ufw status
# If showing "Status: inactive" - firewall is disabled (OK)
# If showing "Status: active":
sudo ufw allow 5000/tcp
sudo ufw reload

# For iptables
sudo iptables -I INPUT -p tcp --dport 5000 -j ACCEPT
# Save iptables rules (optional)
sudo iptables-save > /etc/iptables/rules.v4

# For firewalld
sudo firewall-cmd --add-port=5000/tcp --permanent
sudo firewall-cmd --reload

# Verify port is open
sudo netstat -tlnp | grep 5000
# Should show: tcp 0 0 0.0.0.0:5000 0.0.0.0:* LISTEN
```

---

## Troubleshooting

### Problem: "Port 5000 already in use"

```bash
# ============================================================
# FIX: Port Already in Use
# ============================================================

# Find what's using port 5000
lsof -i :5000
# Shows: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME

# Kill the process using port 5000
kill -9 <PID>  # Replace <PID> with the number shown above

# Or use this to kill all Python processes
pkill -f "python"

# Or use different port
cd /home/tyagi/3.ovoter/Ai-voter-system-tyagirtk
python -c "from app import app; app.run(host='0.0.0.0', port=5001)"
# App will now run on http://localhost:5001
```

### Problem: "Module not found" errors

```bash
# ============================================================
# FIX: Missing Modules
# ============================================================

# Ensure virtual environment is activated
source venv/bin/activate
# (You should see (venv) in your prompt)

# Reinstall requirements
pip install -r requirements.txt --force-reinstall

# Verify Flask is installed
python -c "import flask; print(flask.__version__)"
# Should print version number like 3.1.0
```

### Problem: Database locked error

```bash
# ============================================================
# FIX: Database Locked
# ============================================================

# The app uses WAL mode which is usually fine
# If you get "database is locked" errors:

# Step 1: Stop the application
pkill -f "python app.py"

# Step 2: Remove WAL files
rm data/voter_system.db-wal
rm data/voter_system.db-shm
rm data/voter_system.db-journal

# Step 3: Restart application
python app.py
```

### Problem: Login doesn't work

```bash
# ============================================================
# FIX: Login Issues
# ============================================================

# Check 1: Verify admin user exists
sqlite3 data/voter_system.db "SELECT username, last_login FROM users;"

# Check 2: Verify password hash is set
sqlite3 data/voter_system.db "SELECT username, length(password) FROM users WHERE username='admin';"
# Should show a password length > 20

# Check 3: Reset admin password if needed
python << 'EOF'
from database import Database
from werkzeug.security import generate_password_hash

db = Database('data/voter_system.db')
import sqlite3

# Create backup first!
import shutil
shutil.copy('data/voter_system.db', 'data/voter_system.db.backup')

# Reset password
conn = sqlite3.connect('data/voter_system.db')
cursor = conn.cursor()
new_password = generate_password_hash('TyagiVoter')
cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", (new_password,))
conn.commit()
conn.close()
print("✅ Password reset to: TyagiVoter")
EOF
```

---

## Performance Testing

### Load Testing

```bash
# ============================================================
# PERFORMANCE TEST: Search Speed
# ============================================================

# Test 1: Simple search
time curl -b cookies.txt "http://localhost:5000/api/search?q=test"

# Test 2: Complex search
time curl -b cookies.txt "http://localhost:5000/api/search?q=test&search_type=all&limit=100"

# Test 3: Concurrent searches (requires Apache Bench)
ab -n 100 -c 10 -b cookies.txt http://localhost:5000/api/search?q=test
```

### Memory and CPU Monitoring

```bash
# ============================================================
# MONITOR SYSTEM RESOURCES
# ============================================================

# Real-time monitoring
top
# or
htop

# Monitor while app is running
watch -n 1 'ps aux | grep python'

# Memory usage
ps aux | grep python | awk '{print $6 " KB"}'

# Database file size
du -h data/voter_system.db

# Disk space
df -h
# Look for available space
```

### Load Testing with ab (Apache Bench)

```bash
# ============================================================
# AUTOMATED LOAD TEST
# ============================================================

# Install Apache Bench
sudo apt-get install apache2-utils

# Test 100 requests with 10 concurrent connections
ab -n 100 -c 10 http://localhost:5000/

# Test login endpoint (50 requests)
ab -n 50 -c 5 -p login_data.txt \
   -T 'application/x-www-form-urlencoded' \
   http://localhost:5000/login

# Test search API (100 requests)
ab -n 100 -c 10 "http://localhost:5000/api/search?q=test"
```

---

## ✅ Final Verification Summary

After completing all tests, you should have:

- [x] Application starts without errors
- [x] Database created and initialized
- [x] Default admin user created
- [x] Login works with admin/TyagiVoter
- [x] Sessions persist across page refreshes
- [x] LAN access works from other devices
- [x] Mobile access is responsive
- [x] Static files load correctly
- [x] API endpoints return JSON
- [x] Error pages display properly
- [x] Search functionality works
- [x] Dashboard displays correctly
- [x] No JavaScript errors in browser console
- [x] Database backups can be created
- [x] Performance is acceptable

---

## Emergency Commands

```bash
# ============================================================
# QUICK REFERENCE - EMERGENCY COMMANDS
# ============================================================

# Kill the app immediately
killall python3

# Start fresh with backup
cp data/voter_system.db data/backup_$(date +%s).db && rm data/voter_system.db && python app.py

# Check if app is running
pgrep -f "python app.py"

# View last 50 lines of error log
tail -50 app.log

# Restart app safely
pkill -f "python app.py"; sleep 2; python app.py &

# Test connectivity to app
timeout 5 curl -I http://localhost:5000

# Check disk space
df -h | grep -E "/"

# Quick performance check
echo "Memory:"; free -h; echo "Disk:"; du -h data/voter_system.db
```

---

**Last Updated:** January 2024  
**Test Date:** [Your Date]  
**Tested By:** [Your Name]  
**Status:** ✅ All Tests Passed / ❌ Issues Found

---

*For detailed troubleshooting, refer to README.md #Troubleshooting section*
