"""
Configuración central del proyecto AI Grocery Planner.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

MERCADONA_CLI = os.getenv("MERCADONA_CLI_PATH", "mercadona")
MERCADONA_WAREHOUSE = os.getenv("MERCADONA_WAREHOUSE", "mad1")
MERCADONA_MAX_EUR = float(os.getenv("MERCADONA_MAX_EUR", "0"))

CACHE_DB = DATA_DIR / "cache.db"
PRODUCTS_CACHE = DATA_DIR / "products_cache.json"

DEFAULT_BUDGET_PER_DAY = 10.0
DEFAULT_SERVINGS = 2
