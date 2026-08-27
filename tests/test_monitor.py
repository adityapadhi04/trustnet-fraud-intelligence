"""
TRUSTNET - Live Transaction Stream Simulator Test Suite
Verifies cursor sequencing, status metrics, loop safety, alert integration, and duplicate prevention.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.routes.monitor import monitor_state
from backend.app.routes.alerts import AlertsStore, _db_lock

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_monitor_each_test():
    """Fixture to ensure monitor state is reset before/after each test execution."""
    monitor_state.reset()
    yield
    monitor_state.reset()


def test_monitor_status_initial():
    """Verify live status endpoint initial metrics reporting."""
    response = client.get("/api/v1/monitor/status")
    assert response.status_code == 200
    data = response.json()
    assert data["online"] is True
    assert data["transactions_processed"] == 0
    assert data["last_transaction_time"] is None
    assert data["high_risk_count"] == 0
    assert isinstance(data["alert_count"], int)


def test_monitor_next_sequential_progression():
    """Verify sequence progression and metrics accumulation across sequential calls."""
    # 1. Fetch first transaction
    res1 = client.get("/api/v1/monitor/next")
    assert res1.status_code == 200
    d1 = res1.json()
    assert "transaction" in d1
    assert "analysis" in d1
    assert d1["sequence_number"] == 1
    assert d1["timestamp"] is not None

    # 2. Verify status metrics updated
    status_res1 = client.get("/api/v1/monitor/status")
    s_d1 = status_res1.json()
    assert s_d1["transactions_processed"] == 1
    assert s_d1["last_transaction_time"] == d1["timestamp"]

    # 3. Fetch second transaction
    res2 = client.get("/api/v1/monitor/next")
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["sequence_number"] == 2
    assert d2["transaction"]["transaction_id"] != d1["transaction"]["transaction_id"]

    # 4. Verify count incremented to 2
    status_res2 = client.get("/api/v1/monitor/status")
    assert status_res2.json()["transactions_processed"] == 2


def test_monitor_loop_safety():
    """Verify stream loops back to the start when reaching the end of the transaction dataset."""
    from backend.app.models_loader import get_transactions_df
    df = get_transactions_df()
    total_len = len(df)

    # Force cursor position to the last item
    with monitor_state.lock:
        monitor_state.cursor = total_len - 1

    # Fetch last transaction
    res_last = client.get("/api/v1/monitor/next")
    assert res_last.status_code == 200
    assert res_last.json()["sequence_number"] == total_len

    # Next fetch should loop back to the first transaction (sequence_number = 1)
    res_loop = client.get("/api/v1/monitor/next")
    assert res_loop.status_code == 200
    assert res_loop.json()["sequence_number"] == 1


def test_monitor_alert_generation_and_duplicate_prevention():
    """Verify alerts are correctly created for risky transactions and duplicate alerts are prevented on loops."""
    # Find a transaction that triggers risk score >= 40.0
    # We will step through transactions until we find one, or force-run.
    # Let's run a loop to fetch next transactions until we get one with risk score >= 40.
    found_risky = False
    tx_id = None
    risk_score = None
    
    for _ in range(50):  # scan up to 50 items
        res = client.get("/api/v1/monitor/next")
        data = res.json()
        if data["analysis"]["risk_score"] >= 40.0:
            found_risky = True
            tx_id = data["transaction"]["transaction_id"]
            risk_score = data["analysis"]["risk_score"]
            seq_num = data["sequence_number"]
            break

    if not found_risky:
        pytest.skip("No transaction with risk score >= 40.0 found in first 50 dataset records.")

    # Check alert exists in AlertsStore database
    alert_id = f"ALT-{tx_id}"
    with _db_lock:
        db = AlertsStore.load_all()
    assert alert_id in db
    assert db[alert_id]["risk_score"] == risk_score

    initial_alert_count = len(db)

    # Force cursor back to the same index to simulate a loop encounter of this exact transaction
    with monitor_state.lock:
        monitor_state.cursor = seq_num - 1

    # Request the same transaction again
    res_dup = client.get("/api/v1/monitor/next")
    assert res_dup.status_code == 200
    assert res_dup.json()["transaction"]["transaction_id"] == tx_id

    # Verify that alert was updated but no duplicate alert item was created
    with _db_lock:
        db_after = AlertsStore.load_all()
    assert len(db_after) == initial_alert_count
    assert alert_id in db_after


def test_reports_timeline_integration():
    """Verify that reports endpoints successfully aggregate transaction_timeline and alert_timeline."""
    response = client.get("/api/v1/reports/summary")
    assert response.status_code == 200
    data = response.json()
    
    # Assert timeline keys exist
    assert "transaction_timeline" in data
    assert "alert_timeline" in data
    
    # Assert they are lists of date-count dicts
    assert isinstance(data["transaction_timeline"], list)
    assert isinstance(data["alert_timeline"], list)
    assert len(data["transaction_timeline"]) > 0
    
    first_item = data["transaction_timeline"][0]
    assert "date" in first_item
    assert "count" in first_item


def test_monitor_demo_mode_execution():
    """Verify that when demo_mode is True, every 5th transaction is a CRITICAL demo event."""
    # 1. Enable demo mode
    res_enable = client.post("/api/v1/monitor/demo_mode", json={"demo_mode": True})
    assert res_enable.status_code == 200
    assert res_enable.json()["demo_mode"] is True
    
    # 2. Get demo_mode state
    res_get = client.get("/api/v1/monitor/demo_mode")
    assert res_get.status_code == 200
    assert res_get.json()["demo_mode"] is True

    # 3. Reset transactions_processed to 0 for controlled counting
    with monitor_state.lock:
        monitor_state.transactions_processed = 0
        
    # Process 4 normal transactions
    for i in range(4):
        res = client.get("/api/v1/monitor/next")
        assert res.status_code == 200
        assert res.json().get("demo_event") is False

    # The 5th transaction must be a demo event
    res_5th = client.get("/api/v1/monitor/next")
    assert res_5th.status_code == 200
    data_5th = res_5th.json()
    assert data_5th.get("demo_event") is True
    assert data_5th["analysis"]["risk_level"] == "CRITICAL"
    assert data_5th["analysis"]["risk_score"] >= 90.0
    
    # 4. Disable demo mode and verify normal behavior
    res_disable = client.post("/api/v1/monitor/demo_mode", json={"demo_mode": False})
    assert res_disable.status_code == 200
    assert res_disable.json()["demo_mode"] is False
