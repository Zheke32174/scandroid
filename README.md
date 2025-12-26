# Scandroid

Utilities to bridge work across Google Colab, OpenAI Codex-compatible APIs, and GitHub from a single notebook.

## Contents
- `scandroid.ipynb`: Notebook with ready-to-run cells for Colab, Codex, and GitHub connectivity.
- `integrations.py`: Lightweight helpers for mounting Google Drive in Colab, calling OpenAI models, and retrieving GitHub user data.
- `bridge_setup.md`: Notes on capturing filesystem snapshots (e.g., `groot.html`).

## Quick start
1. Create a virtual environment (optional) and install the runtime dependencies:
   ```bash
   pip install --upgrade openai requests
   ```
2. Open the notebook directly in Colab using the badge at the top of `scandroid.ipynb` or via [this link](https://colab.research.google.com/github/Zheke32174/scandroid/blob/main/scandroid.ipynb).
3. Add your secrets as environment variables inside Colab or your local shell:
   ```bash
   export OPENAI_API_KEY="sk-..."
   export GITHUB_TOKEN="ghp_..."  # or GH_TOKEN
   ```

## Using the helpers
The `integrations.py` module exposes three convenience functions:
- `mount_colab_drive(force_remount=False)`: Mounts your Google Drive at `/content/drive` inside Colab.
- `run_codex_completion(prompt, model="gpt-4o-mini", api_key=None, **kwargs)`: Sends a prompt to an OpenAI chat-completions model for code generation or assistance.
- `get_github_user(token=None)`: Fetches the authenticated GitHub user profile using the provided token or `GITHUB_TOKEN`/`GH_TOKEN`.

Example usage inside the notebook:
```python
from integrations import mount_colab_drive, run_codex_completion, get_github_user

# Mount Google Drive (prompts for authorization inside Colab)
# mount_colab_drive()

# Query GitHub identity
# me = get_github_user()
# print(me["login"])

# Generate code with Codex-style completion
# code = run_codex_completion("Write a Python function that reverses a string")
# print(code)
```

## Tips
- When running in GitHub Codespaces, the `.devcontainer` files will bootstrap a consistent environment.
- Keep tokens in environment variables or a local secrets manager; avoid committing credentials to the repository.
- Update `bridge_setup.md` if you change how filesystem snapshots are generated.
