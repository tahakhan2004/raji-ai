"""RajiAI backend on Modal (free tier, scale-to-zero).

Run from the repo root (the folder containing backend/ and demo-data/):

    modal deploy modal_app.py

Serves the FastAPI API only. The frontend lives on Vercel and calls this
service via the VITE_API_URL env var. Deploy prints a persistent public
HTTPS URL like https://<workspace>--raji-ai-web.modal.run
"""

import modal

app = modal.App("raji-ai")

image = (
    modal.Image.debian_slim(python_version="3.11")
    # CPU-only torch FIRST: installing sentence-transformers afterwards then
    # sees torch already satisfied and skips the ~2.5 GB CUDA bundle.
    .run_commands(
        "pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch"
    )
    .pip_install(
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "scikit-learn",
        "sentence-transformers",
    )
    # Bake the embedding model into the image from the Hugging Face hub.
    # This downloads on Modal's servers (fast), not over your home connection.
    # The backend's loader finds it in the HF cache automatically.
    .run_commands(
        "python -c \"from sentence_transformers import SentenceTransformer; "
        "SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')\""
    )
    # Only the app code + demo data. Deliberately NOT backend/.venv,
    # backend/models (458 MB -- baked into the image above instead),
    # backend/tests, or any caches: keeps the upload small.
    .add_local_dir("backend/app", remote_path="/root/backend/app")
    .add_local_dir("demo-data", remote_path="/root/demo-data")
)


@app.function(image=image, cpu=2.0, memory=4096, min_containers=0)
@modal.asgi_app()
def web():
    import sys

    sys.path.insert(0, "/root/backend")  # mirrors local `uvicorn app.main:app`
    from app.main import app as fastapi_app

    return fastapi_app
