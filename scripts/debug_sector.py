"""Debug sector rotation."""
import sys, traceback
sys.path.insert(0, '/app')
try:
    from modules.features.sector_rotation_detector import SectorRotationDetector
    print('import OK')
    d = SectorRotationDetector()
    print('init OK')
    r = d.analyze_rotation()
    print('result OK:', str(r)[:200])
except Exception as e:
    traceback.print_exc()
    print(type(e).__name__, ':', str(e)[:300])
