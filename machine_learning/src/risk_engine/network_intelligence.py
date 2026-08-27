"""
TRUSTNET - Network Intelligence Engine
Calculates graph-based features, detects suspicious mule account flow patterns,
and computes a deterministic, explainable network risk score from 0-100.
All computations are strictly independent of the ground truth target label (is_fraud_labeled).
"""

import networkx as nx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Set, Tuple, Optional

class NetworkIntelligenceEngine:
    """
    Constructs and analyzes the directed transaction graph using NetworkX
    to flag anomalies, calculate network risk, and identify potential mule patterns.
    """
    
    def __init__(self, transactions_df: pd.DataFrame):
        self.df = transactions_df.copy()
        
        # Ensure timestamp is datetime type
        self.df["timestamp"] = pd.to_datetime(self.df["timestamp"])
        
        # Build the global transaction graph
        self.G = nx.MultiDiGraph()
        
        # Add all transactions as directed edges
        for _, row in self.df.iterrows():
            sender = str(row["sender_id"])
            receiver = str(row["receiver_id"])
            self.G.add_edge(
                sender,
                receiver,
                transaction_id=str(row["transaction_id"]),
                amount=float(row["amount"]),
                timestamp=row["timestamp"],
                is_new_device=int(row.get("is_new_device", 0)),
                is_new_ip=int(row.get("is_new_ip", 0)),
                amount_deviation=float(row["amount_deviation"]) if pd.notna(row.get("amount_deviation")) else None
            )

    def get_total_network_transactions(self) -> int:
        """Returns the total number of transactions in the entire graph."""
        return self.G.number_of_edges()

    def get_account_metrics(self, account_id: str, before_timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculates all historical graph and volume metrics for a specific account.
        Only considers transactions on or before before_timestamp to prevent look-ahead leakage.
        """
        account_str = str(account_id)
        if not self.G.has_node(account_str):
            return {
                "incoming_counterparties": 0,
                "outgoing_counterparties": 0,
                "incoming_tx_count": 0,
                "outgoing_tx_count": 0,
                "incoming_amount": 0.0,
                "outgoing_amount": 0.0,
                "recipient_in_degree": 0,
                "sender_out_degree": 0,
                "in_degree": 0,
                "out_degree": 0,
                "unique_incoming_counterparties": 0,
                "unique_outgoing_counterparties": 0,
                "fan_in": 0,
                "fan_out": 0,
                "total_network_tx_count": self.get_total_network_transactions()
            }
            
        # Get edges filtering by timestamp
        in_edges = []
        for u, v, key, data in self.G.in_edges(account_str, data=True, keys=True):
            if before_timestamp is None or data["timestamp"] < before_timestamp:
                in_edges.append((u, v, key, data))
                
        out_edges = []
        for u, v, key, data in self.G.out_edges(account_str, data=True, keys=True):
            if before_timestamp is None or data["timestamp"] < before_timestamp:
                out_edges.append((u, v, key, data))
                
        # Get unique counterparties
        incoming_counterparties = list(set(u for u, _, _, _ in in_edges))
        outgoing_counterparties = list(set(v for _, v, _, _ in out_edges))
        
        # Calculate incoming metrics
        incoming_amount = 0.0
        incoming_tx_count = len(in_edges)
        in_24h_senders = set()
        
        # Define 24h window
        if before_timestamp is not None:
            window_end = before_timestamp
        else:
            window_end = self.df["timestamp"].max()
        window_start = window_end - timedelta(days=1)
        
        for u, _, _, data in in_edges:
            incoming_amount += data["amount"]
            if window_start <= data["timestamp"] <= window_end:
                in_24h_senders.add(u)
                
        # Calculate outgoing metrics
        outgoing_amount = 0.0
        outgoing_tx_count = len(out_edges)
        out_24h_receivers = set()
        
        for _, v, _, data in out_edges:
            outgoing_amount += data["amount"]
            if window_start <= data["timestamp"] <= window_end:
                out_24h_receivers.add(v)
                
        if before_timestamp is not None:
            total_network_tx_count = sum(1 for _, _, data in self.G.edges(data=True) if data["timestamp"] < before_timestamp)
        else:
            total_network_tx_count = self.get_total_network_transactions()
                
        return {
            "incoming_counterparties": len(incoming_counterparties),
            "outgoing_counterparties": len(outgoing_counterparties),
            "incoming_tx_count": incoming_tx_count,
            "outgoing_tx_count": outgoing_tx_count,
            "incoming_amount": round(incoming_amount, 2),
            "outgoing_amount": round(outgoing_amount, 2),
            "recipient_in_degree": len(in_24h_senders),
            "sender_out_degree": len(out_24h_receivers),
            "in_degree": incoming_tx_count,
            "out_degree": outgoing_tx_count,
            "unique_incoming_counterparties": len(incoming_counterparties),
            "unique_outgoing_counterparties": len(outgoing_counterparties),
            "fan_in": len(incoming_counterparties),
            "fan_out": len(outgoing_counterparties),
            "total_network_tx_count": total_network_tx_count
        }

    def detect_rapid_pass_through_events(self, account_id: str, threshold_hours: float = 3.0, before_timestamp: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Identifies pairs of (incoming_tx, outgoing_tx) where funds are received and
        subsequently sent out within the specified short time interval.
        Only considers transactions on or before before_timestamp to prevent look-ahead leakage.
        """
        account_str = str(account_id)
        if not self.G.has_node(account_str):
            return []
            
        # Get list of all incoming and outgoing transactions
        in_txs = []
        for u, _, key, data in self.G.in_edges(account_str, data=True, keys=True):
            if before_timestamp is None or data["timestamp"] < before_timestamp:
                in_txs.append({
                    "transaction_id": data["transaction_id"],
                    "counterparty": u,
                    "amount": data["amount"],
                    "timestamp": data["timestamp"]
                })
            
        out_txs = []
        for _, v, key, data in self.G.out_edges(account_str, data=True, keys=True):
            if before_timestamp is None or data["timestamp"] < before_timestamp:
                out_txs.append({
                    "transaction_id": data["transaction_id"],
                    "counterparty": v,
                    "amount": data["amount"],
                    "timestamp": data["timestamp"]
                })
            
        # Sort chronologically
        in_txs = sorted(in_txs, key=lambda x: x["timestamp"])
        out_txs = sorted(out_txs, key=lambda x: x["timestamp"])
        
        pass_through_pairs = []
        
        # Check matching time-delay pairs
        for itx in in_txs:
            for otx in out_txs:
                if otx["timestamp"] > itx["timestamp"]:
                    time_diff = (otx["timestamp"] - itx["timestamp"]).total_seconds() / 3600.0
                    if 0 < time_diff <= threshold_hours:
                        pass_through_pairs.append({
                            "incoming_tx_id": itx["transaction_id"],
                            "outgoing_tx_id": otx["transaction_id"],
                            "from_user": itx["counterparty"],
                            "to_user": otx["counterparty"],
                            "incoming_amount": itx["amount"],
                            "outgoing_amount": otx["amount"],
                            "delay_minutes": round(time_diff * 60.0, 1)
                        })
                        
        return pass_through_pairs

    def check_mule_patterns(self, account_id: str, before_timestamp: Optional[datetime] = None) -> Dict[str, bool]:
        """
        Applies rules to detect patterns that are indicative of mule account operations.
        Returns boolean flags for patterns A, B, C, D, and E.
        """
        account_str = str(account_id)
        metrics = self.get_account_metrics(account_str, before_timestamp=before_timestamp)
        pass_through_events = self.detect_rapid_pass_through_events(account_str, threshold_hours=3.0, before_timestamp=before_timestamp)
        
        # PATTERN A: Many distinct accounts -> one account (Fan-In)
        pattern_a = metrics["incoming_counterparties"] >= 5
        
        # PATTERN B: One account -> many distinct accounts (Fan-Out)
        pattern_b = metrics["outgoing_counterparties"] >= 5
        
        # PATTERN C: Many incoming counterparties transferring to outgoing counterparties (Intermediary/Aggregator)
        pattern_c = metrics["incoming_counterparties"] >= 3 and metrics["outgoing_counterparties"] >= 2
        
        # PATTERN D: Rapid pass-through behavior
        pattern_d = len(pass_through_events) > 0
        
        # PATTERN E: High connectivity (>= 5 counterparties) combined with behavioral deviation signals
        # Check if average amount deviation is high, or device/IP changes occurred
        has_behavioral_dev = False
        if self.G.has_node(account_str):
            tx_count = 0
            dev_sum = 0.0
            new_device_count = 0
            new_ip_count = 0
            
            # Look at all transactions involving this node
            for u, v, key, data in self.G.out_edges(account_str, data=True, keys=True):
                if before_timestamp is not None and data["timestamp"] >= before_timestamp:
                    continue
                # Outgoing
                tx_count += 1
                if data["amount_deviation"] is not None:
                    dev_sum += data["amount_deviation"]
                new_device_count += data["is_new_device"]
                new_ip_count += data["is_new_ip"]
                
            for u, v, key, data in self.G.in_edges(account_str, data=True, keys=True):
                if before_timestamp is not None and data["timestamp"] >= before_timestamp:
                    continue
                # Incoming
                tx_count += 1
                if data["amount_deviation"] is not None:
                    dev_sum += data["amount_deviation"]
                new_device_count += data["is_new_device"]
                new_ip_count += data["is_new_ip"]
                
            avg_deviation = (dev_sum / tx_count) if tx_count > 0 else 1.0
            if avg_deviation >= 3.0 or new_device_count > 0 or new_ip_count > 0:
                has_behavioral_dev = True
                
        pattern_e = (metrics["incoming_counterparties"] + metrics["outgoing_counterparties"]) >= 5 and has_behavioral_dev
        
        return {
            "pattern_a": pattern_a,
            "pattern_b": pattern_b,
            "pattern_c": pattern_c,
            "pattern_d": pattern_d,
            "pattern_e": pattern_e
        }

    def calculate_account_network_risk(self, account_id: str, before_timestamp: Optional[datetime] = None) -> float:
        """
        Computes a deterministic, explainable network risk score (0-100).
        Score components:
        1. Connectivity (20%): total unique counterparties (cap at 8)
        2. Fan-In/Fan-Out (20%): max of incoming counterparties / 5 or outgoing / 5
        3. Pass-through (30%): rapid pass-through count (cap at 2 pairs)
        4. Concentration (15%): max incoming/outgoing amount share from/to single counterparty
        5. Behavioral context (15%): anomaly/deviation rates of connected transactions
        All components strictly respect the before_timestamp filter.
        """
        account_str = str(account_id)
        if not self.G.has_node(account_str):
            return 0.0
            
        metrics = self.get_account_metrics(account_str, before_timestamp=before_timestamp)
        pass_throughs = self.detect_rapid_pass_through_events(account_str, threshold_hours=3.0, before_timestamp=before_timestamp)
        
        # 1. Connectivity Score (20% weight)
        total_counterparties = metrics["incoming_counterparties"] + metrics["outgoing_counterparties"]
        s_conn = min(100.0, (total_counterparties / 8.0) * 100.0)
        
        # 2. Fan-In/Fan-Out Score (20% weight)
        s_in = min(100.0, (metrics["incoming_counterparties"] / 5.0) * 100.0)
        s_out = min(100.0, (metrics["outgoing_counterparties"] / 5.0) * 100.0)
        s_fan = max(s_in, s_out)
        
        # 3. Pass-through Score (30% weight)
        s_pass = min(100.0, (len(pass_throughs) / 2.0) * 100.0)
        
        # 4. Concentration Score (15% weight)
        # Calculate max share of a single sender and single receiver
        max_in_share = 0.0
        if metrics["incoming_amount"] > 0:
            sender_amts = {}
            for u, _, data in self.G.in_edges(account_str, data=True):
                if before_timestamp is None or data["timestamp"] < before_timestamp:
                    sender_amts[u] = sender_amts.get(u, 0.0) + data["amount"]
            if sender_amts:
                max_in_share = max(sender_amts.values()) / metrics["incoming_amount"]
                
        max_out_share = 0.0
        if metrics["outgoing_amount"] > 0:
            receiver_amts = {}
            for _, v, data in self.G.out_edges(account_str, data=True):
                if before_timestamp is None or data["timestamp"] < before_timestamp:
                    receiver_amts[v] = receiver_amts.get(v, 0.0) + data["amount"]
            if receiver_amts:
                max_out_share = max(receiver_amts.values()) / metrics["outgoing_amount"]
                
        s_conc = max(max_in_share, max_out_share) * 100.0
        
        # 5. Behavioral context (15% weight)
        # Check device/IP shifts and deviation metrics
        tx_count = 0
        dev_sum = 0.0
        new_device_count = 0
        new_ip_count = 0
        
        for u, v, key, data in self.G.out_edges(account_str, data=True, keys=True):
            if before_timestamp is not None and data["timestamp"] >= before_timestamp:
                continue
            tx_count += 1
            if data["amount_deviation"] is not None:
                dev_sum += data["amount_deviation"]
            new_device_count += data["is_new_device"]
            new_ip_count += data["is_new_ip"]
            
        for u, v, key, data in self.G.in_edges(account_str, data=True, keys=True):
            if before_timestamp is not None and data["timestamp"] >= before_timestamp:
                continue
            tx_count += 1
            if data["amount_deviation"] is not None:
                dev_sum += data["amount_deviation"]
            new_device_count += data["is_new_device"]
            new_ip_count += data["is_new_ip"]
            
        s_behav = 0.0
        if tx_count > 0:
            avg_dev = dev_sum / tx_count
            if avg_dev >= 3.0:
                s_behav += 40.0
            if new_device_count > 0:
                s_behav += 30.0
            if new_ip_count > 0:
                s_behav += 30.0
                
        # Final weighted score
        final_score = (
            0.20 * s_conn +
            0.20 * s_fan +
            0.30 * s_pass +
            0.15 * s_conc +
            0.15 * s_behav
        )
        
        return round(max(0.0, min(100.0, final_score)), 2)

    def generate_explanations(self, account_id: str, before_timestamp: Optional[datetime] = None) -> List[str]:
        """
        Generates clean, human-readable indicators based on active mule patterns and metrics.
        Only considers transactions on or before before_timestamp to prevent look-ahead leakage.
        """
        account_str = str(account_id)
        metrics = self.get_account_metrics(account_str, before_timestamp=before_timestamp)
        patterns = self.check_mule_patterns(account_str, before_timestamp=before_timestamp)
        risk_score = self.calculate_account_network_risk(account_str, before_timestamp=before_timestamp)
        
        explanations = []
        
        if patterns["pattern_a"]:
            explanations.append("High number of incoming counterparties")
        if patterns["pattern_b"]:
            explanations.append("Unusually high outbound connectivity")
        if patterns["pattern_d"]:
            explanations.append("Rapid movement of funds after receiving money")
        if patterns["pattern_c"]:
            explanations.append("Account acts as an intermediary between multiple accounts")
        if risk_score >= 60.0 or patterns["pattern_e"]:
            explanations.append("Potential mule-network behavior detected")
            
        return explanations

    def get_ego_network(self, account_id: str, before_timestamp: Optional[datetime] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extracts a 1-hop sub-graph ego network centered on account_id.
        Excludes is_fraud_labeled to respect safety and data leakage prevention rules.
        Only considers transactions on or before before_timestamp to prevent look-ahead leakage.
        """
        account_str = str(account_id)
        if not self.G.has_node(account_str):
            return {"nodes": [], "edges": []}
            
        # Get 1-hop neighbors from filtered edges
        neighbors = set()
        for u, v, key, data in self.G.in_edges(account_str, data=True, keys=True):
            if before_timestamp is None or data["timestamp"] < before_timestamp:
                neighbors.add(u)
        for u, v, key, data in self.G.out_edges(account_str, data=True, keys=True):
            if before_timestamp is None or data["timestamp"] < before_timestamp:
                neighbors.add(v)
                
        nodes_set = neighbors | {account_str}
        
        # Build node elements
        nodes = []
        for node in nodes_set:
            node_risk = self.calculate_account_network_risk(node, before_timestamp=before_timestamp)
            nodes.append({
                "id": node,
                "type": "account",
                "risk": node_risk
            })
            
        # Build edge elements from global graph
        edges = []
        seen_edges = set()
        
        for u, v, key, data in self.G.edges(data=True, keys=True):
            if before_timestamp is None or data["timestamp"] < before_timestamp:
                if u in nodes_set and v in nodes_set:
                    tx_id = data["transaction_id"]
                    if tx_id not in seen_edges:
                        seen_edges.add(tx_id)
                        edges.append({
                            "source": u,
                            "target": v,
                            "amount": data["amount"],
                            "timestamp": str(data["timestamp"]),
                            "transaction_id": tx_id
                        })
                    
        return {"nodes": nodes, "edges": edges}
