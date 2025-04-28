from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import schemas, crud
from database import SessionLocal, engine, Base
from utils import compute_derived_fields

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Trading Journal API")

# Dependency: Get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== Root ==========
@app.get("/")
def root():
    return {"message": "Welcome to the Two-Table Trading Journal API"}


# ========== Entry Routes ==========

@app.post("/entries", response_model=schemas.TradeEntryResponse)
def create_trade_entry(entry: schemas.TradeEntryCreate, db: Session = Depends(get_db)):
    return crud.create_entry(db, entry)

@app.get("/entries", response_model=List[schemas.TradeEntryResponse])
def get_all_entries(db: Session = Depends(get_db)):
    entries = crud.get_entries(db)
    return [compute_derived_fields(e) for e in entries]

@app.get("/entries/closed", response_model=List[schemas.TradeEntryResponse])
def get_closed_entries(db: Session = Depends(get_db)):
    entries = crud.get_closed_entries(db)
    return [compute_derived_fields(e) for e in entries]

@app.get("/entries/{entry_id}", response_model=schemas.TradeEntryResponse)
def get_single_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = crud.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return compute_derived_fields(entry)

# ========== Exit Routes ==========

@app.post("/exits", response_model=schemas.TradeExitResponse)
def create_exit(exit: schemas.TradeExitCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_exit(db, exit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/exits/{exit_id}", response_model=schemas.TradeExitResponse)
def get_exit_by_id(exit_id: int, db: Session = Depends(get_db)):
    exit = crud.get_exit(db, exit_id)
    if not exit:
        raise HTTPException(status_code=404, detail="Exit not found")
    return exit
