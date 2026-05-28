"""Debug script for features endpoint issue."""
import sys, traceback
sys.path.insert(0, '/app')

from modules.database import get_db_connection
db = get_db_connection()
print('Backend:', type(db._backend).__name__)

# Test 1: direct DB query
try:
    r = db.query("SELECT * FROM technical_features WHERE ticker = ? ORDER BY date", ('AAPL',))
    print('Direct query OK, rows:', len(r))
except Exception as e:
    traceback.print_exc()
    print('Direct query ERROR:', type(e).__name__, '|', str(e)[:300])

# Test 2: via queries module
try:
    from modules.database.queries import get_technical_features as q_gtf
    r = q_gtf('AAPL')
    print('queries.get_technical_features OK, rows:', len(r))
except Exception as e:
    traceback.print_exc()
    print('queries.get_technical_features ERROR:', type(e).__name__, '|', str(e)[:300])

# Test 3: TechnicalIndicatorCalculator
try:
    from modules.features.technical_indicators import TechnicalIndicatorCalculator
    print('TechnicalIndicatorCalculator import OK')
    calc = TechnicalIndicatorCalculator()
    df = calc.calculate_all_indicators('AAPL')
    print('calculate_all_indicators OK, rows:', len(df))
except Exception as e:
    traceback.print_exc()
    print('TechnicalIndicatorCalculator ERROR:', type(e).__name__, '|', str(e)[:300])
