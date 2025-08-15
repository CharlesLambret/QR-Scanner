"""
Service de scan refactorisé
Orchestration de haut niveau pour le processus de scan
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
from ..scanner_core.scanner import QRCodePDFScanner
from .file_service import FileService


@dataclass
class ScanOptions:
    """Options de configuration pour un scan"""
    timeout: int
    search_texts: Optional[List[str]]
    expected_domains: Optional[List[str]] = None
    expected_utm_params: Optional[Dict[str, str]] = None
    ai_extraction_options: Optional[Dict[str, Any]] = None


def scan_file(pdf_path: str, options: ScanOptions, scan_id: str = None,
              progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """
    Lance le scan d'un fichier PDF avec les options spécifiées
    
    Args:
        pdf_path: Chemin vers le fichier PDF
        options: Options de scan
        scan_id: Identifiant du scan (pour les logs)
        progress_callback: Fonction de callback pour les mises à jour de progression
        
    Returns:
        Dict: Résultats du scan
        
    Raises:
        Exception: En cas d'erreur pendant le scan
    """
    print(f"🔧 SCAN_SERVICE: scan_file appelé avec pdf_path={pdf_path}, scan_id={scan_id}")
    print(f"🔧 SCAN_SERVICE: options={options}")
    print(f"🔧 SCAN_SERVICE: progress_callback présent={progress_callback is not None}")
    
    # Validation du fichier
    file_info = FileService.get_file_info(pdf_path)
    if not file_info["exists"]:
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    print(f"📄 SCAN_SERVICE: Fichier validé - {file_info['size_mb']}MB")
    
    # Fonction de progression avec logs
    def enhanced_progress_callback(message: str):
        print(f"📢 SCAN_SERVICE: Progression - {message}")
        if progress_callback:
            progress_callback(message)
    
    try:
        # Création et configuration du scanner
        print(f"🚀 SCAN_SERVICE: Création du scanner QRCodePDFScanner")
        scanner = QRCodePDFScanner(
            pdf_path=pdf_path,
            timeout=options.timeout,
            search_texts=options.search_texts,
            progress_callback=enhanced_progress_callback,
            expected_domains=options.expected_domains,
            expected_utm_params=options.expected_utm_params,
            ai_extraction_options=options.ai_extraction_options
        )
        
        # Exécution du scan
        print(f"🔍 SCAN_SERVICE: Début du scan PDF")
        enhanced_progress_callback("Initialisation du scan...")
        
        results = scanner.scan_pdf()
        
        # Enrichissement des résultats avec métadonnées
        results = _enrich_results(results, pdf_path, options, scan_id)
        
        print(f"✅ SCAN_SERVICE: Scan terminé avec succès")
        enhanced_progress_callback("Scan terminé avec succès")
        
        return results
        
    except Exception as e:
        error_msg = f"Erreur pendant le scan: {str(e)}"
        print(f"❌ SCAN_SERVICE: {error_msg}")
        enhanced_progress_callback(f"Erreur: {str(e)}")
        raise Exception(error_msg)
    
    finally:
        # Nettoyage automatique du fichier après le scan
        print(f"🧹 SCAN_SERVICE: Nettoyage du fichier PDF")
        FileService.cleanup_files(pdf_path, scan_id)


def _enrich_results(results: Dict[str, Any], pdf_path: str, 
                   options: ScanOptions, scan_id: Optional[str]) -> Dict[str, Any]:
    """
    Enrichit les résultats avec des métadonnées supplémentaires
    
    Args:
        results: Résultats de base du scan
        pdf_path: Chemin du fichier PDF
        options: Options de scan utilisées
        scan_id: Identifiant du scan
        
    Returns:
        Dict: Résultats enrichis
    """
    # Informations sur le fichier
    file_info = FileService.get_file_info(pdf_path)
    
    # Métadonnées du scan
    scan_metadata = {
        "scan_id": scan_id,
        "file_info": {
            "filename": file_info.get("filename"),
            "size_mb": file_info.get("size_mb"),
            "size_bytes": file_info.get("size")
        },
        "scan_options": {
            "timeout": options.timeout,
            "search_texts_count": len(options.search_texts) if options.search_texts else 0,
            "has_domain_validation": bool(options.expected_domains),
            "has_utm_validation": bool(options.expected_utm_params),
            "has_ai_extraction": bool(options.ai_extraction_options)
        },
        "processing_info": {
            "scanner_version": "2.0.0-refactored",
            "modules_used": _get_modules_used(options)
        }
    }
    
    # Ajout des métadonnées aux résultats
    enriched_results = {
        **results,
        "metadata": scan_metadata,
        "success": True,
        "message": "Scan completed successfully"
    }
    
    # Calcul de scores de qualité
    quality_scores = _calculate_quality_scores(results)
    enriched_results["quality_scores"] = quality_scores
    
    return enriched_results


def _get_modules_used(options: ScanOptions) -> List[str]:
    """
    Détermine quels modules ont été utilisés
    
    Args:
        options: Options de scan
        
    Returns:
        List[str]: Liste des modules utilisés
    """
    modules = ["qr_detector", "http_validator"]
    
    if options.ai_extraction_options:
        modules.append("ai_extractor")

    if options.expected_domains or options.expected_utm_params:
        modules.append("advanced_validation")
    
    return modules


def _calculate_quality_scores(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule des scores de qualité pour les résultats
    
    Args:
        results: Résultats du scan
        
    Returns:
        Dict: Scores de qualité
    """
    stats = results.get("stats", {})
    url_results = results.get("url_results", [])
    validation_summary = results.get("validation_summary", {})
    
    # Score de détection QR (basé sur le ratio pages avec QR / total pages)
    qr_detection_score = 0
    if stats.get("total_pages", 0) > 0:
        qr_detection_score = round(
            (stats.get("pages_with_qr", 0) / stats.get("total_pages", 1)) * 100, 1
        )
    
    # Score de validation HTTP (basé sur les succès HTTP)
    http_validation_score = 0
    if validation_summary and validation_summary.get("total", 0) > 0:
        http_validation_score = round(
            (validation_summary.get("http_success", 0) / validation_summary.get("total", 1)) * 100, 1
        )
    
    # Score de validation avancée (domaines, UTM, textes)
    advanced_validation_score = None
    if validation_summary and validation_summary.get("total", 0) > 0:
        valid_count = (
            validation_summary.get("domain_valid", 0) +
            validation_summary.get("utm_valid", 0) +
            validation_summary.get("text_valid", 0)
        )
        total_validations = (
            validation_summary.get("domain_valid", 0) + validation_summary.get("domain_invalid", 0) +
            validation_summary.get("utm_valid", 0) + validation_summary.get("utm_invalid", 0) +
            validation_summary.get("text_valid", 0) + validation_summary.get("text_invalid", 0)
        )
        
        if total_validations > 0:
            advanced_validation_score = round((valid_count / total_validations) * 100, 1)
    
    # Score d'extraction IA
    ai_extraction_score = None
    ai_extraction = results.get("ai_extraction")
    if ai_extraction and ai_extraction.get("success"):
        extraction_count = len(ai_extraction.get("extracted_data", []))
        if extraction_count > 0:
            # Score basé sur le nombre d'extractions (plus il y en a, mieux c'est)
            ai_extraction_score = min(100, extraction_count * 10)  # 10 points par extraction, max 100
    
    # Score global
    scores_to_average = [score for score in [
        qr_detection_score, 
        http_validation_score, 
        advanced_validation_score,
        ai_extraction_score
    ] if score is not None]
    
    overall_score = round(sum(scores_to_average) / len(scores_to_average), 1) if scores_to_average else 0
    
    return {
        "qr_detection": qr_detection_score,
        "http_validation": http_validation_score,
        "advanced_validation": advanced_validation_score,
        "ai_extraction": ai_extraction_score,
        "overall": overall_score,
        "details": {
            "total_qr_codes": stats.get("unique_urls", 0),
            "successful_http_requests": validation_summary.get("http_success", 0) if validation_summary else 0,
            "avg_response_time_ms": validation_summary.get("avg_response_time", 0) if validation_summary else 0,
            "ai_extractions_count": stats.get("ai_extracted_items", 0),
            "text_lines_extracted": stats.get("extracted_lines", 0)
        }
    }


