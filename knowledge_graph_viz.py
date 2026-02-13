"""
knowledge_graph_viz.py - Interactive D3.js Knowledge Graph Visualization

Generates interactive force-directed graph showing relationships between:
- Leads (customers)
- Vehicles (inventory)
- Appointments/TestDrives (bookings)
"""

import logging
from typing import Dict, List, Tuple
import json

logger = logging.getLogger(__name__)


def get_knowledge_graph_data(
    neo4j_connection,
    filter_type: str = "all",
    limit: int = 50
) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Query Neo4j for knowledge graph data
    
    Args:
        neo4j_connection: Neo4j handler instance
        filter_type: Filter type - "all", "leads", "vehicles", "appointments", "test_drives"
        limit: Maximum number of nodes to return
        
    Returns:
        Tuple of (nodes_list, edges_list, stats_dict)
    """
    
    logger.info(f"🔍 Fetching knowledge graph data: filter={filter_type}, limit={limit}")
    
    nodes = []
    edges = []
    stats = {
        'total_nodes': 0,
        'total_edges': 0,
        'leads': 0,
        'vehicles': 0,
        'appointments': 0,
        'test_drives': 0
    }
    
    try:
        with neo4j_connection.driver.session(database=neo4j_connection.database) as session:
            
            # ═══════════════════════════════════════════════════════════
            # BUILD QUERY BASED ON FILTER TYPE
            # ═══════════════════════════════════════════════════════════
            
            if filter_type == "leads":
                query = """
                    // Get leads with their appointments and vehicles
                    MATCH (l:Lead)
                    OPTIONAL MATCH (l)-[r1:HAS_APPOINTMENT]->(a:Appointment)
                    OPTIONAL MATCH (a)-[r2:FOR_VEHICLE]->(v:Vehicle)
                    OPTIONAL MATCH (l)-[r3:BOOKED_TEST_DRIVE]->(td:TestDrive)
                    OPTIONAL MATCH (td)-[r4:FOR_VEHICLE]->(v2:Vehicle)
                    WITH l, a, v, td, v2, r1, r2, r3, r4
                    LIMIT $limit
                    RETURN 
                        collect(DISTINCT l) as leads,
                        collect(DISTINCT a) as appointments,
                        collect(DISTINCT td) as test_drives,
                        collect(DISTINCT v) + collect(DISTINCT v2) as vehicles,
                        collect(DISTINCT r1) as r1_rels,
                        collect(DISTINCT r2) as r2_rels,
                        collect(DISTINCT r3) as r3_rels,
                        collect(DISTINCT r4) as r4_rels
                """
                
            elif filter_type == "vehicles":
                query = """
                    // Get vehicles with appointments
                    MATCH (v:Vehicle)
                    OPTIONAL MATCH (a:Appointment)-[r:FOR_VEHICLE]->(v)
                    OPTIONAL MATCH (td:TestDrive)-[r2:FOR_VEHICLE]->(v)
                    WITH v, a, td, r, r2
                    LIMIT $limit
                    RETURN 
                        collect(DISTINCT v) as vehicles,
                        collect(DISTINCT a) as appointments,
                        collect(DISTINCT td) as test_drives,
                        [] as leads,
                        collect(DISTINCT r) as r2_rels,
                        collect(DISTINCT r2) as r4_rels,
                        [] as r1_rels,
                        [] as r3_rels
                """
                
            elif filter_type == "appointments":
                query = """
                    // Get appointments with leads and vehicles
                    MATCH (a:Appointment)
                    OPTIONAL MATCH (l:Lead)-[r1:HAS_APPOINTMENT]->(a)
                    OPTIONAL MATCH (a)-[r2:FOR_VEHICLE]->(v:Vehicle)
                    WITH a, l, v, r1, r2
                    LIMIT $limit
                    RETURN 
                        collect(DISTINCT a) as appointments,
                        collect(DISTINCT l) as leads,
                        collect(DISTINCT v) as vehicles,
                        [] as test_drives,
                        collect(DISTINCT r1) as r1_rels,
                        collect(DISTINCT r2) as r2_rels,
                        [] as r3_rels,
                        [] as r4_rels
                """
                
            elif filter_type == "test_drives":
                query = """
                    // Get test drives with leads and vehicles
                    MATCH (td:TestDrive)
                    OPTIONAL MATCH (l:Lead)-[r3:BOOKED_TEST_DRIVE]->(td)
                    OPTIONAL MATCH (td)-[r4:FOR_VEHICLE]->(v:Vehicle)
                    WITH td, l, v, r3, r4
                    LIMIT $limit
                    RETURN 
                        collect(DISTINCT td) as test_drives,
                        collect(DISTINCT l) as leads,
                        collect(DISTINCT v) as vehicles,
                        [] as appointments,
                        [] as r1_rels,
                        [] as r2_rels,
                        collect(DISTINCT r3) as r3_rels,
                        collect(DISTINCT r4) as r4_rels
                """
                
            else:  # "all"
                query = """
                    // Get comprehensive graph data
                    MATCH (l:Lead)
                    OPTIONAL MATCH (l)-[r1:HAS_APPOINTMENT]->(a:Appointment)
                    OPTIONAL MATCH (a)-[r2:FOR_VEHICLE]->(v1:Vehicle)
                    OPTIONAL MATCH (l)-[r3:BOOKED_TEST_DRIVE]->(td:TestDrive)
                    OPTIONAL MATCH (td)-[r4:FOR_VEHICLE]->(v2:Vehicle)
                    WITH l, a, v1, td, v2, r1, r2, r3, r4
                    LIMIT $limit
                    RETURN 
                        collect(DISTINCT l) as leads,
                        collect(DISTINCT a) as appointments,
                        collect(DISTINCT td) as test_drives,
                        collect(DISTINCT v1) + collect(DISTINCT v2) as vehicles,
                        collect(DISTINCT r1) as r1_rels,
                        collect(DISTINCT r2) as r2_rels,
                        collect(DISTINCT r3) as r3_rels,
                        collect(DISTINCT r4) as r4_rels
                """
            
            # ═══════════════════════════════════════════════════════════
            # EXECUTE QUERY
            # ═══════════════════════════════════════════════════════════
            result = session.run(query, limit=limit).single()
            
            if not result:
                logger.warning("⚠️ Query returned no results")
                return nodes, edges, stats
            
            # ═══════════════════════════════════════════════════════════
            # PROCESS LEAD NODES
            # ═══════════════════════════════════════════════════════════
            lead_nodes = result.get('leads', [])
            for lead in lead_nodes:
                if lead is not None:
                    node_id = lead.get('id', 'unknown')
                    nodes.append({
                        'id': node_id,
                        'label': lead.get('name', 'Unknown Lead'),
                        'type': 'Lead',
                        'data': {
                            'email': lead.get('email', ''),
                            'phone': lead.get('phone', ''),
                            'city': lead.get('city', ''),
                            'budget': lead.get('budget', 0),
                            'status': lead.get('status', 'warm'),
                            'sentiment': lead.get('sentiment', 'neutral'),
                            'interest': lead.get('interest', '')
                        }
                    })
                    stats['leads'] += 1
            
            # ═══════════════════════════════════════════════════════════
            # PROCESS VEHICLE NODES
            # ═══════════════════════════════════════════════════════════
            vehicle_nodes = result.get('vehicles', [])
            seen_vehicles = set()
            
            for vehicle in vehicle_nodes:
                if vehicle is not None:
                    vehicle_id = vehicle.get('id', 'unknown')
                    
                    # Avoid duplicates
                    if vehicle_id in seen_vehicles:
                        continue
                    seen_vehicles.add(vehicle_id)
                    
                    make = vehicle.get('make', 'Unknown')
                    model = vehicle.get('model', 'Model')
                    
                    nodes.append({
                        'id': vehicle_id,
                        'label': f"{make} {model}",
                        'type': 'Vehicle',
                        'data': {
                            'make': make,
                            'model': model,
                            'year': vehicle.get('year', ''),
                            'price': vehicle.get('price', 0),
                            'stock': vehicle.get('stock', 0)
                        }
                    })
                    stats['vehicles'] += 1
            
            # ═══════════════════════════════════════════════════════════
            # PROCESS APPOINTMENT NODES
            # ═══════════════════════════════════════════════════════════
            appointment_nodes = result.get('appointments', [])
            for appt in appointment_nodes:
                if appt is not None:
                    appt_id = appt.get('id', 'unknown')
                    
                    # Format date
                    appt_date = appt.get('date', '')
                    if hasattr(appt_date, 'to_native'):
                        appt_date = appt_date.to_native().strftime('%Y-%m-%d')
                    elif hasattr(appt_date, 'strftime'):
                        appt_date = appt_date.strftime('%Y-%m-%d')
                    else:
                        appt_date = str(appt_date)
                    
                    nodes.append({
                        'id': appt_id,
                        'label': f"Appointment {appt_date}",
                        'type': 'Appointment',
                        'data': {
                            'customer_name': appt.get('customer_name', ''),
                            'date': appt_date,
                            'time': appt.get('time', ''),
                            'status': appt.get('status', 'pending'),
                            'type': appt.get('type', 'Test Drive')
                        }
                    })
                    stats['appointments'] += 1
            
            # ═══════════════════════════════════════════════════════════
            # PROCESS TEST DRIVE NODES
            # ═══════════════════════════════════════════════════════════
            test_drive_nodes = result.get('test_drives', [])
            for td in test_drive_nodes:
                if td is not None:
                    td_id = td.get('id', 'unknown')
                    
                    # Format date
                    td_date = td.get('date', '')
                    if hasattr(td_date, 'to_native'):
                        td_date = td_date.to_native().strftime('%Y-%m-%d')
                    elif hasattr(td_date, 'strftime'):
                        td_date = td_date.strftime('%Y-%m-%d')
                    else:
                        td_date = str(td_date)
                    
                    nodes.append({
                        'id': td_id,
                        'label': f"Test Drive {td_date}",
                        'type': 'TestDrive',
                        'data': {
                            'customer_name': td.get('customer_name', ''),
                            'date': td_date,
                            'time': td.get('time', ''),
                            'status': td.get('status', 'scheduled')
                        }
                    })
                    stats['test_drives'] += 1
            
            # ═══════════════════════════════════════════════════════════
            # PROCESS RELATIONSHIPS
            # ═══════════════════════════════════════════════════════════
            
            # Lead -> Appointment (HAS_APPOINTMENT)
            r1_rels = result.get('r1_rels', [])
            for rel in r1_rels:
                if rel is not None:
                    source_node = rel.start_node
                    target_node = rel.end_node
                    
                    edges.append({
                        'source': source_node.get('id', 'unknown'),
                        'target': target_node.get('id', 'unknown'),
                        'type': 'HAS_APPOINTMENT'
                    })
                    stats['total_edges'] += 1
            
            # Appointment -> Vehicle (FOR_VEHICLE)
            r2_rels = result.get('r2_rels', [])
            for rel in r2_rels:
                if rel is not None:
                    source_node = rel.start_node
                    target_node = rel.end_node
                    
                    edges.append({
                        'source': source_node.get('id', 'unknown'),
                        'target': target_node.get('id', 'unknown'),
                        'type': 'FOR_VEHICLE'
                    })
                    stats['total_edges'] += 1
            
            # Lead -> TestDrive (BOOKED_TEST_DRIVE)
            r3_rels = result.get('r3_rels', [])
            for rel in r3_rels:
                if rel is not None:
                    source_node = rel.start_node
                    target_node = rel.end_node
                    
                    edges.append({
                        'source': source_node.get('id', 'unknown'),
                        'target': target_node.get('id', 'unknown'),
                        'type': 'BOOKED_TEST_DRIVE'
                    })
                    stats['total_edges'] += 1
            
            # TestDrive -> Vehicle (FOR_VEHICLE)
            r4_rels = result.get('r4_rels', [])
            for rel in r4_rels:
                if rel is not None:
                    source_node = rel.start_node
                    target_node = rel.end_node
                    
                    edges.append({
                        'source': source_node.get('id', 'unknown'),
                        'target': target_node.get('id', 'unknown'),
                        'type': 'FOR_VEHICLE'
                    })
                    stats['total_edges'] += 1
            
            stats['total_nodes'] = len(nodes)
            
            logger.info(f"✅ Graph data retrieved: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
            
    except Exception as e:
        logger.error(f"❌ Error fetching graph data: {e}", exc_info=True)
    
    return nodes, edges, stats


def generate_d3_visualization(nodes: List[Dict], edges: List[Dict], stats: Dict) -> str:
    """
    Generate D3.js force-directed graph HTML
    
    Args:
        nodes: List of node dictionaries
        edges: List of edge dictionaries
        stats: Statistics dictionary
        
    Returns:
        HTML string with embedded D3.js visualization
    """
    
    # Handle empty graph
    if not nodes:
        return """
        <div style="padding: 100px; text-align: center; color: #999; font-size: 18px;">
            <div style="font-size: 48px; margin-bottom: 20px;">📊</div>
            <div>No nodes found in the graph</div>
            <div style="font-size: 14px; margin-top: 10px;">Try adjusting the filter or increasing the limit</div>
        </div>
        """
    
    # Convert to JSON for JavaScript - escape for safe embedding
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    
    # Build HTML with string concatenation to avoid f-string conflicts with JavaScript
    html = """
    <div id="graph-container" style="position: relative; width: 100%; height: 800px; border: 2px solid #e0e0e0; border-radius: 12px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); overflow: hidden;">
        
        <!-- Statistics Panel -->
        <div id="stats-panel" style="position: absolute; top: 20px; left: 20px; background: rgba(255,255,255,0.95); padding: 15px 20px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #2c3e50;">📊 Graph Statistics</h3>
            <div style="font-size: 13px; color: #555;">
                <div>🟢 <strong>Leads:</strong> <span id="stat-leads">""" + str(stats.get('leads', 0)) + """</span></div>
                <div>🔵 <strong>Vehicles:</strong> <span id="stat-vehicles">""" + str(stats.get('vehicles', 0)) + """</span></div>
                <div>🟠 <strong>Appointments:</strong> <span id="stat-appointments">""" + str(stats.get('appointments', 0)) + """</span></div>
                <div>🟣 <strong>Test Drives:</strong> <span id="stat-test-drives">""" + str(stats.get('test_drives', 0)) + """</span></div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd;">
                    <strong>Total Nodes:</strong> """ + str(stats.get('total_nodes', 0)) + """<br>
                    <strong>Total Edges:</strong> """ + str(stats.get('total_edges', 0)) + """
                </div>
            </div>
        </div>
        
        <!-- Legend -->
        <div id="legend" style="position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.95); padding: 15px 20px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 1000; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #2c3e50;">🗺️ Legend</h3>
            <div style="font-size: 13px;">
                <div style="margin: 5px 0;">
                    <span style="display: inline-block; width: 16px; height: 16px; background: #27ae60; border-radius: 50%; margin-right: 8px;"></span>
                    <strong>Lead</strong> (Customer)
                </div>
                <div style="margin: 5px 0;">
                    <span style="display: inline-block; width: 16px; height: 16px; background: #3498db; border-radius: 50%; margin-right: 8px;"></span>
                    <strong>Vehicle</strong>
                </div>
                <div style="margin: 5px 0;">
                    <span style="display: inline-block; width: 16px; height: 16px; background: #e67e22; border-radius: 50%; margin-right: 8px;"></span>
                    <strong>Appointment</strong>
                </div>
                <div style="margin: 5px 0;">
                    <span style="display: inline-block; width: 16px; height: 16px; background: #9b59b6; border-radius: 50%; margin-right: 8px;"></span>
                    <strong>Test Drive</strong>
                </div>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 11px; color: #666;">
                    <div>💡 <em>Drag</em> nodes to rearrange</div>
                    <div>💡 <em>Scroll</em> to zoom</div>
                    <div>💡 <em>Click</em> nodes for details</div>
                    <div>💡 <em>Double-click</em> to reset</div>
                </div>
            </div>
        </div>
        
        <!-- Details Panel (hidden by default) -->
        <div id="details-panel" style="display: none; position: absolute; bottom: 20px; left: 20px; right: 20px; background: rgba(255,255,255,0.98); padding: 20px; border-radius: 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.2); z-index: 1000; font-family: Arial, sans-serif; max-width: 600px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 id="details-title" style="margin: 0; font-size: 18px; color: #2c3e50;"></h3>
                <button onclick="document.getElementById('details-panel').style.display='none'" style="background: #e74c3c; color: white; border: none; padding: 5px 12px; border-radius: 5px; cursor: pointer; font-size: 14px;">✕ Close</button>
            </div>
            <div id="details-content" style="font-size: 14px; color: #555; line-height: 1.6;"></div>
        </div>
        
        <!-- SVG Canvas -->
        <svg id="graph-svg" style="width: 100%; height: 100%;"></svg>
    </div>
    
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        // Parse data from Python
        const graphData = {
            nodes: """ + nodes_json + """,
            links: """ + edges_json + """,
            stats: """ + json.dumps(stats) + """
        };
        
        console.log('📊 Graph Data Loaded:', graphData);
        
        // Clone nodes for D3 (D3 mutates the array)
        const nodes = JSON.parse(JSON.stringify(graphData.nodes));
        const links = JSON.parse(JSON.stringify(graphData.links));
        
        // SVG dimensions
        const container = document.getElementById('graph-container');
        const width = container.clientWidth || 1200;
        const height = container.clientHeight || 800;
        
        console.log('📐 Container dimensions:', width, height);
        
        // Create SVG
        const svg = d3.select('#graph-svg')
            .attr('width', width)
            .attr('height', height);
        
        const g = svg.append('g');
        
        // Define color scheme
        const colorMap = {{
            'Lead': '#27ae60',      // Green
            'Vehicle': '#3498db',   // Blue
            'Appointment': '#e67e22', // Orange
            'TestDrive': '#9b59b6'  // Purple
        }};
        
        // Define size scheme
        const sizeMap = {{
            'Lead': 18,
            'Vehicle': 15,
            'Appointment': 13,
            'TestDrive': 13
        }};
        
        // Initialize positions to center (prevent off-screen nodes)
        nodes.forEach(node => {{
            node.x = width / 2 + (Math.random() - 0.5) * 100;
            node.y = height / 2 + (Math.random() - 0.5) * 100;
        }});
        
        console.log('🎯 Initialized', nodes.length, 'nodes at center');
        
        // ═══════════════════════════════════════════════════════════
        // FORCE SIMULATION
        // ═══════════════════════════════════════════════════════════
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links)
                .id(d => d.id)
                .distance(100))
            .force('charge', d3.forceManyBody()
                .strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide()
                .radius(d => (sizeMap[d.type] || 15) + 8))
            .force('x', d3.forceX(width / 2).strength(0.1))
            .force('y', d3.forceY(height / 2).strength(0.1));
        
        // ═══════════════════════════════════════════════════════════
        // DRAW LINKS FIRST (so they appear behind nodes)
        // ═══════════════════════════════════════════════════════════
        const link = g.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke', '#95a5a6')
            .attr('stroke-width', 2)
            .attr('stroke-opacity', 0.6)
            .attr('x1', d => d.source.x || width/2)
            .attr('y1', d => d.source.y || height/2)
            .attr('x2', d => d.target.x || width/2)
            .attr('y2', d => d.target.y || height/2);
        
        console.log('🔗 Drew', links.length, 'links');
        
        // Link labels
        const linkLabel = g.append('g')
            .attr('class', 'link-labels')
            .selectAll('text')
            .data(links)
            .join('text')
            .attr('font-size', 9)
            .attr('fill', '#7f8c8d')
            .attr('text-anchor', 'middle')
            .attr('dy', -3)
            .text(d => d.type)
            .style('pointer-events', 'none');
        
        // ═══════════════════════════════════════════════════════════
        // DRAW NODES
        // ═══════════════════════════════════════════════════════════
        const node = g.append('g')
            .attr('class', 'nodes')
            .selectAll('circle')
            .data(nodes)
            .join('circle')
            .attr('r', d => sizeMap[d.type] || 15)
            .attr('fill', d => colorMap[d.type] || '#95a5a6')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2.5)
            .attr('cx', d => d.x)
            .attr('cy', d => d.y)
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended))
            .on('mouseover', function(event, d) {{
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('r', (sizeMap[d.type] || 15) * 1.4)
                    .attr('stroke-width', 3.5);
            }})
            .on('mouseout', function(event, d) {{
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('r', sizeMap[d.type] || 15)
                    .attr('stroke-width', 2.5);
            }})
            .on('click', showDetails);
        
        console.log('⭕ Drew', nodes.length, 'nodes');
        
        // Node labels
        const label = g.append('g')
            .attr('class', 'labels')
            .selectAll('text')
            .data(nodes)
            .join('text')
            .attr('font-size', 11)
            .attr('font-weight', 'bold')
            .attr('fill', '#2c3e50')
            .attr('text-anchor', 'middle')
            .attr('dy', -23)
            .attr('x', d => d.x)
            .attr('y', d => d.y)
            .text(d => d.label && d.label.length > 20 ? d.label.substring(0, 17) + '...' : d.label)
            .style('pointer-events', 'none');
        
        // ═══════════════════════════════════════════════════════════
        // SIMULATION TICK - UPDATE POSITIONS
        // ═══════════════════════════════════════════════════════════
        simulation.on('tick', () => {{
            // Update links
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            // Update link labels
            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);
            
            // Update nodes
            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);
            
            // Update node labels
            label
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        }});
        
        // ═══════════════════════════════════════════════════════════
        // DRAG FUNCTIONS
        // ═══════════════════════════════════════════════════════════
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        // ═══════════════════════════════════════════════════════════
        // SHOW NODE DETAILS
        // ═══════════════════════════════════════════════════════════
        function showDetails(event, d) {{
            const panel = document.getElementById('details-panel');
            const title = document.getElementById('details-title');
            const content = document.getElementById('details-content');
            
            // Set title with colored bullet
            const color = colorMap[d.type] || '#95a5a6';
            title.innerHTML = `<span style="color: ${{color}};">●</span> ${{d.type}}: ${{d.label}}`;
            
            // Build content HTML
            let html = '<div style="display: grid; grid-template-columns: 140px 1fr; gap: 8px;">';
            
            if (d.data) {{
                for (const [key, value] of Object.entries(d.data)) {{
                    if (value !== null && value !== undefined && value !== '') {{
                        const displayKey = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
                        html += `<div style="font-weight: bold; color: #555;">${{displayKey}}:</div>`;
                        html += `<div style="color: #333;">${{value}}</div>`;
                    }}
                }}
            }}
            
            html += '</div>';
            content.innerHTML = html;
            
            // Show panel with animation
            panel.style.display = 'block';
            panel.style.animation = 'slideUp 0.3s ease-out';
        }}
        
        // ═══════════════════════════════════════════════════════════
        // ZOOM & PAN
        // ═══════════════════════════════════════════════════════════
        const zoom = d3.zoom()
            .scaleExtent([0.2, 5])
            .on('zoom', (event) => {{
                g.attr('transform', event.transform);
            }});
        
        svg.call(zoom);
        
        // Double-click to reset view
        svg.on('dblclick.zoom', () => {{
            svg.transition()
                .duration(750)
                .call(zoom.transform, d3.zoomIdentity);
        }});
        
        // Initial render complete
        console.log('✅ Knowledge Graph rendered successfully');
        console.log('📊 Stats:', graphData.stats);
        
        // Warm start - let simulation run for a bit
        simulation.alpha(1).restart();
    </script>
    
    <style>
        @keyframes slideUp {{
            from {{ transform: translateY(20px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
    </style>
    """
    
    return html