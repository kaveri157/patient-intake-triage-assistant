"""
PS06 - Transaction Risk Investigation Assistant
Single entrypoint: `python app.py` serves backend + frontend on port 8000.
"""
import os
import json
from flask import Flask, jsonify, send_from_directory

from src import rules
from src.gemini_client import generate_narrative

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "customers.json")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "dist")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


def _load_customers():
    if not os.path.exists(DATA_PATH):
        # generate on the fly if missing, so a fresh clone still works
        from src.data_gen import generate_customers
        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        with open(DATA_PATH, "w") as f:
            json.dump(generate_customers(), f, indent=2)
    with open(DATA_PATH) as f:
        return json.load(f)


CUSTOMERS = {c["customer_id"]: c for c in _load_customers()}


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api/customers")
def list_customers():
    # Run the (cheap, deterministic) rule engine for every customer so the
    # sidebar can show a risk indicator without a per-customer LLM call.
    out = []
    for c in CUSTOMERS.values():
        findings = rules.investigate(c)
        out.append({
            "customer_id": c["customer_id"],
            "name": c["name"],
            "num_txns": len(c["history"]),
            "needs_attention": findings["needs_attention"],
            "num_findings": findings["num_findings"],
        })
    return jsonify(out)


@app.get("/api/investigate/<customer_id>")
def investigate(customer_id):
    customer = CUSTOMERS.get(customer_id)
    if not customer:
        return jsonify({"error": f"unknown customer_id '{customer_id}'"}), 404

    try:
        findings = rules.investigate(customer)
    except Exception as e:
        # deterministic logic failing is a real bug -> surface it, don't guess
        return jsonify({"error": f"rule engine failed: {e}"}), 500

    narrative, source = generate_narrative(findings)
    findings["narrative"] = narrative
    findings["narrative_source"] = source  # transparency: "gemini" vs "fallback_template"
    findings["history"] = customer["history"]  # full ledger, for the transaction table view
    return jsonify(findings)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "customers_loaded": len(CUSTOMERS)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