def create_scan_report(results: Dict[str, Any]) -> str:
    """
    Crée un rapport textuel des résultats de scan
    
    Args:
        results: Résultats du scan
        
    Returns:
        str: Rapport formaté
    """
    stats = results.get("stats", {})
    metadata = results.get("metadata", {})
    quality_scores = results.get("quality_scores", {})
    
    report_lines = [
        "=== RAPPORT DE SCAN QR PDF ===",
        "",
        f"📄 Fichier: {metadata.get('file_info', {}).get('filename', 'Inconnu')}",
        f"📊 Taille: {metadata.get('file_info', {}).get('size_mb', 0)} MB",
        f"🆔 Scan ID: {metadata.get('scan_id', 'N/A')}",
        "",
        "=== STATISTIQUES ===",
        f"• Pages totales: {stats.get('total_pages', 0)}",
        f"• Pages avec QR codes: {stats.get('pages_with_qr', 0)}",
        f"• URLs uniques trouvées: {stats.get('unique_urls', 0)}",
        f"• Lignes de texte extraites: {stats.get('extracted_lines', 0)}",
        f"• Extractions IA: {stats.get('ai_extracted_items', 0)}",
        "",
        "=== SCORES DE QUALITÉ ===",
        f"• Détection QR: {quality_scores.get('qr_detection', 0)}%",
        f"• Validation HTTP: {quality_scores.get('http_validation', 0)}%",
    ]
    
    if quality_scores.get('advanced_validation') is not None:
        report_lines.append(f"• Validation avancée: {quality_scores.get('advanced_validation')}%")
    
    if quality_scores.get('ai_extraction') is not None:
        report_lines.append(f"• Extraction IA: {quality_scores.get('ai_extraction')}%")
    
    report_lines.extend([
        f"• Score global: {quality_scores.get('overall', 0)}%",
        "",
        "=== MODULES UTILISÉS ===",
        f"• {', '.join(metadata.get('processing_info', {}).get('modules_used', []))}",
        "",
        f"✅ Scan terminé avec succès"
    ])
    
    return "\n".join(report_lines)


# Fonctions utilitaires pour la compatibilité
def save_upload(file_storage):
    """
    Fonction de compatibilité - utilise FileService
    
    Args:
        file_storage: Fichier uploadé
        
    Returns:
        tuple: (chemin_fichier, scan_id)
    """
    return FileService.save_upload(file_storage)


def cleanup_pdf_files(pdf_path: str, scan_id: str = None):
    """
    Fonction de compatibilité - utilise FileService
    
    Args:
        pdf_path: Chemin du fichier PDF
        scan_id: ID du scan
    """
    FileService.cleanup_files(pdf_path, scan_id)