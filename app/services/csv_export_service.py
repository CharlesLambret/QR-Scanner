"""
Service pour l'export CSV des résultats de scan
"""
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime


class CSVExportService:
    """Service pour exporter les données de scan en format CSV"""
    
    @staticmethod
    def export_page_results(url_results: List[Dict[str, Any]], 
                           ai_extraction: Optional[Dict[str, Any]]) -> str:
        """
        Exporte les résultats organisés par page en CSV
        
        Args:
            url_results: Liste des résultats d'URLs/QR codes
            ai_extraction: Données d'extraction IA
            
        Returns:
            str: Contenu CSV prêt pour le téléchargement
        """
        # Organiser les données par page
        page_data = CSVExportService._organize_data_by_page(url_results, ai_extraction)
        
        # Récupérer les keywords sélectionnés pour créer les colonnes dynamiques
        selected_keywords = []
        if ai_extraction and ai_extraction.get('keywords'):
            selected_keywords = ai_extraction['keywords']
        elif ai_extraction and ai_extraction.get('extracted_data'):
            # Fallback: détecter les keywords à partir des extraction_class trouvées
            extraction_classes = set()
            for item in ai_extraction['extracted_data']:
                extraction_class = item.get('extraction_class', item.get('type', ''))
                if extraction_class and extraction_class != 'langextract':
                    extraction_classes.add(extraction_class)
            
            # Mapper les extraction_class vers les keywords correspondants
            class_to_keyword = {
                'client_name': 'nom',
                'code': 'code',
                'civilité': 'civilité',
                'email': 'email',
                'phone': 'téléphone',
                'date': 'date',
                'amount': 'montant',
                'address': 'adresse'
            }
            
            for extraction_class in extraction_classes:
                keyword = class_to_keyword.get(extraction_class, extraction_class)
                if keyword not in selected_keywords:
                    selected_keywords.append(keyword)
        
        
        # Créer le CSV
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        # En-têtes dynamiques
        headers = [
            'Page',
            'QR_URLs',
            'QR_Status_HTTP',
            'QR_Domain_Valid',
            'QR_UTM_Valid', 
            'QR_Text_Valid'
        ]
        
        # Ajouter une colonne pour chaque keyword sélectionné
        for keyword in selected_keywords:
            headers.append(f'AI_{keyword.title()}')
        
        writer.writerow(headers)
        
        # Données par page
        for page_num in sorted(page_data.keys(), key=int):
            data = page_data[page_num]
            
            # Préparer les données QR
            qr_urls = []
            qr_statuses = []
            qr_domain_valid = []
            qr_utm_valid = []
            qr_text_valid = []
            
            for qr in data.get('qrCodes', []):
                qr_urls.append(qr.get('url', ''))
                qr_statuses.append(str(qr.get('http_status', '')))
                qr_domain_valid.append(CSVExportService._format_validation(qr.get('domain_valid')))
                qr_utm_valid.append(CSVExportService._format_validation(qr.get('utm_valid')))
                qr_text_valid.append(CSVExportService._format_validation(qr.get('text_search_valid')))
            
            # Préparer les données IA par keyword
            keyword_data = {}
            for keyword in selected_keywords:
                keyword_data[keyword] = []
            
            for extraction in data.get('aiExtractions', []):
                extraction_class = extraction.get('extraction_class', extraction.get('type', 'unknown'))
                
                # Prioriser extracted_base pour les codes
                if extraction_class == 'code' and extraction.get('attributes', {}).get('extracted_base'):
                    text = extraction['attributes']['extracted_base']
                else:
                    text = extraction.get('text', extraction.get('extraction_text', ''))
                
                # Associer l'extraction au bon keyword
                # Mapping des extraction_class vers les keywords
                class_to_keyword = {
                    'client_name': 'nom',
                    'code': 'code',
                    'civilité': 'civilité',
                    'email': 'email',
                    'phone': 'téléphone',
                    'date': 'date',
                    'amount': 'montant',
                    'address': 'adresse'
                }
                
                # Trouver le keyword correspondant
                corresponding_keyword = None
                for keyword in selected_keywords:
                    if (extraction_class == keyword or 
                        class_to_keyword.get(extraction_class) == keyword or
                        (keyword == 'nom' and extraction_class in ['client_name', 'name']) or
                        (keyword == 'email' and extraction_class in ['email', 'mail']) or
                        (keyword == 'téléphone' and extraction_class in ['phone', 'telephone']) or
                        (keyword == 'montant' and extraction_class in ['amount', 'prix', 'price'])):
                        corresponding_keyword = keyword
                        break
                
                if corresponding_keyword and corresponding_keyword in keyword_data:
                    keyword_data[corresponding_keyword].append(text)
            
            # Écrire la ligne
            row = [
                page_num,
                ' | '.join(qr_urls),
                ' | '.join(qr_statuses),
                ' | '.join(qr_domain_valid),
                ' | '.join(qr_utm_valid),
                ' | '.join(qr_text_valid)
            ]
            
            # Ajouter les données pour chaque keyword
            for keyword in selected_keywords:
                keyword_values = keyword_data.get(keyword, [])
                row.append(' | '.join(keyword_values) if keyword_values else '')
            writer.writerow(row)
        
        content = output.getvalue()
        output.close()
        return content
    
    @staticmethod
    def _organize_data_by_page(url_results: List[Dict[str, Any]], 
                              ai_extraction: Optional[Dict[str, Any]]) -> Dict[str, Dict]:
        """
        Organise les données par page (même logique que le frontend)
        """
        page_data = {}
        
        # Ajouter les QR codes
        if url_results:
            for result in url_results:
                page = str(result.get('page', 'unknown'))
                if page not in page_data:
                    page_data[page] = {'qrCodes': [], 'aiExtractions': []}
                page_data[page]['qrCodes'].append(result)
        
        # Ajouter les extractions IA
        if ai_extraction and ai_extraction.get('success') and ai_extraction.get('extracted_data'):
            for item in ai_extraction['extracted_data']:
                page_number = CSVExportService._extract_page_number(item)
                
                if page_number != 'unknown':
                    page = str(page_number)
                    if page not in page_data:
                        page_data[page] = {'qrCodes': [], 'aiExtractions': []}
                    page_data[page]['aiExtractions'].append(item)
        
        return page_data
    
    @staticmethod
    def _extract_page_number(item: Dict[str, Any]) -> str:
        """
        Extrait le numéro de page d'un élément d'extraction IA
        """
        if item.get('page'):
            return str(item['page'])
        elif item.get('attributes', {}).get('page'):
            return str(item['attributes']['page'])
        elif item.get('source_location', {}).get('page'):
            return str(item['source_location']['page'])
        return 'unknown'
    
    @staticmethod
    def _format_validation(validation_result: Any) -> str:
        """
        Formate un résultat de validation pour l'export CSV
        """
        if validation_result is None:
            return 'Non testé'
        elif validation_result is True:
            return 'Valide'
        elif validation_result is False:
            return 'Invalide'
        else:
            return str(validation_result)
    
    @staticmethod
    def generate_filename(scan_id: str = None) -> str:
        """
        Génère un nom de fichier pour l'export CSV
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if scan_id:
            return f"qr_scan_results_{scan_id[:8]}_{timestamp}.csv"
        else:
            return f"qr_scan_results_{timestamp}.csv"