import os
import uuid
import shutil
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from flask import current_app
from ..scanner_core.scanner import QRCodePDFScanner

@dataclass
class ScanOptions:
    timeout: int
    search_texts: Optional[List[str]]
    extract_text: bool
    expected_domains: Optional[List[str]] = None
    expected_utm_params: Optional[Dict[str, str]] = None
    landing_page_texts: Optional[List[str]] = None

def save_upload(file_storage) -> (str, str):
    # Validation simple
    filename = file_storage.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        from werkzeug.exceptions import UnsupportedMediaType
        raise UnsupportedMediaType("Only PDF is allowed")

    scan_id = str(uuid.uuid4())
    out_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], scan_id)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "document.pdf")
    file_storage.save(out_path)
    return out_path, scan_id

def cleanup_pdf_files(pdf_path: str, scan_id: str = None):
    """
    Supprime le fichier PDF et son dossier après traitement
    """
    try:
        if os.path.exists(pdf_path):
            # Supprimer le fichier PDF
            os.remove(pdf_path)
            print(f"🗑️ SERVICE: Fichier PDF supprimé: {pdf_path}")
            
            # Supprimer le dossier si vide (contient normalement scan_id)
            pdf_dir = os.path.dirname(pdf_path)
            if scan_id and scan_id in pdf_dir:
                try:
                    os.rmdir(pdf_dir)
                    print(f"🗑️ SERVICE: Dossier scan supprimé: {pdf_dir}")
                except OSError as e:
                    # Dossier non vide, on ne peut pas le supprimer
                    print(f"⚠️ SERVICE: Impossible de supprimer le dossier {pdf_dir}: {e}")
        else:
            print(f"⚠️ SERVICE: Fichier PDF non trouvé pour suppression: {pdf_path}")
    except Exception as e:
        print(f"❌ SERVICE: Erreur lors de la suppression du PDF {pdf_path}: {e}")

def scan_file(pdf_path: str, options: ScanOptions, scan_id: str = None,
              progress_callback: callable = None) -> Dict[str, Any]:
    
    print(f"🔧 SERVICE: scan_file appelé avec pdf_path={pdf_path}, scan_id={scan_id}")
    print(f"🔧 SERVICE: options={options}")
    print(f"🔧 SERVICE: progress_callback présent={progress_callback is not None}")
    
    def log_progress(message):
        print(f"📢 SERVICE: log_progress appelé avec message='{message}'")
        if progress_callback:
            print(f"📢 SERVICE: Appel progress_callback avec message='{message}'")
            progress_callback(message)
        else:
            print(f"❌ SERVICE: progress_callback est None, impossible d'envoyer le message")

    try:
        print(f"🚀 SERVICE: Création du scanner QRCodePDFScanner")
        scanner = QRCodePDFScanner(
            pdf_path=pdf_path,
            timeout=options.timeout,
            search_texts=options.search_texts,
            extract_text=options.extract_text,
            progress_callback=log_progress,
            expected_domains=options.expected_domains,
            expected_utm_params=options.expected_utm_params,
            landing_page_texts=options.landing_page_texts
        )
        
        print(f"🔍 SERVICE: Début du scan PDF")
        results = scanner.scan_pdf()
        print(f"✅ SERVICE: Scan terminé, résultats={results}")
        
        return results
    finally:
        # Toujours nettoyer le fichier PDF après le scan, même en cas d'erreur
        print(f"🧹 SERVICE: Nettoyage du fichier PDF")
        cleanup_pdf_files(pdf_path, scan_id)
