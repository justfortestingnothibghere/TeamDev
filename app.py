from flask import Flask, request, send_from_directory, abort, redirect, render_template_string, make_response
import os
import time

app = Flask(__name__)

# ====================== CONFIG ======================
SITE_DIR = "."  # Current directory (where index.html, JsonValidator/, etc. are)
MAINTENANCE_FILE = "maintenance_on.flag"
ADMIN_PASS_FILE = "admin_password.txt"  # Create this file with your password(s)

# Good bots - fully allowed (Google, Bing, etc.)
GOOD_BOTS = [
    "googlebot", "bingbot", "duckduckbot", "yandexbot", "baiduspider",
    "slurp", "facebookexternalhit", "twitterbot", "linkedinbot", "applebot"
]

# Bad bots/scrapers - delayed + blocked
BAD_UA_PARTS = [
    "curl", "wget", "python", "httpclient", "scrapy", "axios", "headless",
    "phantomjs", "semrush", "ahrefs", "mj12bot", "dotbot", "lighthouse"
]

DELAY_BAD_BOT = 6  # seconds of delay before blocking bad bots

# Simple rate limiting
RATE_LIMIT = {}  # {ip: [timestamps]}

# Tool directories (auto-redirect without trailing slash + serve index.html)
TOOL_DIRS = ["JsonValidator", "ID", "Review", "XMLTool"]

# ====================== HELPERS ======================
def is_good_bot():
    ua = (request.headers.get("User-Agent") or "").lower()
    return any(bot in ua for bot in GOOD_BOTS)

def is_bad_bot():
    ua = (request.headers.get("User-Agent") or "").lower()
    return any(bad in ua for bad in BAD_UA_PARTS)

def is_maintenance():
    return os.path.exists(MAINTENANCE_FILE)

def check_admin_auth():
    auth = request.authorization
    if not auth or auth.username != "admin":
        return False
    try:
        with open(ADMIN_PASS_FILE, "r") as f:
            passwords = [line.strip() for line in f if line.strip()]
        return auth.password in passwords
    except:
        return False

def require_admin():
    if not check_admin_auth():
        resp = make_response("Admin login required", 401)
        resp.headers["WWW-Authenticate"] = 'Basic realm="Admin Panel"'
        return resp
    return None

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
    ip = request.remote_addr or "unknown"
    ua = (request.headers.get("User-Agent") or "").lower()
    path = request.path

    # Block host header spoofing
    if request.host != request.headers.get("Host", ""):
        abort(403)

    # Block empty User-Agent
    if not ua.strip():
        abort(403)

    # Good bots - skip all checks
    if is_good_bot():
        return

    # Maintenance mode
    if is_maintenance() and not path.startswith(("/admin", "/maintenance-", "/blocked.html", "/maintenance.html")):
        return send_from_directory(SITE_DIR, "maintenance.html")

    # Bad bots - delay + block
    if is_bad_bot():
        time.sleep(DELAY_BAD_BOT)
        return send_from_directory(SITE_DIR, "blocked.html"), 403

    # Missing browser headers (except for robots.txt, sitemap.xml)
    if "accept" not in request.headers and not path.endswith((".txt", ".xml")):
        abort(403)

    # Simple rate limiting
    now = time.time()
    times = [t for t in RATE_LIMIT.get(ip, []) if now - t < 10]
    if len(times) > 12:
        time.sleep(3)
        abort(429)
    times.append(now)
    RATE_LIMIT[ip] = times

# ====================== ROUTES ======================

# Home
@app.route("/")
def home():
    return send_from_directory(SITE_DIR, "index.html")

# Special files
@app.route("/robots.txt")
def robots():
    return send_from_directory(SITE_DIR, "robots.txt")

@app.route("/sitemap.xml")
def sitemap():
    resp = send_from_directory(SITE_DIR, "sitemap.xml")
    resp.headers["Content-Type"] = "application/xml"
    return resp

# === MAIN CATCH-ALL ROUTE (Fixes /JsonValidator, /ID, etc.) ===
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    # Redirect clean tool URLs: /JsonValidator → /JsonValidator/
    if path in TOOL_DIRS:
        return redirect(f"/{path}/", code=301)

    # If path ends with / → try to serve index.html inside
    if path.endswith("/"):
        file_path = path + "index.html"
    else:
        file_path = path

    # Full path on disk
    full_path = os.path.normpath(os.path.join(SITE_DIR, file_path))

    # Prevent directory traversal
    if not full_path.startswith(os.path.abspath(SITE_DIR)):
        abort(403)

    if os.path.isfile(full_path):
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(directory, filename)

    abort(404)

# ====================== ADMIN PANEL ======================
@app.route("/admin")
def admin_panel():
    auth = require_admin()
    if auth:
        return auth

    status = "ON" if is_maintenance() else "OFF"
    html = f"""
    <h1 style="font-family: Arial; text-align:center; color:#333;">Admin Panel</h1>
    <p style="text-align:center; font-size:18px;">Maintenance Mode: <strong>{status}</strong></p>
    <div style="text-align:center; margin:40px;">
        <form method="post" action="/maintenance-on" style="display:inline;">
            <button style="padding:15px 30px; background:#d9534f; color:white; border:none; font-size:18px; cursor:pointer;">
                Turn Maintenance ON
            </button>
        </form>
        &nbsp;&nbsp;&nbsp;
        <form method="post" action="/maintenance-off" style="display:inline;">
            <button style="padding:15px 30px; background:#5cb85c; color:white; border:none; font-size:18px; cursor:pointer;">
                Turn Maintenance OFF
            </button>
        </form>
    </div>
    <hr>
    <p style="text-align:center; color:#888; font-size:14px;">Protected area • {request.remote_addr}</p>
    """
    return render_template_string(html)

@app.route("/maintenance-on", methods=["POST"])
def maintenance_on():
    auth = require_admin()
    if auth:
        return auth
    open(MAINTENANCE_FILE, "a").close()
    return redirect("/admin")

@app.route("/maintenance-off", methods=["POST"])
def maintenance_off():
    auth = require_admin()
    if auth:
        return auth
    if os.path.exists(MAINTENANCE_FILE):
        os.remove(MAINTENANCE_FILE)
    return redirect("/admin")

# ====================== RUN ======================
if __name__ == "__main__":
    print("Server starting... Access /admin with your password!")
    app.run(host="0.0.0.0", port=3000, threaded=True)
