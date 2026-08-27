 """
TRUSTNET - Synthetic Transaction Data Generator
Generates a simulated transactional dataset for testing and development of fraud detection ML and graph models.
All generated records are synthetic and do not represent actual financial transactions.
"""

import os
import random
import uuid
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Ensure repeatable results
random.seed(42)
np.random.seed(42)

# Configurations
NUM_USERS = 1000
NUM_TRANSACTIONS = 15000
START_DATE = datetime(2026, 8, 1, 0, 0, 0)
DAYS_RANGE = 20

# Synthetic files output directory
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "synthetic_transactions.csv")


def generate_user_base():
    """
    Generates a pool of synthetic users, each with a primary device, location,
    and historical transaction amount preferences.
    """
    users = {}
    for i in range(1, NUM_USERS + 1):
        user_id = f"U{i:04d}"
        
        # Primary location (Latitude / Longitude centered around India cities)
        base_lat = random.choice([19.0760, 12.9716, 28.7041, 13.0827])  # Mumbai, Bangalore, Delhi, Chennai
        lat = base_lat + random.uniform(-0.1, 0.1)
        lon = random.choice([72.8777, 77.5946, 77.1025, 80.2707]) + random.uniform(-0.1, 0.1)
        
        users[user_id] = {
            "primary_device": f"D{random.randint(100000, 999999)}",
            "primary_ip": f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
            "location_lat": lat,
            "location_lon": lon,
            "avg_amount": float(np.random.exponential(scale=1500.0) + 100),  # mean ~1600 rupees
            "typical_payment_methods": random.choices(["UPI", "Card", "NetBanking"], weights=[0.6, 0.3, 0.1], k=1)[0]
        }
    return users


