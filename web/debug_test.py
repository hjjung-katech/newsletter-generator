#!/usr/bin/env python3
"""Debug test for Flask template rendering"""

import os

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def test_template():
    try:
        return render_template("index.html")
    except Exception as e:
        return f"Template error: {str(e)}"


@app.route("/debug")
def debug_info():
    template_dir = app.template_folder
    template_path = os.path.join(template_dir, "index.html")

    info = {
        "template_folder": template_dir,
        "template_path": template_path,
        "template_exists": os.path.exists(template_path),
        "current_dir": os.getcwd(),
        "app_root": app.root_path,
    }

    return info


if __name__ == "__main__":
    print(f"Flask app root: {app.root_path}")
    print(f"Template folder: {app.template_folder}")
    print(f"Current directory: {os.getcwd()}")
    app.run(debug=True, port=5001)
