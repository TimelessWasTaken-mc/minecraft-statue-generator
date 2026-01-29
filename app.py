import base64
import io
import json
import zipfile
from dataclasses import dataclass
from typing import Optional

import requests
from flask import Flask, request, send_file
from PIL import Image

app = Flask(__name__, static_folder="static", static_url_path="")

@app.get("/")
def home():
    return app.send_static_file("index.html")

@dataclass
class BuildConfig:
    pose: str = "neutral"
    hollow: bool = True
    name_label: bool = False
    label_y: int = 3
    label_text: str = ""
    username: Optional[str] = None

def fetch_skin_by_username(username: str) -> Image.Image:
    """
    Mojang: username -> UUID -> session profile -> skin URL -> PNG
    """
    r = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", timeout=12)
    if r.status_code != 200:
        raise ValueError(f"Could not find username '{username}'.")
    uuid = r.json()["id"]

    r = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}", timeout=12)
    r.raise_for_status()
    props = r.json().get("properties", [])
    if not props:
        raise ValueError("No profile properties found.")
    value_b64 = props[0]["value"]

    profile = json.loads(base64.b64decode(value_b64).decode("utf-8"))
    skin_url = profile["textures"]["SKIN"]["url"]

    png = requests.get(skin_url, timeout=12).content
    return Image.open(io.BytesIO(png)).convert("RGBA")

def load_skin() -> Image.Image:
    f = request.files.get("skin")
    username = (request.form.get("username") or "").strip()

    if f and f.filename:
        return Image.open(f.stream).convert("RGBA")
    if username:
        return fetch_skin_by_username(username)
    raise ValueError("Upload a PNG skin OR enter a username.")

def parse_config() -> BuildConfig:
    pose = request.form.get("pose", "neutral")
    hollow = request.form.get("hollow", "on") == "on"
    name_label = request.form.get("name_label", "off") == "on"
    label_y = int(request.form.get("label_y", "3"))
    label_text = (request.form.get("label_text") or "").strip()
    username = (request.form.get("username") or "").strip() or None
    return BuildConfig(
        pose=pose,
        hollow=hollow,
        name_label=name_label,
        label_y=label_y,
        label_text=label_text,
        username=username,
    )

def generate_zip_placeholder(skin: Image.Image, cfg: BuildConfig) -> bytes:
    """
    Placeholder output so your Render deployment and iPad workflow work immediately.
    Replace this with the real statue generator later.
    """
    meta = {
        "pose": cfg.pose,
        "hollow": cfg.hollow,
        "name_label": cfg.name_label,
        "label_y": cfg.label_y,
        "label_text": cfg.label_text,
        "skin_size": skin.size,
        "note": "Placeholder outputs. Replace generator in app.py when ready."
    }

    mcfunction = (
        "# Placeholder statue.mcfunction\n"
        f"# pose={cfg.pose}\n"
        f"# hollow={cfg.hollow}\n"
        "# TODO: write setblock commands here\n"
    ).encode("utf-8")

    # Save input skin for debugging
    skin_buf = io.BytesIO()
    skin.save(skin_buf, format="PNG")
    skin_buf.seek(0)

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("statue.mcfunction", mcfunction)
        z.writestr("meta.json", json.dumps(meta, indent=2))
        z.writestr("input_skin.png", skin_buf.read())
    out.seek(0)
    return out.read()

@app.post("/api/generate")
def api_generate():
    try:
        cfg = parse_config()
        skin = load_skin()
        payload = generate_zip_placeholder(skin, cfg)
    except Exception as e:
        return (str(e), 400)

    return send_file(
        io.BytesIO(payload),
        mimetype="application/zip",
        as_attachment=True,
        download_name="statue.zip",
    )

if __name__ == "__main__":
    # For local testing only. Render uses gunicorn + wsgi.py
    app.run(host="0.0.0.0", port=5000, debug=True)
