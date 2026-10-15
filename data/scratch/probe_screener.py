import sys
sys.path.insert(0, '.')
from db.connection import DuckDBConnectionManager
from services.screener_service import ScreenerService
from core.interfaces import ScreenerFilter

db = DuckDBConnectionManager(read_only=True)
with db.get_read_cursor() as conn:
    print('Total symbols in symbols table:', conn.execute('SELECT COUNT(*) FROM symbols').fetchone()[0])
    print('Categories in symbols table:', conn.execute('SELECT category, count(*) FROM symbols GROUP BY category').fetchall())
    print('Tiers in symbols table:', conn.execute('SELECT tier, count(*) FROM symbols GROUP BY tier').fetchall())
    print('Total distinct symbols in candles_1d_adjusted:', conn.execute('SELECT COUNT(DISTINCT symbol) FROM candles_1d_adjusted').fetchone()[0])
    max_date = conn.execute('SELECT MAX(date) FROM candles_1d_adjusted').fetchone()[0]
    print('Latest date in candles_1d_adjusted:', max_date)
    cnt_latest = conn.execute(f"SELECT COUNT(DISTINCT symbol) FROM candles_1d_adjusted WHERE date = '{max_date}'").fetchone()[0]
    print('Symbols count with candle on latest date:', cnt_latest)
    
    missing = conn.execute('SELECT COUNT(DISTINCT c.symbol) FROM candles_1d_adjusted c LEFT JOIN symbols s ON c.symbol = s.symbol WHERE s.symbol IS NULL').fetchone()[0]
    print('Distinct symbols in candles_1d_adjusted missing from symbols table:', missing)

    # Sample missing symbols if any
    if missing > 0:
        sample_missing = conn.execute('SELECT DISTINCT c.symbol FROM candles_1d_adjusted c LEFT JOIN symbols s ON c.symbol = s.symbol WHERE s.symbol IS NULL LIMIT 10').fetchall()
        print('Sample missing symbols:', sample_missing)

    # Check date distribution of symbols' latest candles
    dates = conn.execute('''
        SELECT max_d, count(*) FROM (
            SELECT symbol, MAX(date) as max_d FROM candles_1d_adjusted GROUP BY symbol
        ) GROUP BY max_d ORDER BY max_d DESC LIMIT 10
    ''').fetchall()
    print('Latest candle dates per symbol distribution:', dates)

service = ScreenerService(db)
print('Templates:', [t['id'] for t in service.list_presets()])
for t in service.list_presets():
    try:
        res = service.run_screener(template=t['id'])
        print(f"Template {t['id']} (universe={t.get('universe')}): {len(res)} matches")
        if len(res) > 0:
            print(f"   Sample matches: {[r.symbol for r in res[:5]]}")
    except Exception as e:
        print(f"Template {t['id']}: ERROR {e}")
