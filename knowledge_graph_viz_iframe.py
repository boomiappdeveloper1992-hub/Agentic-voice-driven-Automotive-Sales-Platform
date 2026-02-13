"""
knowledge_graph_viz_iframe.py - Interactive D3 Graph via iframe

This version generates the graph as a proper HTML file and loads it via iframe,
bypassing Gradio's quirks mode limitation.
"""

import logging
from typing import Dict, List, Tuple
import json
import os
import base64
from datetime import datetime

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
            
            # Build query based on filter type
            if filter_type == "leads":
                query = """
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
                    // Get all test drive bookings
                    MATCH (td)
                    WHERE td:TestDrive OR td:TestDriveBooking
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
                    // Get a balanced sample of all node types
                    // First, get leads with relationships
                    CALL {
                        MATCH (l:Lead)
                        WHERE EXISTS((l)-[:HAS_APPOINTMENT]->()) OR EXISTS((l)-[:BOOKED_TEST_DRIVE]->())
                        RETURN l
                        LIMIT $limit
                    }
                    
                    // Get their appointments and test drives
                    OPTIONAL MATCH (l)-[r1:HAS_APPOINTMENT]->(a:Appointment)
                    OPTIONAL MATCH (a)-[r2:FOR_VEHICLE]->(v1:Vehicle)
                    OPTIONAL MATCH (l)-[r3:BOOKED_TEST_DRIVE]->(td:TestDrive)
                    OPTIONAL MATCH (td)-[r4:FOR_VEHICLE]->(v2:Vehicle)
                    OPTIONAL MATCH (l)-[r5:BOOKED_TEST_DRIVE]->(tdb:TestDriveBooking)
                    OPTIONAL MATCH (tdb)-[r6:FOR_VEHICLE]->(v3:Vehicle)
                    
                    RETURN 
                        collect(DISTINCT l) as leads,
                        collect(DISTINCT a) as appointments,
                        collect(DISTINCT td) + collect(DISTINCT tdb) as test_drives,
                        collect(DISTINCT v1) + collect(DISTINCT v2) + collect(DISTINCT v3) as vehicles,
                        collect(DISTINCT r1) as r1_rels,
                        collect(DISTINCT r2) as r2_rels,
                        collect(DISTINCT r3) + collect(DISTINCT r5) as r3_rels,
                        collect(DISTINCT r4) + collect(DISTINCT r6) as r4_rels
                """
            
            result = session.run(query, limit=limit).single()
            
            if not result:
                logger.warning("⚠️ Query returned no results")
                return nodes, edges, stats
            
            # Process lead nodes
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
            
            # Process vehicle nodes
            vehicle_nodes = result.get('vehicles', [])
            seen_vehicles = set()
            
            for vehicle in vehicle_nodes:
                if vehicle is not None:
                    vehicle_id = vehicle.get('id', 'unknown')
                    
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
            
            # Process appointment nodes
            appointment_nodes = result.get('appointments', [])
            for appt in appointment_nodes:
                if appt is not None:
                    appt_id = appt.get('id', 'unknown')
                    
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
            
            # Process test drive nodes (both TestDrive and TestDriveBooking)
            test_drive_nodes = result.get('test_drives', [])
            for td in test_drive_nodes:
                if td is not None:
                    td_id = td.get('id', 'unknown')
                    
                    # Get date - try different property names
                    td_date = td.get('date', td.get('appointment_date', ''))
                    if hasattr(td_date, 'to_native'):
                        td_date = td_date.to_native().strftime('%Y-%m-%d')
                    elif hasattr(td_date, 'strftime'):
                        td_date = td_date.strftime('%Y-%m-%d')
                    else:
                        td_date = str(td_date)
                    
                    # Determine node type from labels
                    node_labels = td.labels if hasattr(td, 'labels') else set()
                    if 'TestDriveBooking' in node_labels:
                        node_type = 'TestDriveBooking'
                        label_prefix = 'Booking'
                    else:
                        node_type = 'TestDrive'
                        label_prefix = 'Test Drive'
                    
                    # Get customer name - try different property names
                    customer_name = td.get('customer_name', td.get('name', ''))
                    
                    nodes.append({
                        'id': td_id,
                        'label': f"{label_prefix} {td_date}",
                        'type': node_type,
                        'data': {
                            'customer_name': customer_name,
                            'customer_email': td.get('customer_email', ''),
                            'customer_phone': td.get('customer_phone', ''),
                            'date': td_date,
                            'time': td.get('time', td.get('appointment_time', '')),
                            'status': td.get('status', 'scheduled'),
                            'vehicle_interest': td.get('vehicle_interest', '')
                        }
                    })
                    stats['test_drives'] += 1
            
            # Process relationships
            for rel in result.get('r1_rels', []):
                if rel is not None:
                    edges.append({
                        'source': rel.start_node.get('id'),
                        'target': rel.end_node.get('id'),
                        'type': 'HAS_APPOINTMENT'
                    })
                    stats['total_edges'] += 1
            
            for rel in result.get('r2_rels', []):
                if rel is not None:
                    edges.append({
                        'source': rel.start_node.get('id'),
                        'target': rel.end_node.get('id'),
                        'type': 'FOR_VEHICLE'
                    })
                    stats['total_edges'] += 1
            
            for rel in result.get('r3_rels', []):
                if rel is not None:
                    edges.append({
                        'source': rel.start_node.get('id'),
                        'target': rel.end_node.get('id'),
                        'type': 'BOOKED_TEST_DRIVE'
                    })
                    stats['total_edges'] += 1
            
            for rel in result.get('r4_rels', []):
                if rel is not None:
                    edges.append({
                        'source': rel.start_node.get('id'),
                        'target': rel.end_node.get('id'),
                        'type': 'FOR_VEHICLE'
                    })
                    stats['total_edges'] += 1
            
            stats['total_nodes'] = len(nodes)
            
            logger.info(f"✅ Graph data retrieved: {stats['total_nodes']} nodes, {stats['total_edges']} edges")
            
    except Exception as e:
        logger.error(f"❌ Error fetching graph data: {e}", exc_info=True)
    
    return nodes, edges, stats


