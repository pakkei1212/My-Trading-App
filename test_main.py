# test_main.py
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from main import app, get_db

# Use a test database (SQLite in-memory)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test DB schema
Base.metadata.create_all(bind=engine)

# Override DB dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def test_create_entry():
    response = client.post("/entries", json={
        "stock": "9988",
        "market": "HK",
        "position": "Long",
        "entry_date": "2024-01-01",
        "entry_price": 100.0,
        "qty": 1000,
        "stop_loss_price": 90.0,
        "target_price": 120.0
    })
    assert response.status_code == 200
    data = response.json()
    assert data["stock"] == "9988"
    assert data["remaining_qty"] == 1000
    assert data["is_open"] is True

def test_partial_exit():
    # Add exit
    response = client.post("/exits", json={
        "entry_id": 1,
        "exit_date": "2024-01-10",
        "exit_price": 110.0,
        "exit_qty": 500
    })
    assert response.status_code == 200
    data = response.json()
    assert data["exit_qty"] == 500

    # Confirm entry is partially open
    entry = client.get("/entries/1").json()
    assert entry["remaining_qty"] == 500
    assert entry["is_open"] is True

def test_final_exit_closes_entry():
    # Add second exit to close trade
    response = client.post("/exits", json={
        "entry_id": 1,
        "exit_date": "2024-01-15",
        "exit_price": 120.0,
        "exit_qty": 500
    })
    assert response.status_code == 200

    # Confirm entry is now closed
    entry = client.get("/entries/1").json()
    assert entry["remaining_qty"] == 0
    assert entry["is_open"] is False
    assert len(entry["exits"]) == 2

