import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent.resolve()
STATIC_DIR = BASE_DIR / 'diriyah_brain_ai' / 'static'
INDEX_HTML = BASE_DIR / 'diriyah_brain_ai' / 'index.html'
UPLOAD_DIR = BASE_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///diriyah.db')
TEAMS_API_KEY = os.getenv('TEAMS_API_KEY')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
ACONEX_API_KEY = os.getenv('ACONEX_API_KEY')
P6_API_KEY = os.getenv('P6_API_KEY')
POWERBI_API_KEY = os.getenv('POWERBI_API_KEY')
YOLO_MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'yolov8n.pt')

# Google Drive settings
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'https://diriyah-ai-demo.onrender.com/drive/callback')

class Settings:
    def __init__(self):
        self.openai_api_key = OPENAI_API_KEY
        self.google_client_id = GOOGLE_CLIENT_ID
        self.google_client_secret = GOOGLE_CLIENT_SECRET
        self.google_redirect_uri = GOOGLE_REDIRECT_URI

def get_settings():
    return Settings()


