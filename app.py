# app.py - Ultimate Flask Static Site with Full Admin Control (2025 Edition)

from flask import Flask, request, send_from_directory, abort, redirect, render_template_string, make_response, session, url_for
import os
import time
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super-secret-key-change-this"  # ← Change kar dena apna strong password

# ====================== CONFIG ======================
SITE_DIR = os.path.abspath(".")
MAINTENANCE_FILE = "maintenance_on.flag"
ADMIN_PASS_FILE = "admin_password.txt"
BLOCKED_IPS_FILE = "blocked_ips.json"
LOGS_FILE = "access_logs.txt"

# Default admin password (pehle run pe ye file ban jayegi agar nahi hai)
DEFAULT_ADMIN_PASS = "admin123"

# Good & Bad bots
GOOD_BOTS = ["googlebot", "bingbot", "duckduckbot", "yandexbot", "facebookexternalhit"]
BAD_UA_PARTS = ["curl", "wget", "python", "scrapy", "headless", "phantomjs", "semrush", "ahrefs", "mj12bot"]

DELAY_BAD_BOT = 5
RATE_LIMIT = {}
BLOCKED_IPS = set()

# ====================== LOAD BLOCKED IPS ======================
def load_blocked_ips():
    global BLOCKED_IPS
    if os.path.exists(BLOCKED_IPS_FILE):
        try:
            with open(BLOCKED_IPS_FILE, "r") as f:
                BLOCKED_IPS = set(json.load(f))
        except:
            BLOCKED_IPS = set()

def save_blocked_ips():
    with open(BLOCKED_IPS_FILE, "w") as f:
        json.dump(list(BLOCKED_IPS), f)

load_blocked_ips()

# ====================== LOGGING ======================
def log_access(ip, path, status="200", ua=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {ip} | {status} | {path} | {ua[:100]}\n")

# ====================== HELPERS ======================
def is_good_bot():
    ua = (request.headers.get("User-Agent") or "").lower()
    return any(bot in ua for bot in GOOD_BOTS)

def is_bad_bot():
    ua = (request.headers.get("User-Agent") or "").lower()
    return any(bad in ua for bad in BAD_UA_PARTS)

def is_maintenance():
    return os.path.exists(MAINTENANCE_FILE)

def is_admin_logged_in():
    return session.get("admin_logged_in", False)

# ====================== SECURITY HEADERS ======================
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response

# ====================== FIREWALL ======================
@app.before_request
def firewall():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr.split(',')[0].strip()) if request.remote_addr else "unknown"
    path = request.path
    ua = request.headers.get("User-Agent") or "No-UA"

    log_access(ip, path, ua=ua)

    # Blocked IPs
    if ip in BLOCKED_IPS:
        return send_from_directory(SITE_DIR, "blocked.html"), 403

    if not ua and ip not in ("127.0.0.1", "::1"):
        return send_from_directory(SITE_DIR, "blocked.html"), 403

    if is_good_bot():
        return

    if is_bad_bot():
        time.sleep(DELAY_BAD_BOT)
        return send_from_directory(SITE_DIR, "blocked.html"), 403

    if is_maintenance() and not path.startswith(("/admin", "/login", "/static")):
        return send_from_directory(SITE_DIR, "maintenance.html"), 503

    # Rate limiting
    now = time.time()
    times = [t for t in RATE_LIMIT.get(ip, []) if now - t < 15]
    if len(times) > 40:
        BLOCKED_IPS.add(ip)
        save_blocked_ips()
        return send_from_directory(SITE_DIR, "blocked.html"), 429
    times.append(now)
    RATE_LIMIT[ip] = times

# ====================== CUSTOM 404 PAGE ======================
@app.errorhandler(404)
def page_not_found(e):
    log_access(request.remote_addr, request.path, status="404")
    return send_from_directory(SITE_DIR, "404.html"), 404

# ====================== ROUTES ======================
@app.route("/")
def home():
    return send_from_directory(SITE_DIR, "index.html")

@app.route("/<path:path>")
def catch_all(path):
    full_path = os.path.abspath(os.path.join(SITE_DIR, path))
    if not full_path.startswith(SITE_DIR):
        abort(403)
    if os.path.isfile(full_path):
        return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path))
    # 404.html will be handled by errorhandler above
    abort(404)

