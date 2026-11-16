"""Start the local MyTaxUSA application with uv run run.py."""
from app import create_app

app = create_app({'SEED_SAMPLE_RETURNS': True})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
