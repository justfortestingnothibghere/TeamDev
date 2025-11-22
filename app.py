from flask import Flask, request, send_from_directory, abort, redirect, render_template_string, make_response
import os
import time

app = Flask(__name__)

# ====================== CONFIG ======================
SITE_DIR = os.path.abspath(".")
MAINTENANCE_FILE = "maintenance_on.flag"
ADMIN_PASS_FILE = "admin_password.txt"

# Good bots
GOOD_BOTS = [
    "googlebot", "bingbot", "duckduckbot", "yandexbot",
    "facebookexternalhit", "twitterbot", "linkedinbot"
]

# Bad bots
BAD_UA_PARTS = [
    "curl", "wget", "python", "scrapy", "headless",
    "phantomjs", "semrush", "ahrefs", "mj12bot", "dotbot"
]

DELAY_BAD_BOT = 4
RATE_LIMIT = {}

# Tool folders
TOOL_DIRS = ["jsonvalidator", "id", "review", "xmltool"]

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
            passwords = [p.strip() for p in f if p.strip()]
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

# ====================== SMART FIREWALL ======================
@app.before_request
def firewall():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    ua = (request.headers.get("User-Agent") or "").lower()
    path = request.path

    # Block empty User-Agent (but allow localhost / healthchecks)
    if not ua and ip not in ("127.0.0.1", "localhost"):
        abort(403)

    # Good bots - skip heavy checks
    if is_good_bot():
        return

    # Maintenance mode
    if is_maintenance() and not path.startswith(("/admin", "/maintenance-", "/blocked.html", "/maintenance.html")):
        return send_from_directory(SITE_DIR, "maintenance.html")

    # Bad bots
    if is_bad_bot():
        time.sleep(DELAY_BAD_BOT)
        return send_from_directory(SITE_DIR, "blocked.html"), 403

    # Rate limit
    now = time.time()
    times = [t for t in RATE_LIMIT.get(ip, []) if now - t < 10]
    if len(times) > 20:
        abort(429)
    times.append(now)
    RATE_LIMIT[ip] = times

# ====================== ROUTES ======================
@app.route("/")
def home():
    return send_from_directory(SITE_DIR, "index.html")

@app.route("/robots.txt")
def robots():
    return send_from_directory(SITE_DIR, "robots.txt")

@app.route("/sitemap.xml")
def sitemap():
    resp = send_from_directory(SITE_DIR, "sitemap.xml")
    resp.headers["Content-Type"] = "application/xml"
    return resp

# ====================== CATCH ALL ======================
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    lower_path = path.lower()

    # Redirect clean tool URLs
    if lower_path in TOOL_DIRS and not path.endswith("/"):
        return redirect(f"/{path}/", code=301)

    # If folder → serve index.html
    if path.endswith("/"):
        file_path = path + "index.html"
    else:
        file_path = path

    # Secure path resolve (prevents traversal)
    full_path = os.path.abspath(os.path.join(SITE_DIR, file_path))

    if not full_path.startswith(SITE_DIR):
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
    <h1 style="font-family: Arial; text-align:center;">Admin Panel</h1>
    <p style="text-align:center;">Maintenance Mode: <b>{status}</b></p>
    <div style="text-align:center;">
        <form method="post" action="/maintenance-on">
            <button style="padding:15px; background:#d9534f; color:white;">Turn ON</button>
        </form>
        <br>
        <form method="post" action="/maintenance-off">
            <button style="padding:15px; background:#5cb85c; color:white;">Turn OFF</button>
        </form>
    </div>
    <p style="text-align:center; font-size:12px;">IP: {request.remote_addr}</p>
    """
    return render_template_string(html)

@app.route("/maintenance-on", methods=["POST"])
def maintenance_on():
    auth = require_admin()
    if auth:
        return auth
    open(MAINTENANCE_FILE, "w").close()
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
    print("✅ Server running — open /admin for panel")
    app.run(host="0.0.0.0", port=3000, threaded=True)