@app.route('/id', strict_slashes=False)
def id_page():
    return send_from_directory('ID', 'index.html')


@app.route('/jsonvalidator', strict_slashes=False)
def json_validator():
    return send_from_directory('JsonValidator', 'index.html')

@app.route('/xmltool', strict_slashes=False)
def xml_tool():
    return send_from_directory('XMLTool', 'index.html')

@app.route('/review', strict_slashes=False)
def review():
    return send_from_directory('Review', 'index.html')
    
# ====================== ADMIN PANEL ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        with open(ADMIN_PASS_FILE, "r") as f:
            valid = [p.strip() for p in f.readlines()]
        if password in valid:
            session["admin_logged_in"] = True
            return redirect("/admin")
    return '''
    <h2>Admin Login</h2>
    <form method="post">
        Password: <input type="password" name="password">
        <button type="submit">Login</button>
    </form>
    '''

@app.route("/admin")
def admin_panel():
    if not is_admin_logged_in():
        return redirect("/login")

    # Read logs
    logs = ""
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "r", encoding="utf-8") as f:
            logs = "<br>".join(f.readlines()[-50:][::-1])  # Last 50 logs

    blocked_count = len(BLOCKED_IPS)
    return f"""
    <h1 style="color:#f43f5e; text-align:center;">Super Admin Panel</h1>
    <p><a href="/admin/logout">Logout</a> | <a href="/">Home</a></p>
    <hr>
    <h2>Maintenance Mode</h2>
    <form method="post" action="/admin/maintenance-on" style="display:inline;">
        <button style="padding:10px 20px; background:#d9534f; color:white;">Turn ON</button>
    </form>
    <form method="post" action="/admin/maintenance-off" style="display:inline; margin-left:10px;">
        <button style="padding:10px 20px; background:#5cb85c; color:white;">Turn OFF</button>
    </form>

    <h2>Blocked IPs ({blocked_count})</h2>
    <form method="post" action="/admin/unblock">
        IP: <input name="ip" placeholder="Enter IP to unblock">
        <button>Unblock</button>
    </form>
    <small>Currently blocked: {", ".join(list(BLOCKED_IPS)[:20])}{'...' if blocked_count > 20 else ''}</small>

    <h2>Live Access Logs (Last 50)</h2>
    <pre style="background:#111; color:#0f0; padding:15px; border-radius:10px; max-height:500px; overflow:auto;">{logs or "No logs yet"}</pre>
    <hr>
    <p><b>404 Page:</b> /404.html (edit directly in folder)</p>
    """

@app.route("/admin/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect("/")

@app.route("/admin/maintenance-on", methods=["POST"])
def maintenance_on():
    if is_admin_logged_in():
        open(MAINTENANCE_FILE, "w").close()
    return redirect("/admin")

@app.route("/admin/maintenance-off", methods=["POST"])
def maintenance_off():
    if is_admin_logged_in() and os.path.exists(MAINTENANCE_FILE):
        os.remove(MAINTENANCE_FILE)
    return redirect("/admin")

@app.route("/admin/unblock", methods=["POST"])
def unblock_ip():
    if is_admin_logged_in():
        ip = request.form.get("ip", "").strip()
        if ip in BLOCKED_IPS:
            BLOCKED_IPS.remove(ip)
            save_blocked_ips()
    return redirect("/admin")

# ====================== FIRST RUN SETUP ======================
if not os.path.exists(ADMIN_PASS_FILE):
    with open(ADMIN_PASS_FILE, "w") as f:
        f.write(DEFAULT_ADMIN_PASS + "\n")
    print(f"Admin password set: {DEFAULT_ADMIN_PASS} → Change it from admin_password.txt")

# ====================== CREATE DEFAULT FILES IF MISSING ======================
for file in ["404.html", "maintenance.html", "blocked.html"]:
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            f.write(f"<!DOCTYPE html><html><body><h1>{file.replace('.html','').upper()}</h1><p>Custom {file} page</p></body></html>")

# ====================== RUN ======================
if __name__ == "__main__":
    print("Server chal raha hai! Admin login: http://localhost:3000/login")
    print("Default password:", DEFAULT_ADMIN_PASS if os.path.exists(ADMIN_PASS_FILE) else "Check admin_password.txt")
    app.run(host="0.0.0.0", port=3000, debug=False, threaded=True)
