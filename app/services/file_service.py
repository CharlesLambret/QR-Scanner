"""
Service de gestion des fichiers
Responsable de la sauvegarde, validation et nettoyage des fichiers uploadés
"""
import os
import uuid
import shutil
from typing import Tuple, Optional
from flask import current_app
from werkzeug.exceptions import UnsupportedMediaType
from werkzeug.datastructures import FileStorage


class FileService:
    """Service de gestion des fichiers uploadés"""
    
    @staticmethod
    def save_upload(file_storage: FileStorage) -> Tuple[str, str]:
        """
        Sauvegarde un fichier uploadé et retourne le chemin et l'ID de scan
        
        Args:
            file_storage: Fichier uploadé via Flask
            
        Returns:
            Tuple[str, str]: (chemin_fichier, scan_id)
            
        Raises:
            UnsupportedMediaType: Si le fichier n'est pas un PDF
        """
        # Validation du fichier
        filename = file_storage.filename or "upload.pdf"
        if not FileService._is_valid_pdf(filename):
            raise UnsupportedMediaType("Only PDF files are allowed")
        
        # Génération de l'ID de scan et du dossier de destination
        scan_id = str(uuid.uuid4())
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        scan_dir = os.path.join(upload_dir, scan_id)
        
        # Création du dossier de scan
        os.makedirs(scan_dir, exist_ok=True)
        
        # Sauvegarde du fichier
        file_path = os.path.join(scan_dir, "document.pdf")
        file_storage.save(file_path)
        
        print(f"💾 FILE_SERVICE: Fichier sauvé: {file_path} (scan_id: {scan_id})")
        return file_path, scan_id
    
    @staticmethod
    def cleanup_files(pdf_path: str, scan_id: Optional[str] = None) -> bool:
        """
        Supprime le fichier PDF et son dossier après traitement
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            scan_id: ID du scan (optionnel)
            
        Returns:
            bool: True si le nettoyage a réussi
        """
        try:
            if os.path.exists(pdf_path):
                # Supprimer le fichier PDF
                os.remove(pdf_path)
                print(f"🗑️ FILE_SERVICE: Fichier PDF supprimé: {pdf_path}")
                
                # Supprimer le dossier si vide et contient scan_id
                pdf_dir = os.path.dirname(pdf_path)
                if scan_id and scan_id in pdf_dir:
                    try:
                        os.rmdir(pdf_dir)
                        print(f"🗑️ FILE_SERVICE: Dossier scan supprimé: {pdf_dir}")
                    except OSError as e:
                        # Dossier non vide
                        print(f"⚠️ FILE_SERVICE: Impossible de supprimer le dossier {pdf_dir}: {e}")
                
                return True
            else:
                print(f"⚠️ FILE_SERVICE: Fichier PDF non trouvé pour suppression: {pdf_path}")
                return False
                
        except Exception as e:
            print(f"❌ FILE_SERVICE: Erreur lors de la suppression du PDF {pdf_path}: {e}")
            return False
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        Récupère les informations d'un fichier
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            dict: Informations sur le fichier
        """
        if not os.path.exists(file_path):
            return {"exists": False}
        
        stat = os.stat(file_path)
        return {
            "exists": True,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "filename": os.path.basename(file_path),
            "extension": os.path.splitext(file_path)[1].lower()
        }
    
    @staticmethod
    def _is_valid_pdf(filename: str) -> bool:
        """
        Vérifie si le fichier est un PDF valide
        
        Args:
            filename: Nom du fichier à vérifier
            
        Returns:
            bool: True si c'est un PDF valide
        """
        if not filename:
            return False
        
        return filename.lower().endswith(".pdf")
    
    @staticmethod
    def ensure_upload_directory() -> None:
        """
        S'assure que le dossier d'upload existe
        """
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        print(f"📁 FILE_SERVICE: Dossier d'upload vérifié: {upload_dir}")
    
    @staticmethod
    def cleanup_old_files(max_age_hours: int = 24) -> int:
        """
        Nettoie les fichiers anciens du dossier d'upload
        
        Args:
            max_age_hours: Âge maximum des fichiers en heures
            
        Returns:
            int: Nombre de fichiers supprimés
        """
        import time
        
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        if not os.path.exists(upload_dir):
            return 0
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        try:
            for item in os.listdir(upload_dir):
                item_path = os.path.join(upload_dir, item)
                
                if os.path.isdir(item_path):
                    # Vérifier l'âge du dossier
                    stat = os.stat(item_path)
                    if current_time - stat.st_mtime > max_age_seconds:
                        shutil.rmtree(item_path)
                        deleted_count += 1
                        print(f"🗑️ FILE_SERVICE: Dossier ancien supprimé: {item_path}")
                        
        except Exception as e:
            print(f"❌ FILE_SERVICE: Erreur lors du nettoyage automatique: {e}")
        
        return deleted_count