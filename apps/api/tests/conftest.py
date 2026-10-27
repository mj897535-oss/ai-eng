import sys
from pathlib import Path

# Add apps/api directory to sys.path so app is directly importable
API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))