def generate_graph_iframe(nodes: List[Dict], edges: List[Dict], stats: Dict) -> str:
    """
    Generate iframe with embedded D3.js graph using data URL
    
    This bypasses Gradio's quirks mode by creating a proper HTML document
    and loading it via iframe with a data: URL
    
    Args:
        nodes: List of node dictionaries
        edges: List of edge dictionaries
        stats: Statistics dictionary
        
    Returns:
        HTML string with iframe containing the graph
    """
    
    if not nodes:
        return """
        <div style="padding: 60px; text-align: center; background: white; border-radius: 12px;">
            <div style="font-size: 64px; margin-bottom: 20px;">📊</div>
            <h2 style="color: #666;">No Graph Data Found</h2>
            <p style="color: #999;">Try adjusting the filter or increasing the limit</p>
        </div>
        """
    
    # Build complete HTML document with DOCTYPE
    graph_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            overflow: hidden;
        }
        #graph-container {
            width: 100vw;
            height: 100vh;
            position: relative;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        #stats-panel {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(255,255,255,0.95);
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
        }
        #legend {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.95);
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
        }
        #details-panel {
            display: none;
            position: absolute;
            bottom: 20px;
            left: 20px;
            right: 20px;
            max-width: 600px;
            background: rgba(255,255,255,0.98);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
            z-index: 1000;
        }
        .close-btn {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 5px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div id="graph-container">
        <div id="stats-panel">
            <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #2c3e50;">📊 Graph Statistics</h3>
            <div style="font-size: 13px; color: #555;">
                <div>🟢 <strong>Leads:</strong> """ + str(stats['leads']) + """</div>
                <div>🔵 <strong>Vehicles:</strong> """ + str(stats['vehicles']) + """</div>
                <div>🟠 <strong>Appointments:</strong> """ + str(stats['appointments']) + """</div>
                <div>🟣 <strong>Test Drives:</strong> """ + str(stats['test_drives']) + """</div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #ddd;">
                    <strong>Total Nodes:</strong> """ + str(stats['total_nodes']) + """<br>
                    <strong>Total Edges:</strong> """ + str(stats['total_edges']) + """
                </div>
            </div>
        </div>
        
        <div id="legend">
            <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #2c3e50;">🗺️ Legend</h3>
            <div style="font-size: 13px;">
                <div style="margin: 5px 0;">
                    <span style="display: inline-block; width: 16px; height: 16px; background: #27ae60; border-radius: 50%; margin-right: 8px;"></span>
                    <strong>Lead</strong>
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
                <div style="margin: 5px 0;">
                    <span style="display: inline-block; width: 16px; height: 16px; background: #8e44ad; border-radius: 50%; margin-right: 8px;"></span>
                    <strong>Booking</strong>
                </div>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 11px; color: #666;">
                    <div>💡 <em>Drag</em> nodes</div>
                    <div>💡 <em>Scroll</em> to zoom</div>
                    <div>💡 <em>Click</em> for details</div>
                </div>
            </div>
        </div>
        
        <div id="details-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 id="details-title" style="margin: 0; font-size: 18px; color: #2c3e50;"></h3>
                <button class="close-btn" onclick="document.getElementById('details-panel').style.display='none'">✕ Close</button>
            </div>
            <div id="details-content" style="font-size: 14px; color: #555;"></div>
        </div>
        
        <svg id="graph-svg" style="width: 100%; height: 100%;"></svg>
    </div>
    
    <script>
        const nodes = """ + json.dumps(nodes) + """;
        const links = """ + json.dumps(edges) + """;
        
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        const svg = d3.select('#graph-svg')
            .attr('width', width)
            .attr('height', height);
        
        const g = svg.append('g');
        
        const colorMap = {
            'Lead': '#27ae60',
            'Vehicle': '#3498db',
            'Appointment': '#e67e22',
            'TestDrive': '#9b59b6',
            'TestDriveBooking': '#8e44ad'
        };
        
        const sizeMap = {
            'Lead': 18,
            'Vehicle': 15,
            'Appointment': 13,
            'TestDrive': 13,
            'TestDriveBooking': 13
        };
        
        nodes.forEach(node => {
            node.x = width / 2 + (Math.random() - 0.5) * 100;
            node.y = height / 2 + (Math.random() - 0.5) * 100;
        });
        
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => sizeMap[d.type] + 8));
        
        const link = g.append('g')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke', '#95a5a6')
            .attr('stroke-width', 2)
            .attr('stroke-opacity', 0.6);
        
        const linkLabel = g.append('g')
            .selectAll('text')
            .data(links)
            .join('text')
            .attr('font-size', 9)
            .attr('fill', '#7f8c8d')
            .attr('text-anchor', 'middle')
            .text(d => d.type)
            .style('pointer-events', 'none');
        
        const node = g.append('g')
            .selectAll('circle')
            .data(nodes)
            .join('circle')
            .attr('r', d => sizeMap[d.type])
            .attr('fill', d => colorMap[d.type])
            .attr('stroke', '#fff')
            .attr('stroke-width', 2.5)
            .style('cursor', 'pointer')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended))
            .on('mouseover', function(event, d) {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('r', sizeMap[d.type] * 1.4);
            })
            .on('mouseout', function(event, d) {
                d3.select(this)
                    .transition()
                    .duration(200)
                    .attr('r', sizeMap[d.type]);
            })
            .on('click', showDetails);
        
        const label = g.append('g')
            .selectAll('text')
            .data(nodes)
            .join('text')
            .attr('font-size', 11)
            .attr('font-weight', 'bold')
            .attr('fill', '#2c3e50')
            .attr('text-anchor', 'middle')
            .attr('dy', -23)
            .text(d => d.label.length > 20 ? d.label.substring(0, 17) + '...' : d.label)
            .style('pointer-events', 'none');
        
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);
            
            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);
            
            label
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        });
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        function showDetails(event, d) {
            const panel = document.getElementById('details-panel');
            const title = document.getElementById('details-title');
            const content = document.getElementById('details-content');
            
            title.innerHTML = '<span style="color: ' + colorMap[d.type] + ';">●</span> ' + d.type + ': ' + d.label;
            
            let html = '<div style="display: grid; grid-template-columns: 140px 1fr; gap: 8px;">';
            if (d.data) {
                for (const [key, value] of Object.entries(d.data)) {
                    if (value) {
                        const displayKey = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
                        html += '<div style="font-weight: bold;">' + displayKey + ':</div><div>' + value + '</div>';
                    }
                }
            }
            html += '</div>';
            content.innerHTML = html;
            panel.style.display = 'block';
        }
        
        const zoom = d3.zoom()
            .scaleExtent([0.2, 5])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });
        
        svg.call(zoom);
        
        svg.on('dblclick.zoom', () => {
            svg.transition()
                .duration(750)
                .call(zoom.transform, d3.zoomIdentity);
        });
    </script>
</body>
</html>"""
    
    # Encode HTML as data URL
    encoded = base64.b64encode(graph_html.encode('utf-8')).decode('utf-8')
    data_url = f"data:text/html;base64,{encoded}"
    
    # Return iframe with the graph
    iframe_html = f"""
    <iframe 
        src="{data_url}"
        style="width: 100%; height: 850px; border: 2px solid #e0e0e0; border-radius: 12px; background: white;"
        frameborder="0"
        sandbox="allow-scripts allow-same-origin"
    ></iframe>
    """
    
    return iframe_html