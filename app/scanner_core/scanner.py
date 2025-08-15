import io
import os
import csv
import fitz  # PyMuPDF
import cv2
import numpy as np
import requests
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .models import PDFTask
from ..services.ai_extraction import AIDataExtractor

# pyzbar (blindé)
from pyzbar.pyzbar import decode as zbar_decode, ZBarSymbol

@dataclass
class LoggerShim:
    level: str = "INFO"
    def log(self, level: str, msg: str):
        wanted = ["DEBUG","INFO","WARNING","ERROR"]
        if wanted.index(level) >= wanted.index(self.level):
            print(f"{level} - {msg}")

class QRCodePDFScanner:
    """
    Scanner synchrone pour un PDF:
      - rendu page -> image (PyMuPDF)
      - détection QR (pyzbar, filtré QRCode, + fallback OpenCV)
      - GET HEAD/GET URL, extraction UTM
      - extraction texte pages impaires si demandé
      - export CSV si extract_text=True
    """
    def __init__(
        self,
        pdf_path: str,
        timeout: int = 10,
        search_texts: Optional[List[str]] = None,
        extract_text: bool = False,
        out_dir: Optional[str] = None,
        log_level: str = "INFO",
        progress_callback=None,
        expected_domains: Optional[List[str]] = None,
        expected_utm_params: Optional[Dict[str, str]] = None,
        landing_page_texts: Optional[List[str]] = None,
        unstructured_data_query: Optional[str] = None
    ):
        print(f"🏗️ SCANNER: __init__ appelé avec pdf_path={pdf_path}")
        print(f"🏗️ SCANNER: progress_callback présent={progress_callback is not None}")
        
        self.task = PDFTask(pdf_path=pdf_path, timeout=timeout, search_texts=search_texts, extract_text=extract_text)
        self.out_dir = out_dir or os.path.dirname(pdf_path)
        self.logger = LoggerShim(level=log_level)
        self.progress_callback = progress_callback or (lambda msg: None)
        self.expected_domains = expected_domains
        self.expected_utm_params = expected_utm_params
        self.landing_page_texts = landing_page_texts
        self.unstructured_data_query = unstructured_data_query
        
        # Initialize AI extractor if needed
        self.ai_extractor = AIDataExtractor() if unstructured_data_query else None
        
        print(f"🏗️ SCANNER: Scanner initialisé avec success")


    # ---------- Utils ----------
    def safe_log(self, level: str, msg: str):
        try:
            self.logger.log(level, msg)
        except Exception:
            pass

    def _page_to_image(self, page: fitz.Page, zoom: float = 2.0) -> np.ndarray:
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        if pix.n != 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)

        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
        return img

    def _decode_qr_pyzbar(self, gray: np.ndarray) -> List[str]:
        """Ne lire que les QR codes, ignorer DataBar (corrige l’assert seg->finder)."""
        found = set()
        rotations = [
            gray,
            cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(gray, cv2.ROTATE_180),
            cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE),
        ]
        for idx, frame in enumerate(rotations):
            try:
                codes = zbar_decode(frame, symbols=[ZBarSymbol.QRCODE])
            except Exception as e:
                self.safe_log("WARNING", f"pyzbar decode erreur (rot {idx}): {e}")
                continue
            for c in codes:
                try:
                    data = c.data.decode("utf-8")
                except UnicodeDecodeError:
                    data = c.data.decode("latin-1", errors="ignore")
                if data:
                    found.add(data.strip())
        return list(found)

    def _decode_qr_opencv(self, gray: np.ndarray) -> List[str]:
        det = cv2.QRCodeDetector()
        # detectAndDecodeMulti dispo selon versions OpenCV
        try:
            retval, decoded_info, _, _ = det.detectAndDecodeMulti(gray)
            if retval and decoded_info:
                return [s for s in decoded_info if s]
        except Exception:
            pass
        # fallback single
        try:
            data, points, _ = det.detectAndDecode(gray)
            if points is not None and data:
                return [data]
        except Exception:
            pass
        return []

    def detect_qr_codes(self, image_bgr: np.ndarray) -> List[str]:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        # d'abord pyzbar (robuste), filtré QR seulement
        data = self._decode_qr_pyzbar(gray)
        if data:
            return data
        # fallback OpenCV si rien
        return self._decode_qr_opencv(gray)

    def _http_check(self, url: str) -> Dict[str, Any]:
        res = {
            "url": url, 
            "http_status": None, 
            "netloc": "", 
            "utm": None,
            "domain_valid": None,
            "utm_valid": None, 
            "text_search_valid": None
        }
        try:
            p = urlparse(url)
            res["netloc"] = p.netloc
            utm = {k: v[0] for k, v in parse_qs(p.query).items() if k.lower().startswith("utm_")}
            res["utm"] = utm or None
            
            # Domain validation
            if self.expected_domains:
                # Check exact match first
                if p.netloc in self.expected_domains:
                    res["domain_valid"] = True
                else:
                    # Check if netloc is a subdomain of any expected domain
                    res["domain_valid"] = any(
                        p.netloc.endswith('.' + domain) or p.netloc == domain
                        for domain in self.expected_domains
                    )
            
            # UTM parameter validation
            if self.expected_utm_params:
                if utm:
                    res["utm_valid"] = all(
                        utm.get(key) == expected_value 
                        for key, expected_value in self.expected_utm_params.items()
                    )
                else:
                    res["utm_valid"] = False
            
            # HTTP request for status and landing page text
            response_text = None
            try:
                r = requests.head(url, timeout=self.task.timeout, allow_redirects=True)
                res["http_status"] = r.status_code
                
                # If we need to check landing page text, we need to do a GET request
                if self.landing_page_texts and r.status_code == 200:
                    try:
                        r = requests.get(url, timeout=self.task.timeout, allow_redirects=True)
                        response_text = r.text
                    except Exception:
                        pass
            except Exception:
                try:
                    r = requests.get(url, timeout=self.task.timeout, allow_redirects=True)
                    res["http_status"] = getattr(r, "status_code", None)
                    if self.landing_page_texts:
                        response_text = getattr(r, "text", "")
                except Exception:
                    pass
            
            # Landing page text validation
            if self.landing_page_texts and response_text:
                res["text_search_valid"] = any(
                    text.lower() in response_text.lower() 
                    for text in self.landing_page_texts
                )
            elif self.landing_page_texts:
                res["text_search_valid"] = False
                
        except Exception as e:
            self.safe_log("WARNING", f"HTTP check failed for {url}: {e}")
        return res

    def _extract_text_linewise(self, page: fitz.Page) -> List[str]:
        text = page.get_text("text")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return lines

    # ---------- Public ----------
    def scan_pdf(self) -> Dict[str, Any]:
        print(f"📖 SCANNER: scan_pdf démarré")
        pdf_path = self.task.pdf_path
        print(f"📖 SCANNER: Ouverture du PDF {pdf_path}")
        doc = fitz.open(pdf_path)
        
        print(f"📢 SCANNER: Envoi du message de progression initial")
        self.progress_callback(f"Lecture du PDF : {pdf_path} ({len(doc)} pages)")

        total_pages = len(doc)
        url_rows: List[Dict[str, Any]] = []
        extractions: List[Dict[str, Any]] = []
        pages_with_qr = 0
        
        print(f"📖 SCANNER: PDF ouvert, {total_pages} pages à traiter")

        # CSV handle if needed
        csv_filename = None
        csv_path = None
        csv_writer = None
        if self.task.extract_text:
            csv_filename = "extractions.csv"
            csv_path = os.path.join(self.out_dir, csv_filename)
            csv_fh = open(csv_path, "w", newline="", encoding="utf-8")
            csv_writer = csv.writer(csv_fh)
            csv_writer.writerow(["page", "line"])

        try:
            for i in range(total_pages):
                print(f"📄 SCANNER: Traitement page {i + 1}/{total_pages}")
                self.progress_callback(f"Lecture page {i + 1}/{len(doc)}")

                page = doc[i]
                # Render -> image
                print(f"🖼️ SCANNER: Conversion page {i + 1} en image")
                img = self._page_to_image(page, zoom=2.0)

                # QR
                print(f"🔍 SCANNER: Détection QR codes page {i + 1}")
                qr_values = self.detect_qr_codes(img)
                print(f"🔍 SCANNER: QR codes trouvés page {i + 1}: {qr_values}")
                
                if qr_values:
                    pages_with_qr += 1
                    for val in qr_values:
                        print(f"🔗 SCANNER: Analyse URL: {val}")
                        # heuristique URL
                        if val.startswith(("http://", "https://")):
                            print(f"🌐 SCANNER: Test HTTP pour URL: {val}")
                            row = self._http_check(val)
                            row["page"] = i + 1
                            url_rows.append(row)
                            print(f"🌐 SCANNER: Résultat HTTP: {row}")

                # Text extraction on odd pages (1-indexed: 1,3,5…)
                if self.task.extract_text and ((i + 1) % 2 == 1):
                    print(f"📝 SCANNER: Extraction texte page {i + 1}")
                    lines = self._extract_text_linewise(page)
                    for ln in lines:
                        record = {"page": i + 1, "line": ln}
                        extractions.append(record)
                        if csv_writer:
                            csv_writer.writerow([record["page"], record["line"]])
                
                # Ajout du callback à la fin du scan de la page
                print(f"📢 SCANNER: Envoi message fin page {i + 1}")
                self.progress_callback(f"Page {i + 1} scannée")
        finally:
            if self.task.extract_text and csv_writer:
                csv_fh.close()
            doc.close()
            print(f"📖 SCANNER: Document fermé")

        # dedup urls by (url, page)
        print(f"🔗 SCANNER: Déduplication des URLs")
        seen = set()
        uniq_url_rows = []
        for r in url_rows:
            key = (r["url"], r["page"])
            if key not in seen:
                uniq_url_rows.append(r)
                seen.add(key)

        # AI-based data extraction if requested
        ai_extraction_results = None
        if self.unstructured_data_query and self.ai_extractor:
            print(f"🤖 SCANNER: Début de l'extraction IA")
            self.progress_callback("Extraction de données avec IA...")
            
            # Collect all text from the PDF for AI processing
            full_text = ""
            doc = fitz.open(self.task.pdf_path)  # Reopen for text extraction
            try:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    full_text += page.get_text("text") + "\n"
            finally:
                doc.close()
            
            print(f"🤖 SCANNER: Texte extrait ({len(full_text)} caractères), envoi à l'IA")
            ai_extraction_results = self.ai_extractor.extract_data(full_text, self.unstructured_data_query)
            print(f"🤖 SCANNER: Extraction IA terminée: {ai_extraction_results.get('success', False)}")

        print(f"📊 SCANNER: Création des résultats finaux")
        results: Dict[str, Any] = {
            "stats": {
                "total_pages": total_pages,
                "pages_with_qr": pages_with_qr,
                "unique_urls": len({r["url"] for r in uniq_url_rows}),
                "extracted_lines": len(extractions),
                "ai_extracted_items": len(ai_extraction_results.get("extracted_data", [])) if ai_extraction_results else 0,
            },
            "url_results": uniq_url_rows,
            "extractions": extractions,
            "csv_filename": csv_filename if csv_filename else None,
            "ai_extraction": ai_extraction_results,
        }
        
        print(f"📊 SCANNER: Résultats finaux créés:")
        print(f"📊 SCANNER: - Pages totales: {results['stats']['total_pages']}")
        print(f"📊 SCANNER: - Pages avec QR: {results['stats']['pages_with_qr']}")
        print(f"📊 SCANNER: - URLs uniques: {results['stats']['unique_urls']}")
        print(f"📊 SCANNER: - URLs trouvées: {len(uniq_url_rows)}")
        print(f"📊 SCANNER: - Extractions: {len(extractions)}")
        
        return results
