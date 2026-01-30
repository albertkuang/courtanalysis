import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

UTR_EMAIL = os.getenv('UTR_EMAIL')
UTR_PASSWORD = os.getenv('UTR_PASSWORD')

if not UTR_EMAIL or not UTR_PASSWORD:
    # Fallback or strict error?
    # For now, let's print a warning but allow it to fail later if needed, 
    # or rely on the scripts to handle missing config if they wish.
    # But since these are critical, maybe just warning.
    pass

UTR_CONFIG = {
    'email': UTR_EMAIL,
    'password': UTR_PASSWORD
}
