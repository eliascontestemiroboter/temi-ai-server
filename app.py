from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import requests
import os
import platform
import psutil
from datetime import datetime

app = Flask(__name__)

# Secret Key für Sessions (Login)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-temi-key")

# API-Key laden
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
print("GROQ_API_KEY loaded:", GROQ_API_KEY is not None)

# Gesprächsverlauf (Kurzzeitgedächtnis für KI)
conversation_history = []

# Maximale Anzahl Nachrichten, die behalten werden
MAX_MESSAGES = 10

# Logs für Dashboard
logs = []  # jedes Element: {"timestamp", "question", "answer", "tokens"}

# Token-Zähler (grob geschätzt)
daily_token_usage = 0


def trim_history():
    """Kürzt den Verlauf automatisch, wenn er zu lang wird."""
    global conversation_history
    if len(conversation_history) > MAX_MESSAGES:
        conversation_history = conversation_history[-MAX_MESSAGES:]


def estimate_tokens(text: str) -> int:
    """Sehr grobe Token-Schätzung über Wortanzahl."""
    if not text:
        return 0
    return len(text.split())


def is_logged_in():
    return session.get("logged_in") is True


@app.route("/")
def index():
    if not is_logged_in():
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


# ---------- LOGIN ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == "elias" and password == "elias":
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Falsche Zugangsdaten.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- DASHBOARD ----------

@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("dashboard.html")


# ---------- API: KI GENERATE ----------

@app.route("/generate", methods=["POST"])
def generate():
    global daily_token_usage

    data = request.json
    question = data.get("question", "")

    # User-Nachricht speichern
    conversation_history.append({"role": "user", "content": question})
    trim_history()

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "Du bist Temi, ein humorvoller, freundlicher KI-Assistent. "
        "Du antwortest immer kurz, klar und auf Deutsch. "
        "Dein Humor ist leicht, charmant und nicht übertrieben. "
        "Wenn der Nutzer nach deinem Namen fragt, sagst du: 'Ich heiße Temi.' "
        "Du wiederholst niemals die Frage des Nutzers. "
        "Du antwortest direkt, locker und menschlich."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt}
        ] + conversation_history
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20
        )
        result = response.json()
    except Exception as e:
        return jsonify({"answer": f"Fehler bei Groq: {str(e)}"})

    if "choices" not in result:
        return jsonify({
            "error": True,
            "message": result.get("error", "Unknown error")
        }), 500

    answer = result["choices"][0]["message"]["content"]

    # Antwort speichern
    conversation_history.append({"role": "assistant", "content": answer})
    trim_history()

    # Tokenverbrauch grob schätzen
    q_tokens = estimate_tokens(question)
    a_tokens = estimate_tokens(answer)
    used_tokens = q_tokens + a_tokens
    daily_token_usage += used_tokens

    # Log-Eintrag
    logs.append({
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": answer,
        "tokens": used_tokens
    })

    return jsonify({"answer": answer})


# ---------- API: LOGS & STATS ----------

@app.route("/api/logs")
def api_logs():
    if not is_logged_in():
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(logs[-100:])


@app.route("/api/stats")
def api_stats():
    if not is_logged_in():
        return jsonify({"error": "unauthorized"}), 401

    daily_limit = 1_000_000
    remaining = max(daily_limit - daily_token_usage, 0)

    return jsonify({
        "daily_used": daily_token_usage,
        "daily_limit": daily_limit,
        "daily_remaining": remaining,
        "total_logs": len(logs)
    })


# ---------- API: SYSTEM INFO ----------

@app.route("/api/system")
def api_system():
    if not is_logged_in():
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({
        "python_version": platform.python_version(),
        "system": platform.system(),
        "machine": platform.machine(),
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage": psutil.virtual_memory().percent
    })


# ---------- WICHTIG: KEIN app.run() ----------
# Gunicorn startet die App automatisch
