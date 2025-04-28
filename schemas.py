from pydantic import BaseModel, condecimal
from typing import Optional, List, Literal
from datetime import date


# ========== Exit Schema ==========
class TradeExitBase(BaseModel):
    exit_date: date
    exit_price: condecimal(max_digits=10, decimal_places=2)
    exit_qty: int

class TradeExitCreate(TradeExitBase):
    entry_id: int  # ID of the trade being closed

class TradeExitResponse(TradeExitBase):
    id: int
    entry_id: int

    class Config:
        orm_mode = True


# ========== Entry Schema ==========
class TradeEntryBase(BaseModel):
    stock: str
    market: str
    position: Literal["Long", "Short"]
    entry_date: date
    entry_price: condecimal(max_digits=10, decimal_places=2)
    qty: int
    stop_loss_price: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    target_price: Optional[condecimal(max_digits=10, decimal_places=2)] = None

class TradeEntryCreate(TradeEntryBase):
    pass

class TradeEntryResponse(TradeEntryBase):
    id: int
    remaining_qty: int
    is_open: bool
    exits: List[TradeExitResponse] = []

    # ✅ Add these explicitly
    expected_loss_pct: Optional[float] = None
    expected_gain_pct: Optional[float] = None
    rr_ratio: Optional[float] = None
    actual_gain_loss_pct: Optional[float] = None
    actual_gain_loss: Optional[float] = None
    holding_days: Optional[int] = None
    total_cost: Optional[float] = None

    class Config:
        orm_mode = True



