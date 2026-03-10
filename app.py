from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# API-Key aus Umgebungsvariablen laden
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
print("GROQ_API_KEY loaded:", GROQ_API_KEY is not None)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    question = data.get("question")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Funktionierendes Modell
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "user", "content": question}
        ]
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )

    result = response.json()
    print("Groq response:", result)

    # Fehlerbehandlung
    if "choices" not in result:
        return jsonify({
            "error": True,
            "message": result.get("error", "Unknown error")
        }), 500

    answer = result["choices"][0]["message"]["content"]
    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
