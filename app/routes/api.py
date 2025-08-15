from flask import Blueprint, request, jsonify, current_app
from ..services.scan_service import save_upload, scan_file, ScanOptions

bp = Blueprint("api", __name__)

@bp.post("/scan")
def api_scan():
    f = request.files.get("file") or request.files.get("pdf")
    if not f:
        return jsonify({"error": "file is required"}), 400

    timeout = int(request.form.get("timeout", current_app.config["TIMEOUT_DEFAULT"]))
    extract_text = request.form.get("extract_text", "false").lower() in ("1","true","yes","on")
    search_texts_raw = request.form.get("search_texts")
    search_texts = [s.strip() for s in (search_texts_raw or "").split(";") if s.strip()] or None

    pdf_path, scan_id = save_upload(f)
    opts = ScanOptions(timeout=timeout, search_texts=search_texts, extract_text=extract_text)
    results = scan_file(pdf_path, opts, scan_id=scan_id)
    results["scan_id"] = scan_id
    return jsonify(results)
