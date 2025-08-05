#!/usr/bin/env python3
"""Build a standalone executable for the Flask web server using PyInstaller.

This script bundles Python, required modules, templates, static assets and the
newsletter templates into a single executable. The resulting binary can run on
Windows without a separate Python installation.
"""

import os
import PyInstaller.__main__


def build():
    project_root = os.path.abspath(os.path.dirname(__file__))
    os.chdir(project_root)

    datas = [
        f"templates{os.pathsep}templates",
        f"{os.path.join('web', 'templates')}{os.pathsep}templates",
        f"{os.path.join('web', 'static')}{os.pathsep}static",
    ]

    args = [
        os.path.join('web', 'app.py'),
        '--onefile',
        '--name', 'newsletter_web',
    ]

    for data in datas:
        args += ['--add-data', data]

    PyInstaller.__main__.run(args)


if __name__ == '__main__':
    build()
