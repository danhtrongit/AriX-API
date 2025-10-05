import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'sk-p8eL9PNj1G6wrmXruExXHHLjs04FhQLpKuXFh0H9xEUTTUVJ')
    OPENAI_BASE = os.getenv('OPENAI_BASE', 'https://v98store.com/v1')

    # Flask settings
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

    # VNStock settings
    VNSTOCK_DEFAULT_SOURCE = os.getenv('VNSTOCK_DEFAULT_SOURCE', 'vci')

    # Chat settings
    MAX_CONVERSATION_HISTORY = int(os.getenv('MAX_CONVERSATION_HISTORY', '10'))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # RAG Settings
    QDRANT_HOST = os.getenv('QDRANT_HOST', 'localhost')
    QDRANT_PORT = int(os.getenv('QDRANT_PORT', '6333'))
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', None)  # Optional API key for Qdrant Cloud
    QDRANT_COLLECTION = os.getenv('QDRANT_COLLECTION', 'financial_vectors')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
    CHAT_MODEL = os.getenv('CHAT_MODEL', 'gpt-4o-mini')