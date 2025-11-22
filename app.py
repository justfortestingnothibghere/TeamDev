from flask import Flask, request, Response, send_from_directory, abort
import os
import time

app = Flask(__name__)

# ===== CONFIG =====
SITE_DIR = "./"   # same folder where index.html is
BLOCKED_UA = [
    "curl", "wget", "python", "httpclient", "scrapy",
    "libwww", "go-http-client", "bot", "spider", "crawler"
]

DELAY_ON_BOT = 2

# ===== FIREWALL =====
@app.before_request
def block_bad_clients():
    ua = (request.headers.get("User-Agent") or "").lower()

    # Empty UA = block
    if ua.strip() == "":
        abort(403)

    # Block bad agents
    for bad in BLOCKED_UA:
        if bad in ua:
            time.sleep(DELAY_ON_BOT)
            abort(403)

    # No browser-like headers
    if "accept" not in request.headers:
        abort(403)

# ===== SERVE INDEX =====
@app.route("/")
def home():
    return send_from_directory(SITE_DIR, "index.html")

# ===== SERVE OTHER FILES =====
@app.route("/<path:path>")
def serve_files(path):
    full_path = os.path.join(SITE_DIR, path)
    if os.path.exists(full_path):
        return send_from_directory(SITE_DIR, path)
    else:
        abort(404)

# ===== RUN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
