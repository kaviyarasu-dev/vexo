import json
from pathlib import Path
import sys

# Ensure project root is in sys.path when script is run directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.integrity_auditor import DataIntegrityAuditor
from db.connection import get_db

def run():
    db = get_db()
    auditor = DataIntegrityAuditor(db)
    report = auditor.run_audit()
    print(json.dumps(report, indent=2))
    if report["anomalies_detected"]:
        print("Anomalies found!")
        
if __name__ == "__main__":
    run()
