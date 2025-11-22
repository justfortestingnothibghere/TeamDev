from flask import Flask, request, send_from_directory, abort, redirect, render_template_string, make_response
import os
import time

app = Flask(__name__)

# ==================== CONFIG ====================
SITE_DIR = os.path.abspath(".")
MAINTENANCE_FILE = "maintenance_on.flag"
ADMIN_PASS_FILE = "admin_password.txt"

GOOD_BOTS = ["googlebot", "bingbot", "duckduckbot"]
BAD_UA_PARTS = ["curl", "wget", "python", "headless", "scrapy"]

DELAY_BAD_BOT = 3
RATE_LIMIT = {}

TOOL_DIRS = ["jsonvalidator", "id", "review", "xmltool"]

# ==================== HELPERS ====================
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
        with open(ADMIN_PASS_FILE) as f:
            passwords = [p.strip() for p in f if p.strip()]
        return auth.password in passwords
    except:
        return False

def require_admin():
    if not check_admin_auth():
        r = make_response("Admin auth required", 401)
        r.headers["WWW-Authenticate"] = 'Basic realm="Admin Panel"'
        return r
    return None

# ==================== HEADERS ====================
@app.after_request
def add_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

# ==================== FIREWALL ====================
@app.before_request
def firewall():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = (request.headers.get("User-Agent") or "").lower()
    path = request.path

    # block empty UA
    if not ua and ip not in ("127.0.0.1", "localhost"):
        abort(403)

    if is_good_bot():
        return

    if is_maintenance() and not path.startswith(("/admin", "/maintenance", "/blocked.html")):
        return send_from_directory(SITE_DIR, "blocked.html")

    if is_bad_bot():
        time.sleep(DELAY_BAD_BOT)
        return send_from_directory(SITE_DIR, "blocked.html"), 403

    # very light rate limit
    now = time.time()
    times = [t for t in RATE_LIMIT.get(ip, []) if now - t < 10]
    if len(times) > 25:
        abort(429)
    times.append(now)
    RATE_LIMIT[ip] = times

# ==================== ROUTES ====================
@app.route("/")
def home():
    return send_from_directory(SITE_DIR, "index.html")

@app.route("/robots.txt")
def robots():
    return send_from_directory(SITE_DIR, "robots.txt")

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(SITE_DIR, "sitemap.xml")

# ========== SMART STATIC SERVING ==========
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_files(path):
    lower_path = path.lower()

    # redirect folders without /
    if lower_path in TOOL_DIRS and not path.endswith("/"):
        return redirect(f"/{path}/", code=301)

    if path.endswith("/"):
        file_path = path + "index.html"
    else:
        file_path = path

    full_path = os.path.abspath(os.path.join(SITE_DIR, file_path))

    if not full_path.startswith(SITE_DIR):
        abort(403)

    if os.path.isfile(full_path):
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(directory, filename)

    abort(404)

# ==================== ADMIN ====================
@app.route("/admin")
def admin_panel():
    a = require_admin()
    if a:
        return a

    status = "ON" if is_maintenance() else "OFF"
    return render_template_string(f"""
    <h1 style="text-align:center">Admin Panel</h1>
    <p style="text-align:center">Maintenance: <b>{status}</b></p>
    <form method="post" action="/maintenance-on" style="text-align:center">
        <button>Turn ON</button>
    </form>
    <form method="post" action="/maintenance-off" style="text-align:center">
        <button>Turn OFF</button>
    </form>
    """)

@app.route("/maintenance-on", methods=["POST"])
def mon():
    a = require_admin()
    if a:
        return a
    open(MAINTENANCE_FILE, "w").close()
    return redirect("/admin")

@app.route("/maintenance-off", methods=["POST"])
def moff():
    a = require_admin()
    if a:
        return a
    if os.path.exists(MAINTENANCE_FILE):
        os.remove(MAINTENANCE_FILE)
    return redirect("/admin")

# ==================== RUN ====================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
