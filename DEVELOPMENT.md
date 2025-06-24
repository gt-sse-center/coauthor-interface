# Development Guide

Welcome to the development documentation for this project! This guide will help you set up your environment, run the application, and contribute effectively.

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/coauthor-interface.git
cd coauthor-interface
```

### 2. Install Dependencies (with `uv`)
This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management instead of pip.

If you don't have `uv` installed:
```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

Then, to install dependencies:
```bash
uv sync
uv run python -m spacy download en_core_web_md
```

---

## 🛠️ Configuration and Disabling OpenAI in Development

- API keys are read from `config/api_keys.csv`.
- To run the backend **without** an OpenAI key, set the `DEV_MODE` environment variable to `true`:
  ```bash
  export DEV_MODE=true
  ```
  In this mode, all calls to `/api/query` will return empty suggestions (`[]`).

---

## 🧪 Testing

To run tests and generate a coverage report:
```bash
uv run pytest
```
This will create an HTML coverage report in the `htmlcov` directory.

To view the coverage report in your browser:
```bash
cd htmlcov
python -m http.server [PORT]
```
Then open `http://localhost:[PORT]` in your browser (replace `[PORT]` with your desired port, e.g., 8000).

If you want to run tests **without** generating a coverage report, add the `--nocov` flag:
```bash
uv run pytest --nocov
```

---

## 🧹 Code Style & Linting

- Follow [PEP8](https://peps.python.org/pep-0008/) for Python code.
- Use `ruff` for linting and formatting:
  ```bash
  uvx ruff format
  uvx ruff check --fix
  ```

---

## 🤝 Contributing

1. Fork the repository and create your branch from `main`.
2. Write clear, concise commit messages.
3. Ensure all tests pass before submitting a PR.
4. Open a pull request and describe your changes.

---

## 🛠️ Troubleshooting

- **Dependency issues**: Ensure you're using `uv` and not `pip` directly.
- **API key errors**: Check `config/api_keys.csv` or use `DEV_MODE=true` for local development.

---

For further questions, please open an issue or contact the maintainers.