def generate_transactions(users):
    """
    Generates a list of transactions containing normal payments and injected fraud scenarios.
    """
    transactions = []
    user_ids = list(users.keys())
    
    # 1. Generate Normal Transactions
    print("Generating normal transactions...")
    for _ in range(int(NUM_TRANSACTIONS * 0.95)):
        sender = random.choice(user_ids)
        receiver = random.choice(user_ids)
        while receiver == sender:
            receiver = random.choice(user_ids)
            
        user_profile = users[sender]
        
        # Amount centered around user's normal average
        amount = max(10.0, np.random.normal(loc=user_profile["avg_amount"], scale=user_profile["avg_amount"] * 0.3))
        amount = round(amount, 2)
        
        # Timestamps spread over the DAYS_RANGE
        delta_seconds = random.randint(0, DAYS_RANGE * 24 * 3600)
        timestamp = START_DATE + timedelta(seconds=delta_seconds)
        
        # Device & IP are usually primary, with small probability of change
        device = user_profile["primary_device"]
        ip = user_profile["primary_ip"]
        lat = user_profile["location_lat"]
        lon = user_profile["location_lon"]
        
        if random.random() < 0.05:  # 5% chance of traveling or changing device
            device = f"D{random.randint(100000, 999999)}"
            ip = f"172.16.{random.randint(1, 254)}.{random.randint(1, 254)}"
            lat += random.uniform(-1.0, 1.0)
            lon += random.uniform(-1.0, 1.0)
            
        payment_method = user_profile["typical_payment_methods"]
        if random.random() < 0.1:  # 10% chance of using non-typical method
            payment_method = random.choice(["UPI", "Card", "NetBanking"])

        transactions.append({
            "transaction_id": f"TX{uuid.uuid4().hex[:10].upper()}",
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": amount,
            "timestamp": timestamp.isoformat(),
            "payment_method": payment_method,
            "device_id": device,
            "ip_address": ip,
            "location_lat": round(lat, 4),
            "location_lon": round(lon, 4),
            "is_fraud_labeled": 0,
            "data_type": "SYNTHETIC_SIMULATION"
        })
        
    # 2. Inject Fraud Scenario: Amount Spikes (Sudden 10x-30x of user avg with new device)
    print("Injecting amount spike fraud transactions...")
    for _ in range(150):
        sender = random.choice(user_ids)
        receiver = random.choice(user_ids)
        while receiver == sender:
            receiver = random.choice(user_ids)
            
        user_profile = users[sender]
        
        # Amount spike: 10x to 30x the user avg, capping at high limit
        amount = round(user_profile["avg_amount"] * random.uniform(10.0, 30.0), 2)
        
        delta_seconds = random.randint(0, DAYS_RANGE * 24 * 3600)
        timestamp = START_DATE + timedelta(seconds=delta_seconds)
        
        # Mismatched device & location
        device = f"D{random.randint(100000, 999999)}"
        ip = f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"
        lat = user_profile["location_lat"] + random.uniform(3.0, 5.0)  # separate city
        lon = user_profile["location_lon"] + random.uniform(3.0, 5.0)
        
        transactions.append({
            "transaction_id": f"TX{uuid.uuid4().hex[:10].upper()}",
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": amount,
            "timestamp": timestamp.isoformat(),
            "payment_method": "UPI",  # UPI commonly targeted
            "device_id": device,
            "ip_address": ip,
            "location_lat": round(lat, 4),
            "location_lon": round(lon, 4),
            "is_fraud_labeled": 1,
            "data_type": "SYNTHETIC_SIMULATION"
        })

    # 3. Inject Fraud Scenario: Rapid Velocity Bursts (Multiple transfers in few minutes)
    print("Injecting velocity burst fraud transactions...")
    for _ in range(30):
        attacker = random.choice(user_ids)
        # Select 5-8 random distinct targets
        targets = random.sample(user_ids, random.randint(5, 8))
        if attacker in targets:
            targets.remove(attacker)
            
        base_time = START_DATE + timedelta(seconds=random.randint(0, DAYS_RANGE * 24 * 3600))
        
        # Same new device/IP (hijacked account pattern)
        attacker_device = f"D{random.randint(100000, 999999)}"
        attacker_ip = f"198.51.100.{random.randint(1, 254)}"
        lat = users[attacker]["location_lat"] + random.uniform(1.0, 2.0)
        lon = users[attacker]["location_lon"] + random.uniform(1.0, 2.0)
        
        for idx, target in enumerate(targets):
            # Short intervals: 1 to 5 minutes apart
            tx_time = base_time + timedelta(minutes=idx * random.randint(1, 5))
            amount = round(random.uniform(2000.0, 8000.0), 2)
            
            transactions.append({
                "transaction_id": f"TX{uuid.uuid4().hex[:10].upper()}",
                "sender_id": attacker,
                "receiver_id": target,
                "amount": amount,
                "timestamp": tx_time.isoformat(),
                "payment_method": "UPI",
                "device_id": attacker_device,
                "ip_address": attacker_ip,
                "location_lat": round(lat, 4),
                "location_lon": round(lon, 4),
                "is_fraud_labeled": 1,
                "data_type": "SYNTHETIC_SIMULATION"
            })

    # 4. Inject Fraud Scenario: Mule-account Fan-In & Sweep out patterns
    # A set of compromised users (senders) transfer money to a mule account,
    # which aggregates it and immediately transfers the total to a master sink.
    print("Injecting mule account network fraud transactions...")
    for m_idx in range(15):  # 15 distinct mule rings
        mule_account = f"U{random.randint(800, 900):04d}"  # Pick user from a certain range
        sink_account = f"U{random.randint(901, NUM_USERS):04d}"
        
        senders = random.sample(user_ids[:700], random.randint(3, 6))
        if mule_account in senders: senders.remove(mule_account)
        if sink_account in senders: senders.remove(sink_account)
        
        base_time = START_DATE + timedelta(seconds=random.randint(0, DAYS_RANGE * 24 * 3600))
        
        total_mule_in = 0.0
        # Step A: Senders pay mule
        for idx, sender in enumerate(senders):
            tx_time = base_time + timedelta(minutes=idx * random.randint(10, 30))
            amount = round(random.uniform(5000.0, 15000.0), 2)
            total_mule_in += amount
            
            transactions.append({
                "transaction_id": f"TX{uuid.uuid4().hex[:10].upper()}",
                "sender_id": sender,
                "receiver_id": mule_account,
                "amount": amount,
                "timestamp": tx_time.isoformat(),
                "payment_method": "NetBanking",
                "device_id": users[sender]["primary_device"],
                "ip_address": users[sender]["primary_ip"],
                "location_lat": users[sender]["location_lat"],
                "location_lon": users[sender]["location_lon"],
                "is_fraud_labeled": 1,  # Mule input
                "data_type": "SYNTHETIC_SIMULATION"
            })
            
        # Step B: Mule sweeps out to sink shortly after
        sweep_time = base_time + timedelta(hours=random.randint(1, 3))
        transactions.append({
            "transaction_id": f"TX{uuid.uuid4().hex[:10].upper()}",
            "sender_id": mule_account,
            "receiver_id": sink_account,
            "amount": round(total_mule_in * 0.98, 2),  # 98% swept out (fees/profit cut)
            "timestamp": sweep_time.isoformat(),
            "payment_method": "NetBanking",
            "device_id": users[mule_account]["primary_device"],
            "ip_address": users[mule_account]["primary_ip"],
            "location_lat": users[mule_account]["location_lat"],
            "location_lon": users[mule_account]["location_lon"],
            "is_fraud_labeled": 1,  # Mule sweep
            "data_type": "SYNTHETIC_SIMULATION"
        })

    return transactions


def main():
    print("=" * 60)
    print("TRUSTNET SYNTHETIC TRANSACTION GENERATOR")
    print("=" * 60)
    
    print(f"Creating user base: {NUM_USERS} users...")
    users = generate_user_base()
    
    print("Generating transaction entries...")
    transactions = generate_transactions(users)
    
    df = pd.DataFrame(transactions)
    
    # Sort by timestamp to make it realistic
    df['timestamp_parsed'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp_parsed').drop(columns=['timestamp_parsed'])
    
    # Save file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    
    print("\nGeneration completed successfully!")
    print(f"Total Transactions Generated: {len(df)}")
    print(f"Total Normal Transactions:    {len(df[df['is_fraud_labeled'] == 0])}")
    print(f"Total Fraud Transactions:     {len(df[df['is_fraud_labeled'] == 1])} ({len(df[df['is_fraud_labeled'] == 1])/len(df)*100:.2f}%)")
    print(f"Saved dataset path:           {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
