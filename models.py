from sqlalchemy import Column, Integer, String, Enum, Date, DECIMAL, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class TradeEntry(Base):
    __tablename__ = "trade_entries"

    id = Column(Integer, primary_key=True, index=True)
    stock = Column(String(10), nullable=False)
    market = Column(String(10), nullable=False)
    position = Column(Enum("Long", "Short"), nullable=False)
    entry_date = Column(Date, nullable=False)
    entry_price = Column(DECIMAL(10, 2), nullable=False)
    qty = Column(Integer, nullable=False)
    remaining_qty = Column(Integer, nullable=False)
    stop_loss_price = Column(DECIMAL(10, 2))
    target_price = Column(DECIMAL(10, 2))
    is_open = Column(Boolean, default=True)

    exits = relationship("TradeExit", back_populates="entry")


class TradeExit(Base):
    __tablename__ = "trade_exits"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("trade_entries.id"), nullable=False)
    exit_date = Column(Date, nullable=False)
    exit_price = Column(DECIMAL(10, 2), nullable=False)
    exit_qty = Column(Integer, nullable=False)

    entry = relationship("TradeEntry", back_populates="exits")
