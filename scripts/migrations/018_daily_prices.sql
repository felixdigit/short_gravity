-- Migration 018: Daily stock prices
-- Stores OHLCV data from yfinance for price-based analysis.
-- Backfilled by price_worker.py, updated daily.

CREATE TABLE IF NOT EXISTS daily_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL DEFAULT 'ASTS',
    date DATE NOT NULL,
    open NUMERIC(12,4),
    high NUMERIC(12,4),
    low NUMERIC(12,4),
    close NUMERIC(12,4) NOT NULL,
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date
    ON daily_prices(symbol, date);

ALTER TABLE daily_prices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Daily prices are publicly readable"
    ON daily_prices FOR SELECT
    USING (true);

CREATE POLICY "Service role can manage daily prices"
    ON daily_prices FOR ALL
    USING (auth.role() = 'service_role');

COMMENT ON TABLE daily_prices IS 'OHLCV daily stock prices from yfinance. Primary use: voice accuracy scoring against real price movements.';
