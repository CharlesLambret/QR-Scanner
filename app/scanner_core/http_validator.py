"""
Module de validation HTTP
Responsable de la validation des URLs, domaines, paramètres UTM et contenu des pages
"""
import requests
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, List


class HTTPValidator:
    """Validateur HTTP pour les URLs trouvées dans les QR codes"""
    
    def __init__(self, timeout: int = 10, 
                 expected_domains: Optional[List[str]] = None,
                 expected_utm_params: Optional[Dict[str, str]] = None,
                search_texts: Optional[List[str]] = None,
                 log_callback=None):
        """
        Initialise le validateur HTTP
        
        Args:
            timeout: Timeout pour les requêtes HTTP
            expected_domains: Liste des domaines attendus
            expected_utm_params: Paramètres UTM attendus
                    search_texts: Textes à rechercher sur les pages de destination
            log_callback: Fonction de callback pour les logs
        """
        self.timeout = timeout
        self.expected_domains = expected_domains or []
        self.expected_utm_params = expected_utm_params or {}
        self.search_texts = search_texts or []
        self.log_callback = log_callback or (lambda level, msg: None)
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """
        Valide une URL complètement
        
        Args:
            url: URL à valider
            
        Returns:
            Dict: Résultats de validation
        """
        result = {
            "url": url,
            "http_status": None,
            "netloc": "",
            "utm": None,
            "domain_valid": None,
            "utm_valid": None,
            "text_search_valid": None,
            "response_time": None,
            "final_url": None,
            "error": None
        }
        
        try:
            # Parser l'URL
            parsed = urlparse(url)
            result["netloc"] = parsed.netloc
            
            # Extraire les paramètres UTM
            utm_params = self._extract_utm_params(parsed.query)
            result["utm"] = utm_params if utm_params else None
            
            # Validation du domaine
            result["domain_valid"] = self._validate_domain(parsed.netloc)
            
            # Validation des paramètres UTM
            result["utm_valid"] = self._validate_utm_params(utm_params)
            
            # Requête HTTP pour status et contenu
            http_result = self._make_http_request(url)
            result.update(http_result)
            
            # Validation du contenu de la page
            if http_result.get("response_text"):
                result["text_search_valid"] = self._validate_page_content(
                    http_result["response_text"]
                )
            elif self.search_texts:
                result["text_search_valid"] = False
                
        except Exception as e:
            self.log_callback("WARNING", f"Erreur lors de la validation de {url}: {e}")
            result["error"] = str(e)
        
        return result
    
    def _extract_utm_params(self, query_string: str) -> Dict[str, str]:
        """
        Extrait les paramètres UTM de la query string
        
        Args:
            query_string: Query string de l'URL
            
        Returns:
            Dict: Paramètres UTM trouvés
        """
        parsed_params = parse_qs(query_string)
        utm_params = {}
        
        for key, values in parsed_params.items():
            if key.lower().startswith("utm_") and values:
                utm_params[key] = values[0]  # Prendre la première valeur
        
        return utm_params
    
    def _validate_domain(self, netloc: str) -> Optional[bool]:
        """
        Valide le domaine par rapport à la liste des domaines attendus
        
        Args:
            netloc: Domaine à valider
            
        Returns:
            Optional[bool]: True si valide, False si invalide, None si pas de validation
        """
        if not self.expected_domains:
            return None
        
        # Vérification exacte d'abord
        if netloc in self.expected_domains:
            return True
        
        # Vérification des sous-domaines
        for domain in self.expected_domains:
            if netloc.endswith('.' + domain) or netloc == domain:
                return True
        
        return False
    
    def _validate_utm_params(self, utm_params: Dict[str, str]) -> Optional[bool]:
        """
        Valide les paramètres UTM
        
        Args:
            utm_params: Paramètres UTM trouvés
            
        Returns:
            Optional[bool]: True si valides, False si invalides, None si pas de validation
        """
        if not self.expected_utm_params:
            return None
        
        if not utm_params:
            return False
        
        # Vérifier que tous les paramètres attendus sont présents avec les bonnes valeurs
        for key, expected_value in self.expected_utm_params.items():
            if utm_params.get(key) != expected_value:
                return False
        
        return True
    
    def _validate_page_content(self, response_text: str) -> Optional[bool]:
        """
        Valide le contenu de la page de destination
        
        Args:
            response_text: Contenu HTML de la page
            
        Returns:
            Optional[bool]: True si les textes sont trouvés, False sinon, None si pas de validation
        """
        if not self.search_texts:
            return None
        
        response_lower = response_text.lower()
        
        # Vérifier si au moins un des textes est présent
        for text in self.search_texts:
            if text.lower() in response_lower:
                return True
        
        return False
    
    def _make_http_request(self, url: str) -> Dict[str, Any]:
        """
        Effectue la requête HTTP et retourne les résultats
        
        Args:
            url: URL à requêter
            
        Returns:
            Dict: Résultats de la requête HTTP
        """
        import time
        
        result = {
            "http_status": None,
            "response_time": None,
            "final_url": None,
            "response_text": None,
            "content_type": None,
            "content_length": None
        }
        
        start_time = time.time()
        
        try:
            # Essayer HEAD d'abord (plus rapide)
            response = requests.head(
                url, 
                timeout=self.timeout, 
                allow_redirects=True,
                headers={'User-Agent': 'QR-Scanner/1.0'}
            )
            
            result["http_status"] = response.status_code
            result["final_url"] = response.url
            result["content_type"] = response.headers.get("content-type")
            result["content_length"] = response.headers.get("content-length")
            
            # Si on a besoin du contenu de la page et que HEAD a réussi
            if self.search_texts and response.status_code == 200:
                try:
                    get_response = requests.get(
                        url, 
                        timeout=self.timeout, 
                        allow_redirects=True,
                        headers={'User-Agent': 'QR-Scanner/1.0'}
                    )
                    result["response_text"] = get_response.text
                    
                except Exception as e:
                    self.log_callback("WARNING", f"Erreur GET après HEAD réussi pour {url}: {e}")
            
        except requests.exceptions.RequestException:
            # Si HEAD échoue, essayer GET directement
            try:
                response = requests.get(
                    url, 
                    timeout=self.timeout, 
                    allow_redirects=True,
                    headers={'User-Agent': 'QR-Scanner/1.0'}
                )
                
                result["http_status"] = response.status_code
                result["final_url"] = response.url
                result["content_type"] = response.headers.get("content-type")
                result["content_length"] = len(response.content) if response.content else None
             
            except Exception as e:
                self.log_callback("WARNING", f"Erreur lors de la requête HTTP pour {url}: {e}")
                result["error"] = str(e)
        
        result["response_time"] = round((time.time() - start_time) * 1000, 2)  # en ms
        
        return result
    
    def validate_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Valide plusieurs URLs
        
        Args:
            urls: Liste des URLs à valider
            
        Returns:
            List[Dict]: Résultats de validation pour chaque URL
        """
        results = []
        
        for url in urls:
            if url.startswith(("http://", "https://")):
                result = self.validate_url(url)
                results.append(result)
            else:
                self.log_callback("WARNING", f"URL invalide ignorée: {url}")
        
        return results
    
    def get_validation_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Génère un résumé des validations
        
        Args:
            results: Résultats de validation
            
        Returns:
            Dict: Résumé des validations
        """
        total = len(results)
        if total == 0:
            return {"total": 0}
        
        summary = {
            "total": total,
            "http_success": sum(1 for r in results if r.get("http_status") == 200),
            "http_errors": sum(1 for r in results if r.get("http_status") != 200),
            "domain_valid": sum(1 for r in results if r.get("domain_valid") is True),
            "domain_invalid": sum(1 for r in results if r.get("domain_valid") is False),
            "utm_valid": sum(1 for r in results if r.get("utm_valid") is True),
            "utm_invalid": sum(1 for r in results if r.get("utm_valid") is False),
            "text_valid": sum(1 for r in results if r.get("text_search_valid") is True),
            "text_invalid": sum(1 for r in results if r.get("text_search_valid") is False),
            "avg_response_time": round(
                sum(r.get("response_time", 0) for r in results if r.get("response_time")) / total, 
                2
            )
        }
        
        return summary