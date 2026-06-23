from sqlalchemy import Column, Date, Float, Integer, String, Index
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class OHLCVDaily(Base):
    __tablename__ = "ohlcv_daily"

    id       = Column(Integer, primary_key=True)
    ticker   = Column(String(10), nullable=False, index=True)
    date     = Column(Date, nullable=False)
    open     = Column(Float, nullable=False)
    high     = Column(Float, nullable=False)
    low      = Column(Float, nullable=False)
    close    = Column(Float, nullable=False)
    volume   = Column(Float, nullable=False)
    adj_close = Column(Float, nullable=False)  # use this for returns

    # Composite index: most queries filter by ticker + date range
    __table_args__ = (Index("ix_ohlcv_ticker_date", "ticker", "date"),)