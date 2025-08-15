"""
Scanner principal refactorisé
Orchestration des modules spécialisés pour scanner un PDF
"""
import os
import fitz  # PyMuPDF
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from .models import PDFTask
from .qr_detector import QRDetector
from .http_validator import HTTPValidator
from .text_extractor import TextExtractor
from ..services.ai_extraction import AIDataExtractor


@dataclass
class LoggerShim:
    """Logger simple pour compatibilité"""
    level: str = "INFO"
    
    def log(self, level: str, msg: str):
        wanted = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if wanted.index(level) >= wanted.index(self.level):
            print(f"{level} - {msg}")


class QRCodePDFScanner:
    """
    Scanner PDF refactorisé utilisant des modules spécialisés
    """
    
    def __init__(
        self,
        pdf_path: str,
        timeout: int = 10,
        search_texts: Optional[List[str]] = None,
        extract_text: bool = False,
        out_dir: Optional[str] = None,
        log_level: str = "INFO",
        progress_callback: Optional[Callable[[str], None]] = None,
        expected_domains: Optional[List[str]] = None,
        expected_utm_params: Optional[Dict[str, str]] = None,
        landing_page_texts: Optional[List[str]] = None,
        unstructured_data_query: Optional[str] = None
    ):
        print(f"🏗️ SCANNER: __init__ appelé avec pdf_path={pdf_path}")
        print(f"🏗️ SCANNER: progress_callback présent={progress_callback is not None}")
        
        # Configuration de base
        self.task = PDFTask(
            pdf_path=pdf_path, 
            timeout=timeout, 
            search_texts=search_texts, 
            extract_text=extract_text
        )
        self.out_dir = out_dir or os.path.dirname(pdf_path)
        self.logger = LoggerShim(level=log_level)
        self.progress_callback = progress_callback or (lambda msg: None)
        
        # Initialisation des modules spécialisés
        self._init_modules(
            expected_domains, expected_utm_params, 
            landing_page_texts, unstructured_data_query
        )
        
        print(f"🏗️ SCANNER: Scanner refactorisé initialisé avec succès")
    
    def _init_modules(self, expected_domains, expected_utm_params, 
                     landing_page_texts, unstructured_data_query):
        """Initialise tous les modules spécialisés"""
        
        # Détecteur QR
        self.qr_detector = QRDetector(log_callback=self.safe_log)
        
        # Validateur HTTP
        self.http_validator = HTTPValidator(
            timeout=self.task.timeout,
            expected_domains=expected_domains,
            expected_utm_params=expected_utm_params,
            landing_page_texts=landing_page_texts,
            log_callback=self.safe_log
        )
        
        # Extracteur de texte
        self.text_extractor = TextExtractor(
            extract_odd_pages_only=True,
            log_callback=self.safe_log
        )
        
        # Extracteur IA (si demandé)
        self.ai_extractor = None
        self.unstructured_data_query = unstructured_data_query
        if unstructured_data_query:
            self.ai_extractor = AIDataExtractor()
    
    def safe_log(self, level: str, msg: str):
        """Log sécurisé"""
        try:
            self.logger.log(level, msg)
        except Exception:
            pass
    
    def scan_pdf(self) -> Dict[str, Any]:
        """
        Lance le scan complet du PDF
        
        Returns:
            Dict: Résultats du scan
        """
        print(f"📖 SCANNER: scan_pdf démarré")
        
        pdf_path = self.task.pdf_path
        print(f"📖 SCANNER: Ouverture du PDF {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise Exception(f"Impossible d'ouvrir le PDF: {e}")
        
        try:
            return self._process_document(doc)
        finally:
            doc.close()
            print(f"📖 SCANNER: Document fermé")
    
    def _process_document(self, doc: fitz.Document) -> Dict[str, Any]:
        """
        Traite le document PDF page par page
        
        Args:
            doc: Document PyMuPDF ouvert
            
        Returns:
            Dict: Résultats consolidés
        """
        total_pages = len(doc)
        print(f"📢 SCANNER: Envoi du message de progression initial")
        self.progress_callback(f"Lecture du PDF : {total_pages} pages")
        
        # Structures de données pour collecter les résultats
        all_url_results = []
        all_text_extractions = []
        all_ai_extractions = []
        pages_with_qr = 0
        
        # Traitement CSV si extraction de texte demandée
        csv_writer_info = self._setup_csv_export() if self.task.extract_text else None
        
        try:
            # Traitement page par page
            for page_num in range(total_pages):
                current_page = page_num + 1
                print(f"📄 SCANNER: Traitement page {current_page}/{total_pages}")
                self.progress_callback(f"Lecture page {current_page}/{total_pages}")
                
                page = doc[page_num]
                page_results = self._process_page(page, current_page, csv_writer_info)
                
                # Consolidation des résultats
                if page_results["qr_results"]:
                    all_url_results.extend(page_results["qr_results"])
                    pages_with_qr += 1
                
                if page_results["text_extractions"]:
                    all_text_extractions.extend(page_results["text_extractions"])
                
                if page_results["ai_extractions"]:
                    all_ai_extractions.extend(page_results["ai_extractions"])
                
                self.progress_callback(f"Page {current_page} scannée")
            
            # Finalisation et déduplication
            return self._finalize_results(
                total_pages, pages_with_qr, all_url_results, 
                all_text_extractions, all_ai_extractions, csv_writer_info
            )
            
        finally:
            if csv_writer_info and csv_writer_info["file_handle"]:
                csv_writer_info["file_handle"].close()
    
    def _process_page(self, page: fitz.Page, page_number: int, 
                     csv_writer_info: Optional[dict]) -> Dict[str, List]:
        """
        Traite une page individuelle
        
        Args:
            page: Page PyMuPDF
            page_number: Numéro de la page
            csv_writer_info: Informations pour l'export CSV
            
        Returns:
            Dict: Résultats de la page
        """
        results = {
            "qr_results": [],
            "text_extractions": [],
            "ai_extractions": []
        }
        
        # 1. Détection QR codes
        print(f"🔍 SCANNER: Détection QR codes page {page_number}")
        qr_results = self._process_qr_codes(page, page_number)
        results["qr_results"] = qr_results
        
        # 2. Extraction de texte (pages impaires seulement si activé)
        if self.task.extract_text:
            print(f"📝 SCANNER: Extraction texte page {page_number}")
            text_extractions = self.text_extractor.extract_from_page(page, page_number)
            results["text_extractions"] = text_extractions
            
            # Écriture CSV si configuré
            if csv_writer_info and text_extractions:
                for extraction in text_extractions:
                    csv_writer_info["writer"].writerow([
                        extraction["page"], 
                        extraction["line"]
                    ])
        
        # 3. Extraction IA (si configurée)
        if self.ai_extractor and self.unstructured_data_query:
            print(f"🤖 SCANNER: Extraction IA pour page {page_number}")
            ai_extractions = self._process_ai_extraction(page, page_number)
            results["ai_extractions"] = ai_extractions
        
        return results
    
    def _process_qr_codes(self, page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        """
        Traite les QR codes d'une page
        
        Args:
            page: Page PyMuPDF
            page_number: Numéro de la page
            
        Returns:
            List[Dict]: Résultats des QR codes avec validation HTTP
        """
        # Conversion de la page en image
        print(f"🖼️ SCANNER: Conversion page {page_number} en image")
        image = self._page_to_image(page, zoom=2.0)
        
        # Détection des QR codes
        qr_values = self.qr_detector.detect_qr_codes(image)
        print(f"🔍 SCANNER: QR codes trouvés page {page_number}: {qr_values}")
        
        page_results = []
        
        # Validation HTTP pour chaque URL trouvée
        for qr_value in qr_values:
            print(f"🔗 SCANNER: Analyse QR: {qr_value}")
            if qr_value.startswith(("http://", "https://")):
                print(f"🌐 SCANNER: Validation HTTP pour URL: {qr_value}")
                validation_result = self.http_validator.validate_url(qr_value)
                validation_result["page"] = page_number
                page_results.append(validation_result)
                print(f"🌐 SCANNER: Résultat validation: {validation_result}")
        
        return page_results
    
    def _process_ai_extraction(self, page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        """
        Traite l'extraction IA d'une page
        
        Args:
            page: Page PyMuPDF
            page_number: Numéro de la page
            
        Returns:
            List[Dict]: Extractions IA avec métadonnées de page
        """
        page_text = page.get_text("text")
        if not page_text.strip():
            return []
        
        ai_result = self.ai_extractor.extract_data(page_text, self.unstructured_data_query)
        
        if not (ai_result and ai_result.get('success') and ai_result.get('extracted_data')):
            return []
        
        # Ajouter le numéro de page à chaque extraction
        page_extractions = []
        for extraction in ai_result['extracted_data']:
            extraction['page'] = page_number
            if not extraction.get('attributes'):
                extraction['attributes'] = {}
            extraction['attributes']['page'] = page_number
            page_extractions.append(extraction)
        
        print(f"🤖 SCANNER: {len(page_extractions)} extractions IA trouvées page {page_number}")
        return page_extractions
    
    def _page_to_image(self, page: fitz.Page, zoom: float = 2.0) -> np.ndarray:
        """
        Convertit une page PDF en image numpy
        
        Args:
            page: Page PyMuPDF
            zoom: Facteur de zoom
            
        Returns:
            np.ndarray: Image au format BGR
        """
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        if pix.n != 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)

        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
        return img
    
    def _setup_csv_export(self) -> Optional[Dict[str, Any]]:
        """
        Configure l'export CSV pour les extractions de texte
        
        Returns:
            Optional[Dict]: Informations pour l'export CSV
        """
        try:
            import csv
            
            csv_filename = "extractions.csv"
            csv_path = os.path.join(self.out_dir, csv_filename)
            csv_file = open(csv_path, "w", newline="", encoding="utf-8")
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["page", "line"])
            
            return {
                "filename": csv_filename,
                "path": csv_path,
                "file_handle": csv_file,
                "writer": csv_writer
            }
            
        except Exception as e:
            self.safe_log("ERROR", f"Erreur configuration CSV: {e}")
            return None
    
    def _finalize_results(self, total_pages: int, pages_with_qr: int,
                         all_url_results: List[Dict], all_text_extractions: List[Dict],
                         all_ai_extractions: List[Dict], csv_writer_info: Optional[Dict]) -> Dict[str, Any]:
        """
        Finalise et consolide tous les résultats
        
        Args:
            total_pages: Nombre total de pages
            pages_with_qr: Nombre de pages avec QR codes
            all_url_results: Tous les résultats d'URLs
            all_text_extractions: Toutes les extractions de texte
            all_ai_extractions: Toutes les extractions IA
            csv_writer_info: Informations CSV
            
        Returns:
            Dict: Résultats consolidés finaux
        """
        print(f"🔗 SCANNER: Déduplication des URLs")
        
        # Déduplication des URLs par (url, page)
        seen_urls = set()
        unique_url_results = []
        for result in all_url_results:
            key = (result["url"], result["page"])
            if key not in seen_urls:
                unique_url_results.append(result)
                seen_urls.add(key)
        
        # Préparer les résultats d'extraction IA
        ai_extraction_results = None
        if all_ai_extractions:
            ai_extraction_results = {
                "success": True,
                "extracted_data": all_ai_extractions,
                "query": self.unstructured_data_query,
                "total_extractions": len(all_ai_extractions),
                "model_used": "gemini-2.5-flash via LangExtract (page par page)"
            }
            print(f"🤖 SCANNER: Total extractions IA: {len(all_ai_extractions)}")
        
        # Construire les résultats finaux
        print(f"📊 SCANNER: Création des résultats finaux")
        results = {
            "stats": {
                "total_pages": total_pages,
                "pages_with_qr": pages_with_qr,
                "unique_urls": len({r["url"] for r in unique_url_results}),
                "total_url_results": len(unique_url_results),
                "extracted_lines": len(all_text_extractions),
                "ai_extracted_items": len(all_ai_extractions),
            },
            "url_results": unique_url_results,
            "extractions": all_text_extractions,
            "csv_filename": csv_writer_info["filename"] if csv_writer_info else None,
            "ai_extraction": ai_extraction_results,
            "validation_summary": self._get_validation_summary(unique_url_results),
            "text_stats": self._get_text_stats(all_text_extractions) if all_text_extractions else None
        }
        
        # Log des résultats finaux
        self._log_final_results(results)
        
        return results
    
    def _get_validation_summary(self, url_results: List[Dict]) -> Optional[Dict]:
        """
        Génère un résumé des validations HTTP
        
        Args:
            url_results: Résultats des validations d'URLs
            
        Returns:
            Optional[Dict]: Résumé des validations
        """
        if not url_results:
            return None
        
        return self.http_validator.get_validation_summary(url_results)
    
    def _get_text_stats(self, text_extractions: List[Dict]) -> Dict[str, Any]:
        """
        Génère des statistiques sur les extractions de texte
        
        Args:
            text_extractions: Extractions de texte
            
        Returns:
            Dict: Statistiques des extractions
        """
        return self.text_extractor.get_extraction_stats(text_extractions)
    
    def _log_final_results(self, results: Dict[str, Any]) -> None:
        """
        Log les résultats finaux
        
        Args:
            results: Résultats finaux à logger
        """
        stats = results["stats"]
        print(f"📊 SCANNER: Résultats finaux créés:")
        print(f"📊 SCANNER: - Pages totales: {stats['total_pages']}")
        print(f"📊 SCANNER: - Pages avec QR: {stats['pages_with_qr']}")
        print(f"📊 SCANNER: - URLs uniques: {stats['unique_urls']}")
        print(f"📊 SCANNER: - URLs trouvées: {stats['total_url_results']}")
        print(f"📊 SCANNER: - Extractions texte: {stats['extracted_lines']}")
        print(f"📊 SCANNER: - Extractions IA: {stats['ai_extracted_items']}")
        
        # Log du résumé de validation si disponible
        if results.get("validation_summary"):
            summary = results["validation_summary"]
            print(f"📊 SCANNER: - HTTP success: {summary.get('http_success', 0)}")
            print(f"📊 SCANNER: - Temps réponse moyen: {summary.get('avg_response_time', 0)}ms")