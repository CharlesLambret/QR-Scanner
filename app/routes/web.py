from flask import Blueprint, render_template, request
from flask_socketio import emit
from ..services.scan_service import save_upload, scan_file, ScanOptions
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
    print(f"⚙️ WEB: Options - timeout: {timeout}, extract_text: {extract_text}")

    options = ScanOptions(timeout=timeout, search_texts=search_texts, extract_text=extract_text)

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
