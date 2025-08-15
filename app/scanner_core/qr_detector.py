"""
Module de détection des QR codes
Responsable de la détection et décodage des QR codes dans les images
"""
import cv2
import numpy as np
from typing import List, Set
from pyzbar.pyzbar import decode as zbar_decode, ZBarSymbol


class QRDetector:
    """Détecteur de QR codes utilisant pyzbar et OpenCV en fallback"""
    
    def __init__(self, log_callback=None):
        """
        Initialise le détecteur
        
        Args:
            log_callback: Fonction de callback pour les logs (optionnel)
        """
        self.log_callback = log_callback or (lambda level, msg: None)
    
    def detect_qr_codes(self, image_bgr: np.ndarray) -> List[str]:
        """
        Détecte tous les QR codes dans une image
        
        Args:
            image_bgr: Image au format BGR (OpenCV)
            
        Returns:
            List[str]: Liste des données des QR codes détectés
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        # Première tentative avec pyzbar (plus robuste)
        qr_data = self._decode_with_pyzbar(gray)
        if qr_data:
            self.log_callback("INFO", f"pyzbar a détecté {len(qr_data)} QR codes")
            return qr_data
        
        # Fallback avec OpenCV
        qr_data = self._decode_with_opencv(gray)
        if qr_data:
            self.log_callback("INFO", f"OpenCV a détecté {len(qr_data)} QR codes")
        
        return qr_data
    
    def _decode_with_pyzbar(self, gray: np.ndarray) -> List[str]:
        """
        Décode les QR codes avec pyzbar (plus robuste)
        Filtre uniquement les QR codes pour éviter les erreurs avec DataBar
        
        Args:
            gray: Image en niveaux de gris
            
        Returns:
            List[str]: Données des QR codes trouvés
        """
        found: Set[str] = set()
        
        # Tester plusieurs rotations de l'image
        rotations = [
            gray,
            cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(gray, cv2.ROTATE_180),
            cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE),
        ]
        
        for idx, frame in enumerate(rotations):
            try:
                # Ne chercher que les QR codes (évite l'erreur avec DataBar)
                codes = zbar_decode(frame, symbols=[ZBarSymbol.QRCODE])
                
                for code in codes:
                    try:
                        # Tentative de décodage UTF-8 d'abord
                        data = code.data.decode("utf-8")
                    except UnicodeDecodeError:
                        # Fallback latin-1 si UTF-8 échoue
                        data = code.data.decode("latin-1", errors="ignore")
                    
                    if data and data.strip():
                        found.add(data.strip())
                        
            except Exception as e:
                self.log_callback("WARNING", f"Erreur pyzbar (rotation {idx}): {e}")
                continue
        
        return list(found)
    
    def _decode_with_opencv(self, gray: np.ndarray) -> List[str]:
        """
        Décode les QR codes avec OpenCV (fallback)
        
        Args:
            gray: Image en niveaux de gris
            
        Returns:
            List[str]: Données des QR codes trouvés
        """
        detector = cv2.QRCodeDetector()
        found: Set[str] = set()
        
        # Tenter la détection multiple (si disponible)
        try:
            retval, decoded_info, points, straight_qrcode = detector.detectAndDecodeMulti(gray)
            if retval and decoded_info:
                for info in decoded_info:
                    if info and info.strip():
                        found.add(info.strip())
                        
        except Exception as e:
            self.log_callback("WARNING", f"Erreur OpenCV detectAndDecodeMulti: {e}")
        
        # Fallback sur la détection simple si pas de résultats
        if not found:
            try:
                data, points, straight_qrcode = detector.detectAndDecode(gray)
                if points is not None and data and data.strip():
                    found.add(data.strip())
                    
            except Exception as e:
                self.log_callback("WARNING", f"Erreur OpenCV detectAndDecode: {e}")
        
        return list(found)
    
    def enhance_image_for_qr(self, image: np.ndarray) -> np.ndarray:
        """
        Améliore une image pour la détection de QR codes
        
        Args:
            image: Image d'entrée
            
        Returns:
            np.ndarray: Image améliorée
        """
        # Conversion en niveaux de gris si nécessaire
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Amélioration du contraste avec CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Lissage léger pour réduire le bruit
        enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        return enhanced
    
    def detect_with_enhancement(self, image_bgr: np.ndarray) -> List[str]:
        """
        Détecte les QR codes avec amélioration d'image
        
        Args:
            image_bgr: Image au format BGR
            
        Returns:
            List[str]: Liste des données des QR codes détectés
        """
        # Tentative normale d'abord
        qr_data = self.detect_qr_codes(image_bgr)
        if qr_data:
            return qr_data
        
        # Si pas de résultats, essayer avec amélioration
        self.log_callback("INFO", "Tentative de détection avec amélioration d'image")
        enhanced = self.enhance_image_for_qr(image_bgr)
        
        # Reconvertir en BGR pour la fonction principale
        if len(enhanced.shape) == 2:
            enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        else:
            enhanced_bgr = enhanced
        
        return self.detect_qr_codes(enhanced_bgr)
    
    def get_qr_positions(self, image_bgr: np.ndarray) -> List[dict]:
        """
        Détecte les QR codes et retourne leurs positions
        
        Args:
            image_bgr: Image au format BGR
            
        Returns:
            List[dict]: Liste des QR codes avec positions et données
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        results = []
        
        # Utiliser pyzbar pour obtenir les positions
        try:
            codes = zbar_decode(gray, symbols=[ZBarSymbol.QRCODE])
            
            for code in codes:
                try:
                    data = code.data.decode("utf-8")
                except UnicodeDecodeError:
                    data = code.data.decode("latin-1", errors="ignore")
                
                if data and data.strip():
                    # Extraire les coordonnées du rectangle
                    points = code.polygon
                    if len(points) == 4:
                        x_coords = [p.x for p in points]
                        y_coords = [p.y for p in points]
                        
                        results.append({
                            "data": data.strip(),
                            "bbox": {
                                "x": min(x_coords),
                                "y": min(y_coords),
                                "width": max(x_coords) - min(x_coords),
                                "height": max(y_coords) - min(y_coords)
                            },
                            "polygon": [(p.x, p.y) for p in points]
                        })
                        
        except Exception as e:
            self.log_callback("WARNING", f"Erreur lors de l'extraction des positions: {e}")
        
        return results