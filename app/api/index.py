# api/index.py - Point d'entrée pour Vercel
import os
import sys

# Ajouter le répertoire racine au Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import create_app

# Créer l'application Flask
app = create_app()

# Vercel attend une variable 'app' ou une fonction handler
def handler(request):
    return app(request.environ, lambda status, headers: None)

# Point d'entrée principal pour Vercel
if __name__ == "__main__":
    app.run(debug=False)