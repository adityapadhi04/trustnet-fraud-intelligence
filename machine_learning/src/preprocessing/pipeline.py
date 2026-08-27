"""
TRUSTNET - Machine Learning Preprocessing Pipeline
Contains modules to load raw synthetic data and engineer transaction-level and
network-level risk features chronologically, preventing look-ahead data leakage.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def load_data(filepath: str) -> pd.DataFrame:
    """
    Loads raw transaction CSV data, parses timestamps, and sorts chronologically.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Raw data file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    return df


def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """
    Calculates the great-circle distance between two points on the Earth
    in kilometers using their latitude and longitude.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
    c = 2.0 * np.arcsin(np.sqrt(a))
    r = 6371.0  # Radius of Earth in kilometers
    return float(c * r)


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineers transaction-level features and running network graph indicators.
    Enforces strict chronological feature calculations:
    For any transaction, features are computed using ONLY the state derived from 
    transactions strictly prior to the current transaction.
    """
    # Sort chronologically to prevent any look-ahead leakage
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    features = []
    
    # Running state trackers for user profiles
    # user_id -> {transaction_count, cumulative_amount, home_lat_sum, home_lon_sum, known_devices, known_ips}
    user_profiles = {}
    
    # Running state trackers for velocity
    # user_id -> list of timestamps
    sender_tx_timestamps = {}
    
    # Running state trackers for network degrees
    # user_id -> set of sender_ids (who sent to this user)
    receiver_unique_senders = {}
    # user_id -> set of receiver_ids (who received from this user)
    receiver_unique_receivers = {}
    
    for idx, row in df.iterrows():
        sender = row["sender_id"]
        receiver = row["receiver_id"]
        amount = row["amount"]
        t_time = row["timestamp"]
        device = row["device_id"]
        ip = row["ip_address"]
        lat = row["location_lat"]
        lon = row["location_lon"]
        
        # ---------------------------------------------------------
        # STEP 1: CALCULATE BEHAVIORAL PROFILE FEATURES
        # ---------------------------------------------------------
        if sender not in user_profiles:
            # Cold-start User: No previous transactions exist.
            # Represent deviation metrics as NaN since no historical baseline exists.
            # This is standard for tree-based models (like XGBoost) which can split
            # on NaN values natively, or can be imputed cleanly.
            amount_deviation = np.nan
            is_new_device = 0
            is_new_ip = 0
            location_deviation = np.nan
        else:
            profile = user_profiles[sender]
            count = profile["transaction_count"]
            
            # Amount deviation: current amount compared to the running historical average
            running_mean_amount = profile["cumulative_amount"] / count
            amount_deviation = amount / running_mean_amount if running_mean_amount > 0 else 1.0
            
            # Device and IP deviations: compared against sets of known historical identifiers
            is_new_device = 1 if device not in profile["known_devices"] else 0
            is_new_ip = 1 if ip not in profile["known_ips"] else 0
            
            # Location deviation: Haversine distance from historical mean coordinates
            running_mean_lat = profile["home_lat_sum"] / count
            running_mean_lon = profile["home_lon_sum"] / count
            location_deviation = haversine_distance(lat, lon, running_mean_lat, running_mean_lon)
            
        # ---------------------------------------------------------
        # STEP 2: CALCULATE VELOCITY FEATURES
        # ---------------------------------------------------------
        # Excludes the current transaction (calculated BEFORE adding current timestamp)
        history = sender_tx_timestamps.get(sender, [])
        twenty_four_hours_ago = t_time - timedelta(days=1)
        one_hour_ago = t_time - timedelta(hours=1)
        
        # Filter window to include only events within last 24h
        history = [t for t in history if t > twenty_four_hours_ago]
        sender_tx_timestamps[sender] = history
        
        velocity_24h = len(history)
        velocity_1h = len([t for t in history if t > one_hour_ago])
        
        # ---------------------------------------------------------
        # STEP 3: CALCULATE NETWORK DEGREE FEATURES
        # ---------------------------------------------------------
        # Excludes the current transaction (calculated BEFORE adding current nodes)
        recipient_in_degree = len(receiver_unique_senders.get(receiver, set()))
        sender_out_degree = len(receiver_unique_receivers.get(sender, set()))
        
        # ---------------------------------------------------------
        # STEP 4: EXTRACT TEMPORAL FEATURES
        # ---------------------------------------------------------
        hour_of_day = t_time.hour
        day_of_week = t_time.weekday()
        
        # ---------------------------------------------------------
        # STEP 5: SAVE CALCULATED FEATURES
        # ---------------------------------------------------------
        features.append({
            "transaction_id": row["transaction_id"],
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": amount,
            "timestamp": row["timestamp"],
            "payment_method": row["payment_method"],
            "amount_deviation": round(amount_deviation, 4) if not pd.isna(amount_deviation) else np.nan,
            "is_new_device": is_new_device,
            "is_new_ip": is_new_ip,
            "location_deviation_km": round(location_deviation, 4) if not pd.isna(location_deviation) else np.nan,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "velocity_1h": velocity_1h,
            "velocity_24h": velocity_24h,
            "recipient_in_degree": recipient_in_degree,
            "sender_out_degree": sender_out_degree,
            "is_fraud_labeled": row["is_fraud_labeled"]
        })
        
        # ---------------------------------------------------------
        # STEP 6: UPDATE HISTORICAL STATE TRACKERS
        # ---------------------------------------------------------
        # Current transaction becomes history for the NEXT transactions
        
        # A. Update User Profiles
        if sender not in user_profiles:
            user_profiles[sender] = {
                "transaction_count": 0,
                "cumulative_amount": 0.0,
                "home_lat_sum": 0.0,
                "home_lon_sum": 0.0,
                "known_devices": set(),
                "known_ips": set()
            }
        
        prof = user_profiles[sender]
        prof["transaction_count"] += 1
        prof["cumulative_amount"] += amount
        prof["home_lat_sum"] += lat
        prof["home_lon_sum"] += lon
        prof["known_devices"].add(device)
        prof["known_ips"].add(ip)
        
        # B. Update Velocity Timestamps
        if sender not in sender_tx_timestamps:
            sender_tx_timestamps[sender] = []
        sender_tx_timestamps[sender].append(t_time)
        
        # C. Update Graph Degrees
        receiver_unique_senders.setdefault(receiver, set()).add(sender)
        receiver_unique_receivers.setdefault(sender, set()).add(receiver)
        
    return pd.DataFrame(features)


def preprocess_pipeline(raw_filepath: str, output_filepath: str):
    """
    Executes the complete preprocessing pipeline.
    Loads raw data, extracts features, and saves the engineered feature CSV.
    """
    print(f"Loading raw transaction data from {raw_filepath}...")
    df = load_data(raw_filepath)
    
    print("Engineering behavior and network graph features chronologically...")
    df_features = extract_features(df)
    
    print(f"Saving engineered feature matrix to {output_filepath}...")
    df_features.to_csv(output_filepath, index=False)
    print("Preprocessing completed successfully!")


if __name__ == "__main__":
    # If run directly, preprocess the synthetic datasets
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    raw_path = os.path.join(base_dir, "datasets", "synthetic_transactions.csv")
    output_path = os.path.join(base_dir, "datasets", "processed_features.csv")
    
    if os.path.exists(raw_path):
        preprocess_pipeline(raw_path, output_path)
    else:
        print(f"Raw data file not found: {raw_path}")
