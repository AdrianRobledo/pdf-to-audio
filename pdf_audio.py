# app.py
import os
import uuid
from flask import Flask, request, send_from_directory, jsonify, render_template_string
import fitz  # PyMuPDF
from openai import OpenAI
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow cross-origin requests (needed for Webflow front-end POSTs)

# Use OPENAI_API_KEY from environment (safe, not in repo)
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable not set")

client = OpenAI(api_key=OPENAI_KEY)

HTML_PAGE = """
<!doctype html>
<title>PDF to Audio</title>
<h1>Upload a PDF to Convert to Audio</h1>
<form method="post" enctype="multipart/form-data" action="/">
  <input type="file" name="file" accept="application/pdf" required>
  <input type="submit" value="Convert">
</form>
"""

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def extract_text(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Validate file present
        if "file" not in request.files:
            return jsonify({"error": "no file uploaded"}), 400
        f = request.files["file"]
        # Basic filename safety
        uid = uuid.uuid4().hex
        pdf_filename = f"{uid}.pdf"
        pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
        f.save(pdf_path)

        # Extract text (consider page/size limits for production)
        text = extract_text(pdf_path)
        if not text.strip():
            return jsonify({"error": "no extractable text"}), 400

        # Convert to audio (limit to first N chars to avoid huge calls)
        chunk = text[:4000]

        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=chunk
        )

        mp3_name = f"{uid}.mp3"
        mp3_path = os.path.join(UPLOAD_DIR, mp3_name)
        with open(mp3_path, "wb") as out:
            out.write(response.read())

        # Return JSON with download URL
        download_url = f"/download/{mp3_name}"
        return jsonify({"download_url": download_url}), 200

    return render_template_string(HTML_PAGE)

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    # Bind to host and port that Render (or any host) expects
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

@app.route("/convert", methods=["POST"])
def convert():
    file = request.files.get("file")
    if not file:
        return "No file uploaded", 400

    file.save("uploaded.pdf")
    # Your PDF → MP3 conversion code here
    return "File converted!"  # For now, just a placeholder
