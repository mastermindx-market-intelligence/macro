from pathlib import Path
import sys
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root))
from scripts import verify_d06_macro as verifier
verifier.OUT=Path(__file__).resolve().parent
verifier.main()
