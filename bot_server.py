from flask import Flask, request, jsonify
from marketing_agent_safe import ask_chatgpt, load_websites
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "No question provided."}), 400

    try:
        websites = load_websites()
        answer = ask_chatgpt(question, websites, use_history=True)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)