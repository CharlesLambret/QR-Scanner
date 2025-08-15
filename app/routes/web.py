"""
Routes web refactorisées
Gestion simplifiée des routes web utilisant les services modulaires
"""
import uuid
from flask import Blueprint, render_template, request
from ..services.file_service import FileService
from ..services.websocket_service import WebSocketService
from ..services.scan_service import ScanOptions

bp = Blueprint("web", __name__)


@bp.get("/")
def index():
    """Page d'accueil avec formulaire de scan"""
    return render_template("index.html")


@bp.post("/scan")
def scan():
    """
    Endpoint de scan web avec WebSocket
    Démarre le processus de scan en arrière-plan
    """
    print(f"🌐 WEB: Requête POST /scan reçue")
    
    # Validation du fichier
    uploaded_file = request.files.get("pdf")
    if not uploaded_file:
        print(f"❌ WEB: Aucun fichier fourni")
        return render_template("index.html", error="Aucun fichier fourni")

    try:
        # Sauvegarde du fichier
        scan_id = str(uuid.uuid4())
        print(f"🆔 WEB: scan_id généré: {scan_id}")
        
        pdf_path, _ = FileService.save_upload(uploaded_file)
        print(f"💾 WEB: Fichier sauvé: {pdf_path}")

        # Extraction des options du formulaire
        scan_options = _extract_scan_options_from_form(request.form)
        print(f"⚙️ WEB: Options extraites: {scan_options}")

        # Création du callback de progression WebSocket
        progress_callback = WebSocketService.create_progress_callback(scan_id)

        # Préparation des données de scan
        scan_data = {
            'pdf_path': pdf_path,
            'options': scan_options,
            'scan_id': scan_id,
            'progress_callback': progress_callback
        }

        # Enregistrement du scan pour traitement différé
        WebSocketService.register_scan(scan_id, scan_data)
        print(f"📦 WEB: Données de scan enregistrées pour scan_id={scan_id}")

        # Redirection vers la page de résultats
        print(f"🎭 WEB: Rendu template results.html avec scan_id={scan_id}")
        return render_template("results.html", scan_id=scan_id)

    except Exception as e:
        print(f"❌ WEB: Erreur lors du traitement: {e}")
        return render_template("index.html", error=f"Erreur lors du traitement: {str(e)}")


def _extract_scan_options_from_form(form_data) -> ScanOptions:
    """
    Extrait les options de scan depuis les données du formulaire
    
    Args:
        form_data: Données du formulaire Flask
        
    Returns:
        ScanOptions: Options de scan configurées
    """
    # Options de base
    timeout = int(form_data.get("timeout", 10))
    
    # Textes de recherche
    search_texts_raw = form_data.get("search_texts", "")
    search_texts = [s.strip() for s in search_texts_raw.split(";") if s.strip()] or None
    
    # Validation avancée des URLs
    expected_domains = _parse_domains(form_data.get("expected_domains", ""))
    expected_utm_params = _parse_utm_params(form_data.get("expected_utm_params", ""))
    
    # Extraction IA - Keywords et options
    extraction_keywords = form_data.getlist("extraction_keywords")  # Liste des mots-clés cochés
    search_code_length = int(form_data.get("search_code_length", 5))
    result_code_length = int(form_data.get("result_code_length", 4))
    
    # Construire les options d'extraction IA
    ai_extraction_options = None
    if extraction_keywords:
        ai_extraction_options = {
            'keywords': extraction_keywords,
            'search_code_length': search_code_length,
            'result_code_length': result_code_length
        }
    
    # Log des options extraites
    print(f"⚙️ WEB: Options de base - timeout: {timeout}")
    print(f"⚙️ WEB: Recherche - textes: {search_texts}")
    print(f"⚙️ WEB: Validation - domaines: {expected_domains}")
    print(f"⚙️ WEB: Validation - UTM: {expected_utm_params}")
    print(f"⚙️ WEB: IA - keywords: {extraction_keywords}")
    print(f"⚙️ WEB: IA - longueurs code: {search_code_length}→{result_code_length}")

    return ScanOptions(
        timeout=timeout,
        search_texts=search_texts,
        expected_domains=expected_domains,
        expected_utm_params=expected_utm_params,
        ai_extraction_options=ai_extraction_options
    )


def _parse_domains(domains_str: str) -> list:
    """Parse la chaîne de domaines attendus"""
    if not domains_str:
        return None
    return [d.strip() for d in domains_str.split(",") if d.strip()]


def _parse_utm_params(utm_str: str) -> dict:
    """Parse la chaîne de paramètres UTM attendus"""
    if not utm_str:
        return None
    
    params = {}
    for param in utm_str.split(";"):
        if "=" in param:
            key, value = param.split("=", 1)
            params[key.strip()] = value.strip()
    
    return params if params else None



@bp.errorhandler(413)
def file_too_large(error):
    """Gestionnaire d'erreur pour les fichiers trop volumineux"""
    return render_template("index.html", 
                         error="Fichier trop volumineux. Taille maximale autorisée: 50MB"), 413


@bp.errorhandler(Exception)
def handle_error(error):
    """Gestionnaire d'erreur général pour les routes web"""
    print(f"❌ WEB: Erreur non gérée: {error}")
    return render_template("index.html", 
                         error="Une erreur inattendue s'est produite"), 500