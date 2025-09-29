import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    # Flask settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

    # VNStock settings
    VNSTOCK_DEFAULT_SOURCE = os.getenv('VNSTOCK_DEFAULT_SOURCE', 'TCBS')

    # Chat settings
    MAX_CONVERSATION_HISTORY = int(os.getenv('MAX_CONVERSATION_HISTORY', '10'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')