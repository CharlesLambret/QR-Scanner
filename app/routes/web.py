from flask import Blueprint, render_template, request
from flask_socketio import emit
from ..services.scan_service import save_upload, scan_file, ScanOptions, cleanup_pdf_files
from .. import socketio
import uuid

bp = Blueprint("web", __name__)

@socketio.on('client_ready')
def handle_client_ready(data):
    scan_id = data.get('scan_id')
    print(f"🎯 SOCKET: Client prêt pour scan_id={scan_id}")
    
    if hasattr(socketio, 'pending_scans') and scan_id in socketio.pending_scans:
        scan_data = socketio.pending_scans[scan_id]
        print(f"🚀 SOCKET: Démarrage du scan pour scan_id={scan_id}")
        
        def start_scan():
            try:
                results = scan_file(
                    scan_data['pdf_path'], 
                    scan_data['options'], 
                    scan_id=scan_id, 
                    progress_callback=scan_data['ws_progress']
                )
                print(f"✅ SOCKET: scan_file terminé pour scan_id={scan_id}")
                
                socketio.emit("scan_complete", {"scan_id": scan_id, "results": results})
                print(f"📢 SOCKET: scan_complete envoyé pour scan_id={scan_id}")
                
                # Nettoyer les données temporaires
                del socketio.pending_scans[scan_id]
            except Exception as e:
                print(f"❌ SOCKET: Erreur pendant le scan {scan_id}: {e}")
                # En cas d'erreur, s'assurer que le fichier PDF est supprimé
                cleanup_pdf_files(scan_data['pdf_path'], scan_id)
                socketio.emit("scan_error", {"scan_id": scan_id, "error": str(e)})
        
        socketio.start_background_task(start_scan)
    else:
        print(f"❌ SOCKET: Aucune donnée de scan trouvée pour scan_id={scan_id}")

@socketio.on('test_message')
def handle_test_message(data):
    print(f"🧪 SOCKET: Message de test reçu: {data}")
    emit('test_response', {'message': 'Test reçu par le serveur'})

@bp.get("/")
def index():
    return render_template("index.html")

@bp.post("/scan")
def scan():
    print(f"🌐 WEB: Requête POST /scan reçue")
    
    f = request.files.get("pdf")
    if not f:
        print(f"❌ WEB: Aucun fichier fourni")
        return render_template("index.html", error="Aucun fichier fourni")

    scan_id = str(uuid.uuid4())
    print(f"🆔 WEB: scan_id généré: {scan_id}")
    
    pdf_path, _ = save_upload(f)  # Unpack the tuple to get just the path
    print(f"💾 WEB: Fichier sauvé: {pdf_path}")

    timeout = int(request.form.get("timeout", 10))
    extract_text = request.form.get("extract_text") == "on"
    search_texts = request.form.get("search_texts", "").split(";") or None
    
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
    
    print(f"⚙️ WEB: Options - timeout: {timeout}, extract_text: {extract_text}")
    print(f"⚙️ WEB: Validation - domains: {expected_domains}, utm: {expected_utm_params}, texts: {landing_page_texts}")
    print(f"⚙️ WEB: AI Extraction - query: {unstructured_data_query}")

    options = ScanOptions(
        timeout=timeout, 
        search_texts=search_texts, 
        extract_text=extract_text,
        expected_domains=expected_domains,
        expected_utm_params=expected_utm_params,
        landing_page_texts=landing_page_texts,
        unstructured_data_query=unstructured_data_query
    )

    def ws_progress(msg):
        print(f"📢 WEB: Envoi WebSocket scan_progress: scan_id={scan_id}, message='{msg}'")
        socketio.emit("scan_progress", {"scan_id": scan_id, "message": msg})

    print(f"🎭 WEB: Rendu template results.html avec scan_id={scan_id}")
    
    # Stocker les informations du scan pour le traitement différé
    scan_data = {
        'pdf_path': pdf_path,
        'options': options,
        'scan_id': scan_id,
        'ws_progress': ws_progress
    }
    
    # Stocker temporairement les données de scan (vous pourriez utiliser Redis en production)
    if not hasattr(socketio, 'pending_scans'):
        socketio.pending_scans = {}
    socketio.pending_scans[scan_id] = scan_data
    
    print(f"📦 WEB: Données de scan stockées pour scan_id={scan_id}")
    
    return render_template("results.html", scan_id=scan_id)
