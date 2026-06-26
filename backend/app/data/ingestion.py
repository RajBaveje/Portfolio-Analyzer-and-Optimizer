import logging
from datetime import datetime
import pandas as pd
import numpy as np
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.ohlcv import OHLCVDaily

# Technical Analysis Library 
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands

logger = logging.getLogger("data_ingestion")
logging.basicConfig(level=logging.INFO)

# Step 2.2: Universe selection
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "JPM", "GS", "BAC",
    "JNJ", "UNH", "PFE",
    "PG", "KO", "WMT",
    "XOM", "CAT", "HON",
    "TLT", "GLD"
]

class DataIngestionService:
    @staticmethod
    def fetch_historical_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Extracts historical market data via yfinance and flattens multi-indexes 
        to ensure robust parsing. Caches locally automatically.
        """
        logger.info(f"Extracting historical market data for {ticker} from {start_date} to {end_date}")
        
        df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True)
        
        if df.empty:
            logger.warning(f"No historical price records returned for ticker: {ticker}")
            return pd.DataFrame()
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df

    @staticmethod
    def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Step 2.4 technical indicators cleanly without lookahead bias.
        """
        if df.empty:
            return df
            
        df = df.copy()
        
        close_series = df['Close']
        
        # RSI(14)
        df['rsi'] = RSIIndicator(close=close_series, window=14).rsi()
        
        # MACD(12,26,9) Histogram
        macd_init = MACD(close=close_series, window_fast=12, window_slow=26, window_sign=9)
        df['macd_hist'] = macd_init.macd_diff()
        
        # Bollinger Bands(20,2)
        bb_init = BollingerBands(close=close_series, window=20, window_dev=2)
        df['bb_pct'] = bb_init.bollinger_pband()
        
        # Rolling 20-day realized volatility (Annualized standard deviation of daily returns)
        daily_returns = close_series.pct_change()
        df['rolling_vol_20'] = daily_returns.rolling(window=20).std() * np.sqrt(252)
        
        # Rolling 60-day return (Medium-term momentum)
        df['rolling_return_60'] = close_series.pct_change(periods=60)
        
        # Drop Early Rows entirely 
        df = df.dropna()
        
        return df

    @classmethod
    def normalize_and_save(cls, db: Session, ticker: str, df: pd.DataFrame) -> int:
        """
        Normalizes raw market data, appends technical indicators, 
        and executes an optimized atomic batch upsert.
        """
        if df.empty:
            return 0

        df_with_features = cls.compute_technical_indicators(df)
        records_to_upsert = []

        for timestamp, row in df_with_features.iterrows():
            record_date = timestamp.date() if isinstance(timestamp, pd.Timestamp) else timestamp

            records_to_upsert.append({
                "ticker": ticker.upper(),
                "date": record_date,
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                # adj_close uses Close because auto_adjust=True handles adjustment factors directly
                "adj_close": float(row['Close']), 
                "volume": int(row['Volume']) if pd.notna(row['Volume']) else 0
            })

        if not records_to_upsert:
            return 0

        stmt = insert(OHLCVDaily).values(records_to_upsert)
        
        update_dict = {
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "adj_close": stmt.excluded.adj_close,
            "volume": stmt.excluded.volume
        }
        
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['ticker', 'date'],
            set_=update_dict
        )

        db.execute(upsert_stmt)
        db.commit()
        
        logger.info(f"Successfully processed features and upserted {len(records_to_upsert)} rows for {ticker}")
        return len(records_to_upsert)