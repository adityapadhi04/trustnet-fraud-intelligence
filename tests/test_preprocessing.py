"""
TRUSTNET - Preprocessing and Data Engine Test Suite
Tests for data generator and feature preprocessing pipeline.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from machine_learning.src.preprocessing.pipeline import (
    haversine_distance,
    load_data,
    extract_features
)


def test_haversine_distance():
    """
    Test that Haversine distance correctly calculates geographical separation in km.
    Reference: Mumbai (19.0760, 72.8777) to Bangalore (12.9716, 77.5946) is ~840 km.
    """
    mumbai_lat, mumbai_lon = 19.0760, 72.8777
    bangalore_lat, bangalore_lon = 12.9716, 77.5946
    
    distance = haversine_distance(mumbai_lat, mumbai_lon, bangalore_lat, bangalore_lon)
    
    # Distance should be close to 840 km (with tolerance)
    assert pytest.approx(distance, abs=20) == 840.0
    
    # Same point should yield 0.0 distance
    assert haversine_distance(mumbai_lat, mumbai_lon, mumbai_lat, mumbai_lon) == 0.0


def test_cold_start_and_running_profile():
    """
    Tests cold start (first transaction) and subsequent running profile calculation.
    """
    data = {
        "transaction_id": ["TX1", "TX2", "TX3"],
        "sender_id": ["U0001", "U0001", "U0001"],
        "receiver_id": ["U0002", "U0002", "U0003"],
        "amount": [100.0, 200.0, 150.0],
        "device_id": ["D1", "D1", "D1"],
        "ip_address": ["192.168.1.1", "192.168.1.1", "192.168.1.1"],
        "location_lat": [12.9, 12.9, 12.9],
        "location_lon": [77.5, 77.5, 77.5],
        "timestamp": [
            datetime(2026, 8, 1, 10, 0),
            datetime(2026, 8, 1, 11, 0),
            datetime(2026, 8, 1, 12, 0)
        ],
        "payment_method": ["UPI", "UPI", "UPI"],
        "is_fraud_labeled": [0, 0, 0]
    }
    df = pd.DataFrame(data)
    
    df_features = extract_features(df)
    
    # Cold start check: First transaction amount_deviation and location_deviation_km must be NaN
    assert np.isnan(df_features.loc[0, "amount_deviation"])
    assert np.isnan(df_features.loc[0, "location_deviation_km"])
    assert df_features.loc[0, "is_new_device"] == 0
    assert df_features.loc[0, "is_new_ip"] == 0
    
    # Transaction 2 check:
    # Baseline mean amount before TX2 is TX1 amount = 100.0
    # TX2 amount is 200.0, so amount_deviation = 200 / 100 = 2.0
    assert df_features.loc[1, "amount_deviation"] == 2.0
    assert df_features.loc[1, "is_new_device"] == 0
    
    # Transaction 3 check:
    # Baseline mean before TX3 is (100.0 + 200.0) / 2 = 150.0
    # TX3 amount is 150.0, so amount_deviation = 150 / 150 = 1.0
    assert df_features.loc[2, "amount_deviation"] == 1.0


def test_lookahead_leakage_prevention():
    """
    Validation Test: Future transactions must NOT affect features computed for prior transactions.
    """
    # Dataset A: Only Transaction 1 and 2
    data_a = {
        "transaction_id": ["TX1", "TX2"],
        "sender_id": ["U0001", "U0001"],
        "receiver_id": ["U0002", "U0002"],
        "amount": [1000.0, 1000.0],
        "device_id": ["D1", "D1"],
        "ip_address": ["192.168.1.1", "192.168.1.1"],
        "location_lat": [12.9, 12.9],
        "location_lon": [77.5, 77.5],
        "timestamp": [
            datetime(2026, 8, 1, 10, 0),
            datetime(2026, 8, 1, 11, 0)
        ],
        "payment_method": ["UPI", "UPI"],
        "is_fraud_labeled": [0, 0]
    }
    df_a = pd.DataFrame(data_a)
    features_a = extract_features(df_a)
    
    # Dataset B: Transaction 1, 2 AND a future Transaction 3 with a massive spike
    data_b = {
        "transaction_id": ["TX1", "TX2", "TX3"],
        "sender_id": ["U0001", "U0001", "U0001"],
        "receiver_id": ["U0002", "U0002", "U0003"],
        "amount": [1000.0, 1000.0, 50000.0],  # Spike
        "device_id": ["D1", "D1", "D1"],
        "ip_address": ["192.168.1.1", "192.168.1.1", "192.168.1.1"],
        "location_lat": [12.9, 12.9, 12.9],
        "location_lon": [77.5, 77.5, 77.5],
        "timestamp": [
            datetime(2026, 8, 1, 10, 0),
            datetime(2026, 8, 1, 11, 0),
            datetime(2026, 8, 1, 12, 0)  # Future transaction
        ],
        "payment_method": ["UPI", "UPI", "UPI"],
        "is_fraud_labeled": [0, 0, 1]
    }
    df_b = pd.DataFrame(data_b)
    features_b = extract_features(df_b)
    
    # Compare features for TX1 and TX2 across both datasets
    for col in ["amount_deviation", "is_new_device", "location_deviation_km", "velocity_1h", "velocity_24h", "recipient_in_degree"]:
        val_a1 = features_a.loc[0, col]
        val_b1 = features_b.loc[0, col]
        val_a2 = features_a.loc[1, col]
        val_b2 = features_b.loc[1, col]
        
        # Test Transaction 1 features remain identical
        if pd.isna(val_a1):
            assert pd.isna(val_b1)
        else:
            assert val_a1 == val_b1
            
        # Test Transaction 2 features remain identical
        if pd.isna(val_a2):
            assert pd.isna(val_b2)
        else:
            assert val_a2 == val_b2


def test_velocity_boundaries():
    """
    Tests that current transaction is excluded from historical velocity,
    and future transactions are excluded.
    """
    data = {
        "transaction_id": ["TX1", "TX2", "TX3"],
        "sender_id": ["U0001", "U0001", "U0001"],
        "receiver_id": ["U0002", "U0003", "U0004"],
        "amount": [100.0, 100.0, 100.0],
        "device_id": ["D1", "D1", "D1"],
        "ip_address": ["192.168.1.1", "192.168.1.1", "192.168.1.1"],
        "location_lat": [12.9, 12.9, 12.9],
        "location_lon": [77.5, 77.5, 77.5],
        "timestamp": [
            datetime(2026, 8, 1, 12, 0),  # TX1
            datetime(2026, 8, 1, 12, 10), # TX2 (10 mins later)
            datetime(2026, 8, 1, 13, 30)  # TX3 (90 mins later)
        ],
        "payment_method": ["UPI", "UPI", "UPI"],
        "is_fraud_labeled": [0, 0, 0]
    }
    df = pd.DataFrame(data)
    features = extract_features(df)
    
    # TX1: velocity_1h must be 0 (current TX not counted)
    assert features.loc[0, "velocity_1h"] == 0
    
    # TX2: velocity_1h must be 1 (only TX1 is counted, TX2 excluded, future TX3 excluded)
    assert features.loc[1, "velocity_1h"] == 1
    
    # TX3: velocity_1h must be 0 (TX1 and TX2 are older than 1 hour, TX3 excluded)
    assert features.loc[2, "velocity_1h"] == 0
    # TX3: velocity_24h must be 2 (TX1 and TX2 are within 24 hours)
    assert features.loc[2, "velocity_24h"] == 2


def test_device_and_ip_anomaly_detection():
    """
    Verify device and IP anomalies calculate against historical values.
    """
    data = {
        "transaction_id": ["TX1", "TX2", "TX3"],
        "sender_id": ["U0001", "U0001", "U0001"],
        "receiver_id": ["U0002", "U0003", "U0004"],
        "amount": [100.0, 100.0, 100.0],
        "device_id": ["D1", "D1", "D2"],    # D2 is new at TX3
        "ip_address": ["192.168.1.1", "10.0.0.1", "192.168.1.1"], # 10.0.0.1 is new at TX2
        "location_lat": [12.9, 12.9, 12.9],
        "location_lon": [77.5, 77.5, 77.5],
        "timestamp": [
            datetime(2026, 8, 1, 10, 0),
            datetime(2026, 8, 1, 11, 0),
            datetime(2026, 8, 1, 12, 0)
        ],
        "payment_method": ["UPI", "UPI", "UPI"],
        "is_fraud_labeled": [0, 0, 0]
    }
    df = pd.DataFrame(data)
    features = extract_features(df)
    
    # TX1: Cold start, both flags 0
    assert features.loc[0, "is_new_device"] == 0
    assert features.loc[0, "is_new_ip"] == 0
    
    # TX2: device is D1 (seen before) -> 0; IP is 10.0.0.1 (not seen before) -> 1
    assert features.loc[1, "is_new_device"] == 0
    assert features.loc[1, "is_new_ip"] == 1
    
    # TX3: device is D2 (not seen before) -> 1; IP is 192.168.1.1 (seen at TX1) -> 0
    assert features.loc[2, "is_new_device"] == 1
    assert features.loc[2, "is_new_ip"] == 0


def test_chronological_network_degree():
    """
    Checks that recipient in-degree and sender out-degree are calculated chronologically.
    """
    data = {
        "transaction_id": ["TX1", "TX2", "TX3"],
        "sender_id": ["U0001", "U0002", "U0001"],
        "receiver_id": ["U0003", "U0003", "U0004"],
        "amount": [100.0, 100.0, 100.0],
        "device_id": ["D1", "D1", "D1"],
        "ip_address": ["192.168.1.1", "192.168.1.1", "192.168.1.1"],
        "location_lat": [12.9, 12.9, 12.9],
        "location_lon": [77.5, 77.5, 77.5],
        "timestamp": [
            datetime(2026, 8, 1, 10, 0),  # U0001 -> U0003
            datetime(2026, 8, 1, 11, 0),  # U0002 -> U0003
            datetime(2026, 8, 1, 12, 0)   # U0001 -> U0004
        ],
        "payment_method": ["UPI", "UPI", "UPI"],
        "is_fraud_labeled": [0, 0, 0]
    }
    df = pd.DataFrame(data)
    features = extract_features(df)
    
    # TX1: receiver U0003 has received from 0 users previously.
    assert features.loc[0, "recipient_in_degree"] == 0
    
    # TX2: receiver U0003 has received from 1 user (U0001) previously.
    assert features.loc[1, "recipient_in_degree"] == 1
    
    # TX3: sender U0001 has sent to 1 receiver (U0003) previously.
    assert features.loc[2, "sender_out_degree"] == 1


def test_unsorted_input():
    """
    Verifies that pipeline sorts transaction records chronologically before feature extraction.
    """
    data = {
        "transaction_id": ["TX3", "TX1", "TX2"],
        "sender_id": ["U0001", "U0001", "U0001"],
        "receiver_id": ["U0004", "U0002", "U0003"],
        "amount": [150.0, 100.0, 200.0],
        "device_id": ["D1", "D1", "D1"],
        "ip_address": ["192.168.1.1", "192.168.1.1", "192.168.1.1"],
        "location_lat": [12.9, 12.9, 12.9],
        "location_lon": [77.5, 77.5, 77.5],
        "timestamp": [
            datetime(2026, 8, 1, 12, 0),  # TX3 (latest)
            datetime(2026, 8, 1, 10, 0),  # TX1 (earliest)
            datetime(2026, 8, 1, 11, 0)   # TX2 (middle)
        ],
        "payment_method": ["UPI", "UPI", "UPI"],
        "is_fraud_labeled": [0, 0, 0]
    }
    df = pd.DataFrame(data)
    
    # The pipeline should sort: TX1 -> TX2 -> TX3
    df_features = extract_features(df)
    
    # Verify chronological sorting order in output
    assert df_features.loc[0, "transaction_id"] == "TX1"
    assert df_features.loc[1, "transaction_id"] == "TX2"
    assert df_features.loc[2, "transaction_id"] == "TX3"
    
    # Mean before TX2 is 100. TX2 amount is 200. Deviation should be 2.0.
    assert df_features.loc[1, "amount_deviation"] == 2.0
