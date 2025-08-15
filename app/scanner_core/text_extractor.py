"""
Module d'extraction de texte
Responsable de l'extraction et du traitement du texte des pages PDF
"""
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional
import csv
import os


class TextExtractor:
    """Extracteur de texte pour les pages PDF"""
    
    def __init__(self, extract_odd_pages_only: bool = True, log_callback=None):
        """
        Initialise l'extracteur de texte
        
        Args:
            extract_odd_pages_only: Si True, n'extrait que les pages impaires
            log_callback: Fonction de callback pour les logs
        """
        self.extract_odd_pages_only = extract_odd_pages_only
        self.log_callback = log_callback or (lambda level, msg: None)
    
    def extract_from_page(self, page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        """
        Extrait le texte d'une page PDF
        
        Args:
            page: Page PyMuPDF
            page_number: Numéro de la page (1-indexé)
            
        Returns:
            List[Dict]: Liste des lignes extraites avec métadonnées
        """
        # Vérifier si on doit extraire cette page
        if self.extract_odd_pages_only and page_number % 2 == 0:
            return []
        
        extractions = []
        
        try:
            # Extraction du texte ligne par ligne
            lines = self._extract_lines_from_page(page)
            
            for line_number, line_text in enumerate(lines, 1):
                if line_text.strip():  # Ignorer les lignes vides
                    extraction = {
                        "page": page_number,
                        "line": line_text,
                        "line_number": line_number,
                        "char_count": len(line_text),
                        "word_count": len(line_text.split())
                    }
                    extractions.append(extraction)
            
            self.log_callback("INFO", f"Page {page_number}: {len(extractions)} lignes extraites")
            
        except Exception as e:
            self.log_callback("ERROR", f"Erreur extraction texte page {page_number}: {e}")
        
        return extractions
    
    def _extract_lines_from_page(self, page: fitz.Page) -> List[str]:
        """
        Extrait les lignes de texte d'une page
        
        Args:
            page: Page PyMuPDF
            
        Returns:
            List[str]: Liste des lignes de texte
        """
        # Extraction du texte brut
        text = page.get_text("text")
        
        # Séparation en lignes et nettoyage
        lines = []
        for line in text.splitlines():
            cleaned_line = line.strip()
            if cleaned_line:  # Ignorer les lignes vides
                lines.append(cleaned_line)
        
        return lines
    
    def extract_structured_text(self, page: fitz.Page, page_number: int) -> Dict[str, Any]:
        """
        Extrait le texte structuré d'une page avec positions
        
        Args:
            page: Page PyMuPDF
            page_number: Numéro de la page
            
        Returns:
            Dict: Texte structuré avec positions
        """
        try:
            # Extraction du texte avec informations de position
            text_dict = page.get_text("dict")
            
            structured_data = {
                "page": page_number,
                "blocks": [],
                "fonts": set(),
                "text_stats": {
                    "total_chars": 0,
                    "total_words": 0,
                    "total_lines": 0
                }
            }
            
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    block_data = self._process_text_block(block)
                    structured_data["blocks"].append(block_data)
                    
                    # Collecter les statistiques
                    for line in block_data.get("lines", []):
                        structured_data["text_stats"]["total_lines"] += 1
                        structured_data["text_stats"]["total_chars"] += len(line.get("text", ""))
                        structured_data["text_stats"]["total_words"] += len(line.get("text", "").split())
                        
                        # Collecter les polices
                        for span in line.get("spans", []):
                            font_info = f"{span.get('font', 'unknown')}_{span.get('size', 0)}"
                            structured_data["fonts"].add(font_info)
            
            structured_data["fonts"] = list(structured_data["fonts"])
            
            return structured_data
            
        except Exception as e:
            self.log_callback("ERROR", f"Erreur extraction structurée page {page_number}: {e}")
            return {"page": page_number, "blocks": [], "fonts": [], "error": str(e)}
    
    def _process_text_block(self, block: Dict) -> Dict[str, Any]:
        """
        Traite un bloc de texte et extrait les informations structurées
        
        Args:
            block: Bloc de texte PyMuPDF
            
        Returns:
            Dict: Données du bloc structurées
        """
        block_data = {
            "bbox": block.get("bbox"),
            "lines": []
        }
        
        for line in block.get("lines", []):
            line_text = ""
            spans_data = []
            
            for span in line.get("spans", []):
                span_text = span.get("text", "")
                line_text += span_text
                
                spans_data.append({
                    "text": span_text,
                    "font": span.get("font"),
                    "size": span.get("size"),
                    "flags": span.get("flags"),
                    "color": span.get("color"),
                    "bbox": span.get("bbox")
                })
            
            line_data = {
                "text": line_text.strip(),
                "bbox": line.get("bbox"),
                "spans": spans_data
            }
            
            if line_data["text"]:  # Seulement les lignes non vides
                block_data["lines"].append(line_data)
        
        return block_data
    
    def save_to_csv(self, extractions: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Sauvegarde les extractions dans un fichier CSV
        
        Args:
            extractions: Liste des extractions
            output_path: Chemin de sortie du fichier CSV
            
        Returns:
            bool: True si la sauvegarde a réussi
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                if extractions:
                    fieldnames = extractions[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(extractions)
                else:
                    # Fichier vide avec headers par défaut
                    writer = csv.writer(csvfile)
                    writer.writerow(["page", "line", "line_number", "char_count", "word_count"])
            
            self.log_callback("INFO", f"Extractions sauvées dans {output_path}")
            return True
            
        except Exception as e:
            self.log_callback("ERROR", f"Erreur sauvegarde CSV {output_path}: {e}")
            return False
    
    def search_text_in_extractions(self, extractions: List[Dict[str, Any]], 
                                  search_terms: List[str]) -> List[Dict[str, Any]]:
        """
        Recherche des termes dans les extractions
        
        Args:
            extractions: Liste des extractions
            search_terms: Termes à rechercher
            
        Returns:
            List[Dict]: Extractions contenant les termes recherchés
        """
        if not search_terms:
            return extractions
        
        results = []
        search_terms_lower = [term.lower() for term in search_terms]
        
        for extraction in extractions:
            line_text = extraction.get("line", "").lower()
            
            # Vérifier si au moins un terme est présent
            for term in search_terms_lower:
                if term in line_text:
                    # Ajouter des métadonnées sur la correspondance
                    match_info = extraction.copy()
                    match_info["matched_term"] = term
                    match_info["match_position"] = line_text.find(term)
                    results.append(match_info)
                    break
        
        return results
    
    def get_extraction_stats(self, extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Génère des statistiques sur les extractions
        
        Args:
            extractions: Liste des extractions
            
        Returns:
            Dict: Statistiques des extractions
        """
        if not extractions:
            return {"total_lines": 0}
        
        pages = set()
        total_chars = 0
        total_words = 0
        longest_line = ""
        shortest_line = extractions[0].get("line", "") if extractions else ""
        
        for extraction in extractions:
            pages.add(extraction.get("page"))
            line = extraction.get("line", "")
            
            total_chars += len(line)
            total_words += len(line.split())
            
            if len(line) > len(longest_line):
                longest_line = line
            if len(line) < len(shortest_line):
                shortest_line = line
        
        return {
            "total_lines": len(extractions),
            "total_pages": len(pages),
            "total_chars": total_chars,
            "total_words": total_words,
            "avg_chars_per_line": round(total_chars / len(extractions), 2),
            "avg_words_per_line": round(total_words / len(extractions), 2),
            "longest_line": longest_line[:100] + "..." if len(longest_line) > 100 else longest_line,
            "shortest_line": shortest_line,
            "pages_processed": sorted(list(pages))
        }