import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "instance", "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    THREADS = int(os.getenv("THREADS", 4))
    TIMEOUT_DEFAULT = int(os.getenv("TIMEOUT_DEFAULT", 10))
