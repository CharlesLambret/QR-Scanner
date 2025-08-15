"""
Routes API refactorisées
API REST pour le scan de PDF avec gestion d'erreurs améliorée
"""
from flask import Blueprint, request, jsonify, current_app
from ..services.file_service import FileService
from ..services.scan_service import scan_file, ScanOptions

bp = Blueprint("api", __name__)


@bp.post("/scan")
def api_scan():
    """
    Endpoint API pour scanner un PDF
    Traitement synchrone avec retour JSON
    """
    try:
        # Validation du fichier
        uploaded_file = request.files.get("file") or request.files.get("pdf")
        if not uploaded_file:
            return _error_response("file is required", 400)

        # Extraction des paramètres
        scan_params = _extract_api_parameters(request.form)
        
        # Sauvegarde du fichier
        pdf_path, scan_id = FileService.save_upload(uploaded_file)
        
        # Configuration des options de scan
        scan_options = ScanOptions(**scan_params)
        
        # Exécution du scan
        results = scan_file(pdf_path, scan_options, scan_id=scan_id)
        
        # Ajout de l'ID de scan aux résultats
        results["scan_id"] = scan_id
        
        return jsonify(results)

    except Exception as e:
        # En cas d'erreur, nettoyer les fichiers créés
        if 'pdf_path' in locals() and 'scan_id' in locals():
            FileService.cleanup_files(pdf_path, scan_id)
        
        return _error_response(str(e), 500)


@bp.get("/health")
def health_check():
    """Endpoint de vérification de santé de l'API"""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "file_service": "ok",
            "scan_service": "ok",
            "ai_extraction": "ok" if _check_ai_service() else "unavailable"
        }
    })


@bp.get("/info")
def api_info():
    """Informations sur l'API"""
    return jsonify({
        "name": "QR PDF Scanner API",
        "version": "1.0.0",
        "description": "API pour scanner les QR codes dans les PDF avec validation et extraction IA",
        "endpoints": {
            "POST /api/scan": "Scanner un PDF",
            "GET /api/health": "Vérification de santé",
            "GET /api/info": "Informations sur l'API"
        },
        "supported_formats": ["PDF"],
        "max_file_size": "50MB",
        "features": [
            "QR code detection",
            "HTTP validation",
            "UTM parameter validation",
            "Domain validation",
            "Landing page text search",
            "AI data extraction",
            "Text extraction"
        ]
    })


def _extract_api_parameters(form_data) -> dict:
    """
    Extrait et valide les paramètres de l'API
    
    Args:
        form_data: Données du formulaire
        
    Returns:
        dict: Paramètres validés pour ScanOptions
    """
    # Paramètres de base
    timeout = int(form_data.get("timeout", current_app.config["TIMEOUT_DEFAULT"]))
    extract_text = form_data.get("extract_text", "false").lower() in ("1", "true", "yes", "on")
    
    # Validation des paramètres
    if timeout < 1 or timeout > 60:
        raise ValueError("timeout must be between 1 and 60 seconds")
    
    # Textes de recherche
    search_texts_raw = form_data.get("search_texts")
    search_texts = [s.strip() for s in (search_texts_raw or "").split(";") if s.strip()] or None
    
    # Validation avancée
    expected_domains = _parse_api_domains(form_data.get("expected_domains", ""))
    expected_utm_params = _parse_api_utm_params(form_data.get("expected_utm_params", ""))
    
    # Extraction IA
    unstructured_data_query = form_data.get("unstructured_data_query", "").strip() or None
    
    return {
        "timeout": timeout,
        "search_texts": search_texts,
        "extract_text": extract_text,
        "expected_domains": expected_domains,
        "expected_utm_params": expected_utm_params,
        "unstructured_data_query": unstructured_data_query
    }


def _parse_api_domains(domains_str: str) -> list:
    """Parse et valide les domaines pour l'API"""
    if not domains_str:
        return None
    
    domains = [d.strip() for d in domains_str.split(",") if d.strip()]
    
    # Validation basique des domaines
    for domain in domains:
        if not _is_valid_domain_format(domain):
            raise ValueError(f"Invalid domain format: {domain}")
    
    return domains if domains else None


def _parse_api_utm_params(utm_str: str) -> dict:
    """Parse et valide les paramètres UTM pour l'API"""
    if not utm_str:
        return None
    
    params = {}
    for param in utm_str.split(";"):
        if "=" not in param:
            raise ValueError(f"Invalid UTM parameter format: {param}. Use key=value")
        
        key, value = param.split("=", 1)
        key = key.strip()
        value = value.strip()
        
        if not key or not value:
            raise ValueError(f"Empty UTM parameter key or value: {param}")
        
        params[key] = value
    
    return params if params else None



def _is_valid_domain_format(domain: str) -> bool:
    """Valide le format d'un domaine"""
    import re
    domain_regex = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])*$'
    return re.match(domain_regex, domain) is not None


def _check_ai_service() -> bool:
    """Vérifie si le service IA est disponible"""
    try:
        from ..services.ai_extraction import AIDataExtractor
        extractor = AIDataExtractor()
        return extractor.enabled
    except:
        return False


def _error_response(message: str, status_code: int) -> tuple:
    """
    Crée une réponse d'erreur standardisée
    
    Args:
        message: Message d'erreur
        status_code: Code de statut HTTP
        
    Returns:
        tuple: (response_json, status_code)
    """
    return jsonify({
        "error": message,
        "status": "error",
        "code": status_code
    }), status_code


# Gestionnaires d'erreurs pour l'API
@bp.errorhandler(400)
def bad_request(error):
    """Gestionnaire pour les requêtes malformées"""
    return _error_response("Bad request", 400)


@bp.errorhandler(413)
def file_too_large(error):
    """Gestionnaire pour les fichiers trop volumineux"""
    return _error_response("File too large. Maximum size: 50MB", 413)


@bp.errorhandler(415)
def unsupported_media_type(error):
    """Gestionnaire pour les types de fichiers non supportés"""
    return _error_response("Unsupported file type. Only PDF files are allowed", 415)


@bp.errorhandler(Exception)
def handle_api_error(error):
    """Gestionnaire d'erreur général pour l'API"""
    print(f"❌ API: Erreur non gérée: {error}")
    return _error_response("Internal server error", 500)