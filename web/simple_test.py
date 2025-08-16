#!/usr/bin/env python3
import sys

print("Python script started")

try:
    from flask import Flask

    print("Flask imported successfully")

    app = Flask(__name__)
    print("Flask app created")

    @app.route("/")
    def index():
        return "<h1>Hello World!</h1><p>Flask is working</p>"

    print("Route defined")

    if __name__ == "__main__":
        print("Starting Flask server...")
        app.run(host="127.0.0.1", port=5000, debug=True)

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
