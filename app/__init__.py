from flask import Flask
from flask_socketio import SocketIO
from .config import Config

socketio = SocketIO(cors_allowed_origins="*")  # WebSocket

def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    import os
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Blueprints
    from .routes.web import bp as web_bp
    from .routes.api import bp as api_bp
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    socketio.init_app(app)

    return app
