from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent
CREDENTIALS_JSON = EVALUATION_DIR / 'credentials.json'

DATA_DIR = EVALUATION_DIR.parent / 'data'
TESTS_JSON = DATA_DIR / 'tests.json'
TESTS_IMG = DATA_DIR / 'images'

FAILED_THRESHOLD = 0.75