"""
Service de gestion des WebSockets
Responsable de la communication temps réel avec le client
"""
from typing import Dict, Any, Callable, Optional
from flask import current_app
from flask_socketio import emit
from .. import socketio


class WebSocketService:
    """Service de gestion des communications WebSocket"""
    
    # Stockage temporaire des scans en cours
    pending_scans: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register_scan(cls, scan_id: str, scan_data: Dict[str, Any]) -> None:
        """
        Enregistre un scan en attente de traitement
        
        Args:
            scan_id: Identifiant unique du scan
            scan_data: Données du scan (pdf_path, options, etc.)
        """
        cls.pending_scans[scan_id] = scan_data
        print(f"📦 WS_SERVICE: Scan enregistré pour scan_id={scan_id}")
    
    @classmethod
    def get_scan_data(cls, scan_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les données d'un scan
        
        Args:
            scan_id: Identifiant du scan
            
        Returns:
            Optional[Dict]: Données du scan ou None si non trouvé
        """
        return cls.pending_scans.get(scan_id)
    
    @classmethod
    def remove_scan(cls, scan_id: str) -> bool:
        """
        Supprime un scan des données temporaires
        
        Args:
            scan_id: Identifiant du scan
            
        Returns:
            bool: True si le scan a été supprimé
        """
        if scan_id in cls.pending_scans:
            del cls.pending_scans[scan_id]
            print(f"🗑️ WS_SERVICE: Données de scan supprimées pour scan_id={scan_id}")
            return True
        return False
    
    @staticmethod
    def emit_progress(scan_id: str, message: str) -> None:
        """
        Émet un message de progression
        
        Args:
            scan_id: Identifiant du scan
            message: Message de progression
        """
        try:
            socketio.emit("scan_progress", {"scan_id": scan_id, "message": message})
            print(f"📢 WS_SERVICE: Progression envoyée pour scan_id={scan_id}: {message}")
        except Exception as e:
            print(f"❌ WS_SERVICE: Erreur lors de l'envoi de progression: {e}")
    
    @staticmethod
    def emit_complete(scan_id: str, results: Dict[str, Any]) -> None:
        """
        Émet un signal de scan terminé
        
        Args:
            scan_id: Identifiant du scan
            results: Résultats du scan
        """
        try:
            socketio.emit("scan_complete", {"scan_id": scan_id, "results": results})
            print(f"📢 WS_SERVICE: Scan terminé envoyé pour scan_id={scan_id}")
        except Exception as e:
            print(f"❌ WS_SERVICE: Erreur lors de l'envoi de completion: {e}")
    
    @staticmethod
    def emit_error(scan_id: str, error_message: str) -> None:
        """
        Émet un signal d'erreur
        
        Args:
            scan_id: Identifiant du scan
            error_message: Message d'erreur
        """
        try:
            socketio.emit("scan_error", {"scan_id": scan_id, "error": error_message})
            print(f"📢 WS_SERVICE: Erreur envoyée pour scan_id={scan_id}: {error_message}")
        except Exception as e:
            print(f"❌ WS_SERVICE: Erreur lors de l'envoi d'erreur: {e}")
    
    @staticmethod
    def create_progress_callback(scan_id: str) -> Callable[[str], None]:
        """
        Crée une fonction de callback pour les mises à jour de progression
        
        Args:
            scan_id: Identifiant du scan
            
        Returns:
            Callable: Fonction de callback
        """
        def progress_callback(message: str) -> None:
            WebSocketService.emit_progress(scan_id, message)
        
        return progress_callback
    
    @staticmethod
    def start_background_scan(scan_id: str, scan_function: Callable, *args, **kwargs) -> None:
        """
        Démarre un scan en arrière-plan
        
        Args:
            scan_id: Identifiant du scan
            scan_function: Fonction de scan à exécuter
            *args, **kwargs: Arguments pour la fonction de scan
        """
        app = current_app._get_current_object()
        
        def background_task():
            with app.app_context():
                try:
                    print(f"🚀 WS_SERVICE: Démarrage du scan en arrière-plan pour scan_id={scan_id}")
                    results = scan_function(*args, **kwargs)
                    
                    WebSocketService.emit_complete(scan_id, results)
                    WebSocketService.remove_scan(scan_id)
                    
                except Exception as e:
                    print(f"❌ WS_SERVICE: Erreur pendant le scan {scan_id}: {e}")
                    WebSocketService.emit_error(scan_id, str(e))
                    WebSocketService.remove_scan(scan_id)
        
        socketio.start_background_task(background_task)


# Gestionnaires d'événements WebSocket
@socketio.on('client_ready')
def handle_client_ready(data):
    """Gestionnaire pour l'événement client_ready"""
    scan_id = data.get('scan_id')
    print(f"🎯 WS_SERVICE: Client prêt pour scan_id={scan_id}")
    
    scan_data = WebSocketService.get_scan_data(scan_id)
    if scan_data:
        print(f"🚀 WS_SERVICE: Démarrage du scan pour scan_id={scan_id}")
        
        # Démarrer le scan en arrière-plan
        from .scan_service import scan_file
        WebSocketService.start_background_scan(
            scan_id,
            scan_file,
            scan_data['pdf_path'],
            scan_data['options'],
            progress_callback=scan_data['progress_callback']
        )
    else:
        print(f"❌ WS_SERVICE: Aucune donnée de scan trouvée pour scan_id={scan_id}")


@socketio.on('test_message')
def handle_test_message(data):
    """Gestionnaire pour les messages de test"""
    print(f"🧪 WS_SERVICE: Message de test reçu: {data}")
    emit('test_response', {'message': 'Test reçu par le serveur'})


@socketio.on('connect')
def handle_connect():
    """Gestionnaire de connexion"""
    print("🔌 WS_SERVICE: Client connecté")


@socketio.on('disconnect')
def handle_disconnect():
    """Gestionnaire de déconnexion"""
    print("🔌 WS_SERVICE: Client déconnecté")