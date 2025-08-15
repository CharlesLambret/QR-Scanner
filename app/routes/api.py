from flask import Blueprint, request, jsonify, current_app
from ..services.scan_service import save_upload, scan_file, ScanOptions, cleanup_pdf_files

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

    # Parse new validation fields
    expected_domains_raw = request.form.get("expected_domains", "")
    expected_domains = [d.strip() for d in expected_domains_raw.split(",") if d.strip()] if expected_domains_raw else None
    
    expected_utm_params_raw = request.form.get("expected_utm_params", "")
    expected_utm_params = {}
    if expected_utm_params_raw:
        for param in expected_utm_params_raw.split(";"):
            if "=" in param:
                key, value = param.split("=", 1)
                expected_utm_params[key.strip()] = value.strip()
    expected_utm_params = expected_utm_params if expected_utm_params else None
    
    landing_page_texts_raw = request.form.get("landing_page_texts", "")
    landing_page_texts = [t.strip() for t in landing_page_texts_raw.split(";") if t.strip()] if landing_page_texts_raw else None
    
    unstructured_data_query = request.form.get("unstructured_data_query", "").strip() or None

    pdf_path, scan_id = save_upload(f)
    try:
        opts = ScanOptions(
            timeout=timeout, 
            search_texts=search_texts, 
            extract_text=extract_text,
            expected_domains=expected_domains,
            expected_utm_params=expected_utm_params,
            landing_page_texts=landing_page_texts,
            unstructured_data_query=unstructured_data_query
        )
        results = scan_file(pdf_path, opts, scan_id=scan_id)
        results["scan_id"] = scan_id
        return jsonify(results)
    except Exception as e:
        # En cas d'erreur, s'assurer que le fichier est supprimé
        cleanup_pdf_files(pdf_path, scan_id)
        return jsonify({"error": str(e)}), 500
