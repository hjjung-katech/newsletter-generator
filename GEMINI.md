# GEMINI.md

## Project Overview

This project is a Python CLI tool called "newsletter-generator". It generates newsletters by collecting and summarizing news articles based on user-provided keywords or a domain. The tool supports multiple LLM providers (Google Gemini, OpenAI GPT, Anthropic Claude) for content processing and can send the generated newsletters via email using Postmark. It also features a web interface built with Flask for interactive use.

The project is well-structured, with separate modules for different functionalities like article collection, content composition, and delivery. It uses `typer` for the CLI, `LangGraph` for the newsletter generation workflow, and `pydantic` for configuration management.

## Building and Running

### Prerequisites

- Python 3.10+
- An environment with the required dependencies installed.

### Installation

1.  **Set up the environment:**
    It is recommended to use a virtual environment.

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the application:**
    - Create a `.env` file by copying the `.env.example` file.
    - Populate the `.env` file with the necessary API keys and configuration values. The `setup_env.py` script can be used to automate this process.
    - `python setup_env.py`

### Running the Application

-   **CLI:**
    The main entry point for the CLI is `newsletter/__main__.py`. You can run the application using the following command:

    ```bash
    python -m newsletter run --keywords "AI,machine learning" --to your@email.com
    ```

    For a full list of commands and options, run:
    ```bash
    python -m newsletter --help
    ```

-   **Web Interface:**
    The project also includes a Flask-based web interface. To run the web server, use the following command:

    ```bash
    python test_server.py
    ```
    The web interface will be available at `http://localhost:5000`.

### Testing

The project uses `pytest` for testing. To run the tests, use the following command:

```bash
pytest
```

## Development Conventions

### Code Style

The project uses `black` for code formatting, `isort` for import sorting, and `flake8` for linting. It is recommended to use the `pre-commit` hooks to automatically enforce the code style.

-   **Install pre-commit hooks:**
    ```bash
    pre-commit install
    ```

-   **Run pre-commit hooks on all files:**
    ```bash
    pre-commit run --all-files
    ```

### Branching and Commits

The project does not have a strict branching model defined in the provided files. However, it is recommended to use a feature-branching workflow.

### Dependencies

The project's dependencies are managed in the `pyproject.toml` and `requirements.txt` files. Use `pip-compile` or a similar tool to keep the `requirements.txt` file up-to-date with the dependencies defined in `pyproject.toml`.

### Logging

The project uses a custom logger defined in `newsletter/utils/logger.py`. Use the `get_logger()` function to get a logger instance and use it for logging.
