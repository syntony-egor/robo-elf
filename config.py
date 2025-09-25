import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not found in environment variables")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")