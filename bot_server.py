from flask import Flask, request, jsonify, render_template_string
from marketing_agent_safe import ask_chatgpt, load_websites
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json(force=True)
        print("DEBUG /query received JSON:", data)

        question = data.get("question", "")
        if not question:
            print("DEBUG /query missing question")
            return jsonify({"error": "No question provided."}), 400

        websites = load_websites()
        answer = ask_chatgpt(question, websites, use_history=True)
        return jsonify({"answer": answer})

    except Exception as e:
        print("ERROR in /query:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/chat")
def chat_page():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Prebid Chatbot</title>
      <style>
        body { font-family: Arial; margin: 0; padding: 0; }
        #chatbox { height: 90vh; overflow-y: scroll; padding: 1em; }
        #inputbox {
          position: fixed; bottom: 0; width: 100%;
          display: flex; padding: 1em; background: #f0f0f0;
        }
        input { flex: 1; padding: 0.5em; font-size: 1em; }
        button { padding: 0.5em 1em; margin-left: 0.5em; }
        .message { margin: 0.5em 0; }
        .bot { color: #333; }
        .user { color: #0056d6; }
      </style>
    </head>
    <body>
      <div id="chatbox">
        <div class="message bot"><b>Bot:</b> Hi there! Ask me anything about Prebid.</div>
      </div>
      <div id="inputbox">
        <input id="question" placeholder="Ask a question about Prebid..." />
        <button onclick="send()">Send</button>
      </div>
      <script>
        const chatbox = document.getElementById('chatbox');
        const input = document.getElementById('question');

        async function send() {
          const q = input.value.trim();
          if (!q) return;
          chatbox.innerHTML += `<div class="message user"><b>You:</b> ${q}</div>`;
          input.value = "";

          const res = await fetch("/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q })
          });
          const data = await res.json();
          const a = data.answer || data.error || "No response";
          chatbox.innerHTML += `<div class="message bot"><b>Bot:</b> ${a}</div>`;
          chatbox.scrollTop = chatbox.scrollHeight;
        }

        input.addEventListener("keypress", e => {
          if (e.key === "Enter") send();
        });
      </script>
    </body>
    </html>
    """)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
