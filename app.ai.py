from flask import Flask, request, jsonify
from transformers import pipeline

app = Flask(__name__)
nlp = pipeline("sentiment-analysis")

@app.route("/predict", methods=["POST"])
def predict():
    text = request.json.get("text", "")
    result = nlp(text)
    return jsonify(result)

@app.route("/healthz", methods=["GET"])
@app.route("/healthz/", methods=["GET"])
def healthz():
    return jsonify({"ok": True}), 200
@app.route("/")
def index():
    return {"ok": True, "endpoints": ["/healthz (GET)", "/predict (POST)"]}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)