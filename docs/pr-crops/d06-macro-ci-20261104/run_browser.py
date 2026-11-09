from pathlib import Path
import sys
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root))
from scripts import verify_d06_macro as verifier
# Configure only the existing harness artifact destination; no application state is changed.
verifier.OUT=Path(__file__).resolve().parent
verifier.main()
