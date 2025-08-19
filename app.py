# ------------------------------
# File: app.py
# ------------------------------
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ------------------------------
# Helpers
# ------------------------------
SENSITIVE_KEYS = {
    "password", "passwd", "secret", "apikey", "api_key", "key", "token",
    "access_key", "secret_key", "certificate", "cert", "uri", "url",
}


def _redact(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: ("(redacted)" if _is_sensitive(k) else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    # strings / numbers → keep
    return value


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(part in k for part in SENSITIVE_KEYS)


def load_json_env(var: str) -> Dict[str, Any] | None:
    raw = os.environ.get(var)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return {"_error": f"Invalid JSON in {var}"}


def load_file_vcap(path_env: str = "VCAP_SERVICES_FILE_PATH") -> Dict[str, Any] | None:
    p = os.environ.get(path_env)
    if not p:
        return None
    try:
        text = Path(p).read_text(encoding="utf-8")
        return json.loads(text)
    except FileNotFoundError:
        return {"_error": f"File not found: {p}"}
    except Exception:
        return {"_error": f"Invalid JSON in file: {p}"}


def load_k8s_bindings(base: str = "/etc/cf-service-bindings") -> List[Dict[str, Any]]:
    base_path = Path(base)
    if not base_path.exists():
        return []

    items: List[Dict[str, Any]] = []
    for d in sorted([p for p in base_path.iterdir() if p.is_dir()]):
        entry: Dict[str, Any] = {
            "binding_name": d.name,
            "data": {}
        }
        for f in d.iterdir():
            if f.is_file():
                try:
                    # Values are arbitrary bytes; try to decode as utf-8, else hex
                    content = f.read_bytes()
                    try:
                        val = content.decode("utf-8").strip()
                    except Exception:
                        val = content.hex()
                    if f.name == "binding-guid":
                        entry["binding_guid"] = val
                        next
                    entry["data"][f.name] = val
                except Exception:
                    entry["data"][f.name] = "(unreadable)"
        items.append(entry)
    return items


def extract_bindings_from_vcap(vcap_services: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    if not vcap_services:
        return []
    if "_error" in vcap_services:
        return [{"_error": vcap_services["_error"]}]

    flat: List[Dict[str, Any]] = []
    for svc_label, arr in vcap_services.items():
        if not isinstance(arr, list):
            continue
        for inst in arr:
            flat.append({
                "service_label": svc_label,
                "plan": inst.get("plan", "—"),
                "instance_name": inst.get("name", "—"),
                "instance_guid": inst.get("instance_guid", "—"),
                "binding_guid": inst.get("binding_guid", "—"),
                "binding_name": inst.get("binding_name", "—"),
                "credentials": inst.get("credentials", {}),
            })
    return flat


def app_meta() -> Dict[str, Any]:
    vapp = load_json_env("VCAP_APPLICATION") or {}
    limits = vapp.get("limits", {})
    return {
        "cf_api": vapp.get("cf_api", "—"),
        "app_name": vapp.get("application_name") or vapp.get("name") or os.environ.get("APP_NAME", "—"),
        "app_uris": vapp.get("application_uris", []),
        "instance_index": vapp.get("instance_index", os.environ.get("CF_INSTANCE_INDEX", "—")),
        "space_name": vapp.get("space_name", "—"),
        "org_name": vapp.get("organization_name", "—"),
        "memory_limit": limits.get("mem", os.environ.get("MEMORY_LIMIT", "—")),
        "disk_limit": limits.get("disk", os.environ.get("DISK_LIMIT", "—")),
    }


# ------------------------------
# Routes
# ------------------------------
@app.get("/")
def index():
    meta = app_meta()

    vcap_env = load_json_env("VCAP_SERVICES")
    vcap_from_env = extract_bindings_from_vcap(vcap_env)

    vcap_file_raw = load_file_vcap()
    vcap_from_file = extract_bindings_from_vcap(vcap_file_raw)

    k8s_bindings = load_k8s_bindings()

    # Redacted copies for safe rendering
    vcap_env_redacted = [{**b, "credentials": _redact(b.get("credentials", {}))} for b in vcap_from_env]
    vcap_file_redacted = [{**b, "credentials": _redact(b.get("credentials", {}))} for b in vcap_from_file]
    k8s_redacted = [{**b, "data": _redact(b.get("data", {}))} for b in k8s_bindings]

    return render_template(
        "index.html",
        meta=meta,
        vcap_env=vcap_env_redacted,
        vcap_file=vcap_file_redacted,
        k8s=k8s_redacted,
        vcap_env_error=(vcap_env or {}).get("_error"),
        vcap_file_error=(vcap_file_raw or {}).get("_error"),
    )


@app.get("/health")
def health():
    return ("OK", 200)


@app.get("/bindings.json")
def bindings_json():
    # Optional debug endpoint (redact unless reveal=1)
    reveal = request.args.get("reveal") == "1"

    vcap_env = extract_bindings_from_vcap(load_json_env("VCAP_SERVICES"))
    vcap_file = extract_bindings_from_vcap(load_file_vcap())
    k8s_bindings = load_k8s_bindings()

    if not reveal:
        vcap_env = [{**b, "credentials": _redact(b.get("credentials", {}))} for b in vcap_env]
        vcap_file = [{**b, "credentials": _redact(b.get("credentials", {}))} for b in vcap_file]
        k8s_bindings = [{**b, "data": _redact(b.get("data", {}))} for b in k8s_bindings]

    return jsonify({
        "env": vcap_env,
        "file": vcap_file,
        "k8s": k8s_bindings,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)