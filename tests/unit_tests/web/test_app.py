from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Newsletter Generator - Test</title>
    </head>
    <body>
        <h1>Newsletter Generator Web Service</h1>
        <p>Test page is working!</p>
        <p>Current time: <span id="time"></span></p>
        <script>
            document.getElementById('time').textContent = new Date().toLocaleString();
        </script>
    </body>
    </html>
    """


@app.route("/health")
def health():
    return {"status": "ok", "message": "Test server is running"}


if __name__ == "__main__":
    print("Starting test Flask server on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
