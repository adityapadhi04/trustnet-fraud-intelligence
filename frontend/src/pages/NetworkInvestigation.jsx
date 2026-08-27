import React, { useState, useEffect } from 'react';
import { fetchAccountNetworkProfile, fetchSampleTransactions } from '../services/api';

function NetworkInvestigation() {
  const [accountId, setAccountId] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [networkData, setNetworkData] = useState(null);
  
  // For quick selections
  const [sampleAccounts, setSampleAccounts] = useState([]);
  const [loadingSamples, setLoadingSamples] = useState(false);
  
  // Hover states for graph
  const [hoveredNode, setHoveredNode] = useState(null);
  const [hoveredEdge, setHoveredEdge] = useState(null);

  // Fetch sample transactions on mount to populate quick search options
  useEffect(() => {
    async function loadSamples() {
      try {
        setLoadingSamples(true);
        const data = await fetchSampleTransactions(40);
        if (data.transactions) {
          const accountsSet = new Set();
          data.transactions.forEach(tx => {
            accountsSet.add(tx.sender_id);
            accountsSet.add(tx.receiver_id);
          });
          setSampleAccounts(Array.from(accountsSet).slice(0, 10)); // Take first 10
        }
      } catch (err) {
        console.error('Failed to load sample accounts:', err);
      } finally {
        setLoadingSamples(false);
      }
    }
    loadSamples();
  }, []);

  // Fetch network profile
  const handleSearch = async (idToSearch) => {
    const cleanId = (idToSearch || searchQuery || accountId).trim().toUpperCase();
    if (!cleanId) return;

    setAccountId(cleanId);
    setSearchQuery(cleanId);
    setLoading(true);
    setError(null);
    setNetworkData(null);

    try {
      const data = await fetchAccountNetworkProfile(cleanId);
      setNetworkData(data);
    } catch (err) {
      console.error('Failed to fetch network profile:', err);
      setError(err.message || `Failed to retrieve network profile for account ${cleanId}`);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (risk) => {
    if (risk >= 80) return '#EF4444'; // CRITICAL - Red
    if (risk >= 60) return '#F97316'; // HIGH - Orange
    if (risk >= 30) return '#EAB308'; // MEDIUM - Yellow
    return '#10B981'; // LOW - Green
  };

  const getRiskLabel = (risk) => {
    if (risk >= 80) return 'CRITICAL';
    if (risk >= 60) return 'HIGH';
    if (risk >= 30) return 'MEDIUM';
    return 'LOW';
  };

  // Helper to layout nodes in a circle around the center
  const getGraphLayout = () => {
    if (!networkData || !networkData.relevant_transaction_relationships) return null;
    
    const centerId = networkData.account_id;
    const { nodes, edges } = networkData.relevant_transaction_relationships;
    
    const centerX = 350;
    const centerY = 280;
    const radius = 180;
    
    const neighborNodes = nodes.filter(n => n.id !== centerId);
    const layoutNodes = {};
    
    // Position center node
    const centerNodeObj = nodes.find(n => n.id === centerId) || { id: centerId, risk: networkData.network_risk };
    layoutNodes[centerId] = {
      ...centerNodeObj,
      x: centerX,
      y: centerY,
      isCenter: true
    };
    
    // Position neighbors radially
    neighborNodes.forEach((node, index) => {
      const theta = (2 * Math.PI * index) / neighborNodes.length;
      layoutNodes[node.id] = {
        ...node,
        x: centerX + radius * Math.cos(theta),
        y: centerY + radius * Math.sin(theta),
        isCenter: false
      };
    });
    
    // Position edges
    const layoutEdges = edges.map((edge, idx) => {
      const sourceNode = layoutNodes[edge.source];
      const targetNode = layoutNodes[edge.target];
      return {
        ...edge,
        id: edge.transaction_id || `edge-${idx}`,
        x1: sourceNode ? sourceNode.x : centerX,
        y1: sourceNode ? sourceNode.y : centerY,
        x2: targetNode ? targetNode.x : centerX,
        y2: targetNode ? targetNode.y : centerY
      };
    });
    
    return {
      nodes: Object.values(layoutNodes),
      edges: layoutEdges
    };
  };

  const graphLayout = getGraphLayout();

  return (
    <div className="workspace-grid" style={{ gridTemplateColumns: '1fr' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', width: '100%' }}>
        
        {/* Search Header Dashboard */}
        <div className="card-panel" style={{ padding: '20px' }}>
          <h2 style={{ margin: '0 0 10px 0', fontSize: '18px', color: 'var(--text-primary)' }}>
            🕸️ Network Intelligence Investigation
          </h2>
          <p style={{ margin: '0 0 20px 0', fontSize: '13px', color: 'var(--text-muted)' }}>
            Search any account ID to fetch its 1-hop transactions network, calculate network-risk metrics, detect potential mule activities, and map fund movements.
          </p>
          
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '15px' }}>
            <input 
              type="text" 
              placeholder="Enter Account ID (e.g. U0123)..." 
              className="search-input"
              style={{ flex: 1, maxWidth: '400px', margin: 0 }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button 
              className="action-btn-primary" 
              onClick={() => handleSearch()}
              disabled={loading}
              style={{ padding: '0 24px', height: '42px' }}
            >
              {loading ? 'Analyzing...' : 'Search Graph'}
            </button>
          </div>

          {/* Quick select buttons */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Quick Select:</span>
            {loadingSamples ? (
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Loading samples...</span>
            ) : (
              sampleAccounts.map(id => (
                <button
                  key={id}
                  onClick={() => handleSearch(id)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '11px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '4px',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer'
                  }}
                  className="quick-select-btn"
                >
                  {id}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="error-alert-box" style={{ padding: '16px' }}>
            <strong>Investigation Error:</strong> {error}
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <div className="spinner" style={{ margin: '0 auto 20px auto' }}></div>
            <p>Constructing account graph and executing graph metrics scoring...</p>
          </div>
        )}

        {/* Empty State */}
        {!networkData && !loading && !error && (
          <div className="empty-state" style={{ padding: '60px 20px', minHeight: '300px' }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>🕸️</div>
            <h3>Forensic Network Investigator</h3>
            <p style={{ maxWidth: '500px', margin: '0 auto' }}>
              Select an account using the Quick Select chips above or enter an account ID in the search bar to run NetworkX topology algorithms and visualize transfer relationships.
            </p>
          </div>
        )}

        {/* Main Graph Workbench Content */}
        {networkData && !loading && (
          <div style={{ display: 'grid', gridTemplateColumns: '7fr 3fr', gap: '20px' }}>
            
            {/* Left Graph Panel */}
            <div className="card-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', height: '620px', position: 'relative' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <span style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)' }}>
                  1-Hop Ego Network Map for Account: <span style={{ color: 'var(--accent-color)', fontFamily: 'monospace' }}>{networkData.account_id}</span>
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {networkData.relevant_transaction_relationships.nodes.length} nodes | {networkData.relevant_transaction_relationships.edges.length} edges
                </span>
              </div>
              
              {/* Interactive SVG graph */}
              <div style={{ flex: 1, backgroundColor: 'rgba(0, 0, 0, 0.2)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', overflow: 'hidden', position: 'relative' }}>
                <svg width="100%" height="100%" viewBox="0 0 700 560" style={{ cursor: 'grab' }}>
                  {/* Arrowhead definitions */}
                  <defs>
                    <marker 
                      id="arrow" 
                      viewBox="0 0 10 10" 
                      refX="24" 
                      refY="5" 
                      markerWidth="6" 
                      markerHeight="6" 
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
                    </marker>
                    <marker 
                      id="arrow-hover" 
                      viewBox="0 0 10 10" 
                      refX="24" 
                      refY="5" 
                      markerWidth="8" 
                      markerHeight="8" 
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#f43f5e" />
                    </marker>
                  </defs>

                  {/* Draw edges (lines) */}
                  {graphLayout && graphLayout.edges.map((edge) => {
                    const isHovered = hoveredEdge?.transaction_id === edge.transaction_id;
                    return (
                      <g 
                        key={edge.id}
                        onMouseEnter={() => setHoveredEdge(edge)}
                        onMouseLeave={() => setHoveredEdge(null)}
                        style={{ cursor: 'pointer' }}
                      >
                        {/* Interactive fat collision line for easier hovering */}
                        <line 
                          x1={edge.x1} 
                          y1={edge.y1} 
                          x2={edge.x2} 
                          y2={edge.y2} 
                          stroke="transparent" 
                          strokeWidth="12" 
                        />
                        {/* Visual line */}
                        <line 
                          x1={edge.x1} 
                          y1={edge.y1} 
                          x2={edge.x2} 
                          y2={edge.y2} 
                          stroke={isHovered ? '#f43f5e' : 'rgba(100, 116, 139, 0.4)'} 
                          strokeWidth={isHovered ? '2.5' : '1.5'} 
                          markerEnd={isHovered ? 'url(#arrow-hover)' : 'url(#arrow)'}
                        />
                        {/* Text label on line for amounts (only for hovered/selected or high amounts) */}
                        {isHovered && (
                          <rect
                            x={(edge.x1 + edge.x2) / 2 - 45}
                            y={(edge.y1 + edge.y2) / 2 - 10}
                            width="90"
                            height="18"
                            rx="3"
                            fill="#1e293b"
                            stroke="#f43f5e"
                            strokeWidth="1"
                          />
                        )}
                        {isHovered && (
                          <text 
                            x={(edge.x1 + edge.x2) / 2}
                            y={(edge.y1 + edge.y2) / 2 + 3}
                            fill="#f8fafc"
                            fontSize="10px"
                            fontWeight="bold"
                            textAnchor="middle"
                          >
                            ₹{edge.amount.toFixed(2)}
                          </text>
                        )}
                      </g>
                    );
                  })}

                  {/* Draw nodes (circles) */}
                  {graphLayout && graphLayout.nodes.map((node) => {
                    const rColor = getRiskColor(node.risk);
                    const isCenter = node.isCenter;
                    const isHovered = hoveredNode?.id === node.id;
                    const size = isCenter ? 26 : 20;
                    
                    return (
                      <g 
                        key={node.id} 
                        transform={`translate(${node.x}, ${node.y})`}
                        style={{ cursor: 'pointer' }}
                        onClick={() => handleSearch(node.id)}
                        onMouseEnter={() => setHoveredNode(node)}
                        onMouseLeave={() => setHoveredNode(null)}
                      >
                        <circle 
                          r={size + (isHovered ? 4 : 0)} 
                          fill={isCenter ? '#0f172a' : '#1e293b'}
                          stroke={isHovered ? '#ffffff' : rColor}
                          strokeWidth={isCenter ? '3.5' : '2'}
                          style={{ transition: 'all 0.15s ease' }}
                        />
                        {isCenter && (
                          <circle
                            r="6"
                            fill={rColor}
                          />
                        )}
                        <text 
                          y={size + 15}
                          fill="var(--text-primary)"
                          fontSize="11px"
                          fontWeight={isCenter ? 'bold' : 'normal'}
                          fontFamily="monospace"
                          textAnchor="middle"
                        >
                          {node.id} {isCenter ? '(Center)' : ''}
                        </text>
                        {/* Risk text badge on hover */}
                        {isHovered && (
                          <g transform={`translate(0, -${size + 15})`}>
                            <rect 
                              x="-35" 
                              y="-15" 
                              width="70" 
                              height="20" 
                              rx="4" 
                              fill="#0f172a" 
                              stroke="rgba(255,255,255,0.15)"
                              strokeWidth="1"
                            />
                            <text 
                              y="-2" 
                              fill={rColor} 
                              fontSize="9px" 
                              fontWeight="bold" 
                              textAnchor="middle"
                            >
                              Risk: {node.risk.toFixed(0)}%
                            </text>
                          </g>
                        )}
                      </g>
                    );
                  })}
                </svg>

                {/* Graph tooltip overlays */}
                {hoveredEdge && (
                  <div style={{
                    position: 'absolute',
                    bottom: '12px',
                    left: '12px',
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    border: '1px solid #f43f5e',
                    borderRadius: '6px',
                    padding: '10px 14px',
                    fontSize: '12px',
                    zIndex: 10,
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)'
                  }}>
                    <div style={{ fontWeight: 'bold', color: '#f43f5e', marginBottom: '4px' }}>Transaction Relationship</div>
                    <div>From: <span style={{ fontFamily: 'monospace' }}>{hoveredEdge.source}</span></div>
                    <div>To: <span style={{ fontFamily: 'monospace' }}>{hoveredEdge.target}</span></div>
                    <div style={{ fontWeight: 600, marginTop: '4px' }}>Amount: ₹{hoveredEdge.amount.toFixed(2)}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '2px' }}>Time: {hoveredEdge.timestamp}</div>
                  </div>
                )}

                {/* Instructions */}
                <div style={{
                  position: 'absolute',
                  top: '12px',
                  right: '12px',
                  backgroundColor: 'rgba(15, 23, 42, 0.8)',
                  padding: '6px 10px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  color: 'var(--text-muted)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  pointerEvents: 'none'
                }}>
                  💡 Click node to pivot search. Hover nodes/edges for details.
                </div>
              </div>
            </div>
            
            {/* Right Risk Assessment Sidebar */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Overall Network Risk Rating */}
              <div className="card-panel" style={{ padding: '20px', textAlign: 'center' }}>
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Network Prioritization Risk</span>
                
                <div style={{ margin: '15px 0' }}>
                  <div style={{ 
                    fontSize: '36px', 
                    fontWeight: 800, 
                    color: getRiskColor(networkData.network_risk),
                    textShadow: `0 0 10px ${getRiskColor(networkData.network_risk)}33`
                  }}>
                    {networkData.network_risk.toFixed(1)}%
                  </div>
                  <div style={{ 
                    display: 'inline-block',
                    padding: '3px 12px',
                    borderRadius: '12px',
                    fontSize: '11px',
                    fontWeight: 'bold',
                    marginTop: '5px',
                    backgroundColor: `${getRiskColor(networkData.network_risk)}20`,
                    color: getRiskColor(networkData.network_risk),
                    border: `1px solid ${getRiskColor(networkData.network_risk)}40`
                  }}>
                    {getRiskLabel(networkData.network_risk)} RISK
                  </div>
                </div>

                <hr style={{ border: 0, borderTop: '1px solid rgba(255,255,255,0.05)', margin: '15px 0' }} />

                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>Estimated Mule Flow Score</span>
                <div style={{ margin: '10px 0' }}>
                  <div style={{ fontSize: '24px', fontWeight: 700, color: getRiskColor(networkData.mule_risk) }}>
                    {networkData.mule_risk.toFixed(1)}%
                  </div>
                  <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px', marginTop: '10px', overflow: 'hidden' }}>
                    <div style={{ 
                      width: `${networkData.mule_risk}%`, 
                      height: '100%', 
                      backgroundColor: getRiskColor(networkData.mule_risk) 
                    }}></div>
                  </div>
                </div>
              </div>

              {/* Mule Account Indicators */}
              <div className="card-panel" style={{ padding: '20px' }}>
                <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-secondary)', display: 'block', marginBottom: '12px' }}>
                  🚨 Network Indicators
                </span>
                
                {networkData.indicators && networkData.indicators.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {networkData.indicators.map((ind, i) => (
                      <div 
                        key={i}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '6px',
                          fontSize: '12px',
                          backgroundColor: 'rgba(239, 68, 68, 0.08)',
                          color: '#FDA4AF',
                          borderLeft: '3px solid #EF4444'
                        }}
                      >
                        ⚠️ {ind}
                      </div>
                    ))}
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '8px', fontStyle: 'italic' }}>
                      * Network indicators support investigation and prioritization; they do not prove fraud or confirm that an account is a mule.
                    </div>
                  </div>
                ) : (
                  <div style={{ 
                    padding: '12px', 
                    borderRadius: '6px', 
                    fontSize: '12px', 
                    backgroundColor: 'rgba(16, 185, 129, 0.08)', 
                    color: '#A7F3D0',
                    borderLeft: '3px solid #10B981',
                    textAlign: 'center'
                  }}>
                    ✅ No critical mule indicators detected.
                  </div>
                )}
              </div>

              {/* Account Topology Metrics */}
              <div className="card-panel" style={{ padding: '20px', flex: 1 }}>
                <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-secondary)', display: 'block', marginBottom: '12px' }}>
                  📊 Network Graph Metrics
                </span>
                
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <tbody>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Incoming Counterparties (Fan-In)</td>
                      <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 'bold' }}>{networkData.incoming_connections}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Outgoing Counterparties (Fan-Out)</td>
                      <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 'bold' }}>{networkData.outgoing_connections}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Incoming Tx Volume</td>
                      <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 'bold' }}>{networkData.network_metrics.incoming_tx_count}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Outgoing Tx Volume</td>
                      <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 'bold' }}>{networkData.network_metrics.outgoing_tx_count}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Incoming Fund Strength</td>
                      <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 'bold', color: '#10B981' }}>₹{networkData.network_metrics.incoming_amount.toFixed(2)}</td>
                    </tr>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Outgoing Fund Strength</td>
                      <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 'bold', color: '#EF4444' }}>₹{networkData.network_metrics.outgoing_amount.toFixed(2)}</td>
                    </tr>
                    <tr>
                      <td style={{ padding: '8px 0', color: 'var(--text-secondary)' }}>Rapid Pass-Throughs</td>
                      <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 'bold', color: networkData.network_metrics.rapid_pass_through_count > 0 ? '#F97316' : 'inherit' }}>
                        {networkData.network_metrics.rapid_pass_through_count}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

            </div>

          </div>
        )}

        {/* Connected Accounts Details Table */}
        {networkData && !loading && (
          <div className="card-panel" style={{ padding: '20px' }}>
            <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-secondary)', display: 'block', marginBottom: '12px' }}>
              👥 Connected Account Members
            </span>
            <div className="table-container" style={{ maxHeight: '200px', overflowY: 'auto' }}>
              <table className="tx-table" style={{ fontSize: '12px' }}>
                <thead>
                  <tr>
                    <th>Account ID</th>
                    <th>Connection Type</th>
                    <th style={{ textAlign: 'center' }}>Network Risk</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {graphLayout && graphLayout.nodes.filter(n => !n.isCenter).map((node) => {
                    const isIncoming = networkData.relevant_transaction_relationships.edges.some(e => e.source === node.id && e.target === networkData.account_id);
                    const isOutgoing = networkData.relevant_transaction_relationships.edges.some(e => e.source === networkData.account_id && e.target === node.id);
                    
                    let relation = 'Neighbor';
                    if (isIncoming && isOutgoing) relation = 'Mutual Partner';
                    else if (isIncoming) relation = 'Predecessor (Sender)';
                    else if (isOutgoing) relation = 'Successor (Receiver)';

                    return (
                      <tr key={node.id}>
                        <td style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{node.id}</td>
                        <td>{relation}</td>
                        <td style={{ textAlign: 'center' }}>
                          <span style={{ 
                            color: getRiskColor(node.risk),
                            fontWeight: 'bold',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            backgroundColor: `${getRiskColor(node.risk)}15`
                          }}>
                            {node.risk.toFixed(0)}%
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            onClick={() => handleSearch(node.id)}
                            style={{
                              padding: '2px 8px',
                              fontSize: '11px',
                              backgroundColor: 'rgba(255, 255, 255, 0.05)',
                              border: '1px solid rgba(255, 255, 255, 0.1)',
                              borderRadius: '4px',
                              color: 'var(--text-secondary)',
                              cursor: 'pointer'
                            }}
                          >
                            Investigate ➔
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export default NetworkInvestigation;
