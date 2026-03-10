from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# API-Key laden
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
print("GROQ_API_KEY loaded:", GROQ_API_KEY is not None)

# Gesprächsverlauf (Kurzzeitgedächtnis)
conversation_history = []

# Maximale Anzahl Nachrichten, die behalten werden (wenig Tokens)
MAX_MESSAGES = 10


def trim_history():
    """Kürzt den Verlauf automatisch, wenn er zu lang wird."""
    global conversation_history
    if len(conversation_history) > MAX_MESSAGES:
        conversation_history = conversation_history[-MAX_MESSAGES:]


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    question = data.get("question")

    # User-Nachricht speichern
    conversation_history.append({"role": "user", "content": question})
    trim_history()

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Humorvoller, deutscher, kurzer Temi
    system_prompt = (
        "Du bist Temi, ein humorvoller, freundlicher KI-Assistent. "
        "Du antwortest immer kurz, klar und auf Deutsch. "
        "Dein Humor ist leicht, charmant und nicht übertrieben. "
        "Wenn der Nutzer nach deinem Namen fragt, sagst du: 'Ich heiße Temi.' "
        "Du wiederholst niemals die Frage des Nutzers. "
        "Du antwortest direkt, locker und menschlich."
    )

    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "system", "content": system_prompt}
        ] + conversation_history
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )

    result = response.json()
    print("Groq response:", result)

    if "choices" not in result:
        return jsonify({
            "error": True,
            "message": result.get("error", "Unknown error")
        }), 500

    answer = result["choices"][0]["message"]["content"]

    # Antwort speichern
    conversation_history.append({"role": "assistant", "content": answer})
    trim_history()

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
