from sqlalchemy import desc
from sqlalchemy.orm import Session
from decimal import Decimal
import models, schemas


# ========== Entry Operations ==========

def create_entry(db: Session, entry: schemas.TradeEntryCreate):
    db_entry = models.TradeEntry(
        **entry.model_dump(),
        remaining_qty=entry.qty,
        is_open=True,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


def get_entry(db: Session, entry_id: int):
    return db.query(models.TradeEntry).filter(models.TradeEntry.id == entry_id).first()


def get_entries(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.TradeEntry).order_by(desc(models.TradeEntry.entry_date)).offset(
        skip).limit(limit).all()

def get_closed_entries(db: Session):
    return db.query(models.TradeEntry).filter(models.TradeEntry.is_open == False).all()


# ========== Exit Operations ==========

def create_exit(db: Session, exit: schemas.TradeExitCreate):
    parent_entry = get_entry(db, exit.entry_id)
    if not parent_entry or not parent_entry.is_open:
        raise ValueError("Entry not found or already closed")

    if parent_entry.remaining_qty < exit.exit_qty:
        raise ValueError("Exit quantity exceeds remaining position")

    db_exit = models.TradeExit(
        entry_id=exit.entry_id,
        exit_date=exit.exit_date,
        exit_price=exit.exit_price,
        exit_qty=exit.exit_qty
    )
    db.add(db_exit)

    # Update entry state
    parent_entry.remaining_qty -= exit.exit_qty
    if parent_entry.remaining_qty == 0:
        parent_entry.is_open = False

    db.commit()
    db.refresh(db_exit)
    return db_exit


def get_exit(db: Session, exit_id: int):
    return db.query(models.TradeExit).filter(models.TradeExit.id == exit_id).first()


def get_exits_for_entry(db: Session, entry_id: int):
    return db.query(models.TradeExit).filter(models.TradeExit.entry_id == entry_id).all()
