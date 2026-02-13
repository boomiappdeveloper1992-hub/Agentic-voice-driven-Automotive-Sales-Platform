"""
Neo4j Knowledge Graph Handler - Enhanced with Retry Logic
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired
import time
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jHandler:
    """Production Neo4j handler with retry logic and timeout handling"""
    
    def __init__(self):
        """Initialize Neo4j connection with enhanced configuration"""
        self.uri = "neo4j+s://50ad6469.databases.neo4j.io"
        self.username = "neo4j"
        self.password = "xr2vCSD0RHLbfb3Bzzlpds04tm3fARSgvGHqZRkfevc"
        self.database = "neo4j"
        
        try:
            # Enhanced driver configuration
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
                connection_timeout=30,
                keep_alive=True,
                max_transaction_retry_time=30
            )
            
            # Test connection with retry
            self._verify_connectivity_with_retry()
            logger.info("✅ Successfully connected to Neo4j Aura")
            
            self._initialize_schema()
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            raise
    
    def _verify_connectivity_with_retry(self, max_retries: int = 3):
        """Verify connection with retry logic"""
        for attempt in range(max_retries):
            try:
                with self.driver.session(database=self.database) as session:
                    result = session.run("RETURN 1 as num", timeout=10.0)
                    record = result.single()
                    if record and record["num"] == 1:
                        logger.info("✅ Neo4j connectivity verified")
                        return
            except Exception as e:
                logger.warning(f"⚠️ Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def execute_with_retry(self, query: str, params: Dict = None, max_retries: int = 3, timeout: float = 30.0):
        """
        Execute query with automatic retry on timeout
        
        Args:
            query: Cypher query
            params: Query parameters
            max_retries: Maximum retry attempts
            timeout: Query timeout in seconds
            
        Returns:
            Query results or None on failure
        """
        params = params or {}
        
        for attempt in range(max_retries):
            try:
                with self.driver.session(database=self.database) as session:
                    result = session.run(query, params, timeout=timeout)
                    return list(result)
                    
            except (ServiceUnavailable, SessionExpired) as e:
                logger.warning(f"⚠️ Query attempt {attempt + 1}/{max_retries} failed: {type(e).__name__}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Query failed after {max_retries} attempts")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                return None
        
        return None
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def _initialize_schema(self):
        """Initialize database schema and constraints"""
        queries = [
            "CREATE CONSTRAINT lead_id IF NOT EXISTS FOR (l:Lead) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT vehicle_id IF NOT EXISTS FOR (v:Vehicle) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT appointment_id IF NOT EXISTS FOR (a:Appointment) REQUIRE a.id IS UNIQUE",
            "CREATE INDEX lead_status IF NOT EXISTS FOR (l:Lead) ON (l.status)",
            "CREATE INDEX vehicle_make IF NOT EXISTS FOR (v:Vehicle) ON (v.make)",
            "CREATE INDEX vehicle_price IF NOT EXISTS FOR (v:Vehicle) ON (v.price)",
        ]
        
        for query in queries:
            try:
                self.execute_with_retry(query, timeout=10.0)
            except Exception as e:
                logger.debug(f"Schema creation (may already exist): {e}")
        
        logger.info("Database schema initialized")
    
    def seed_initial_data(self):
        """Seed database with initial data"""
        with self.driver.session(database=self.database) as session:
            # Create vehicles with REAL working images
            vehicles = [
                {
                    'id': 'V001', 'make': 'Toyota', 'model': 'Land Cruiser', 
                    'year': 2024, 'price': 180000, 
                    'features': ['4WD', 'V8 Engine', 'Leather Seats', '7 Seater'],
                    'stock': 5, 
                    'image': 'https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=400',
                    'description': 'Legendary SUV with unmatched off-road capability and luxury comfort'
                },
                {
                    'id': 'V002', 'make': 'BMW', 'model': 'X5', 
                    'year': 2024, 'price': 320000,
                    'features': ['AWD', 'Hybrid', 'Premium Sound', 'Panoramic Roof'],
                    'stock': 3,
                    'image': 'https://images.unsplash.com/photo-1555215695-3004980ad54e?w=400',
                    'description': 'Premium SAV with cutting-edge technology and dynamic performance'
                },
                {
                    'id': 'V003', 'make': 'Mercedes', 'model': 'GLE', 
                    'year': 2024, 'price': 350000,
                    'features': ['4MATIC', 'MBUX System', 'Air Suspension', 'AMG Line'],
                    'stock': 2,
                    'image': 'https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=400',
                    'description': 'Sophisticated SUV combining luxury, technology, and performance'
                },
                {
                    'id': 'V004', 'make': 'Honda', 'model': 'CR-V', 
                    'year': 2024, 'price': 95000,
                    'features': ['AWD', 'Honda Sensing', 'Spacious Interior', 'Fuel Efficient'],
                    'stock': 8,
                    'image': 'https://images.unsplash.com/photo-1619767886558-efdc259cde1a?w=400',
                    'description': 'Reliable and practical SUV perfect for families'
                },
                {
                    'id': 'V005', 'make': 'Tesla', 'model': 'Model Y', 
                    'year': 2024, 'price': 280000,
                    'features': ['Electric', 'Autopilot', 'Long Range', 'Premium Interior'],
                    'stock': 4,
                    'image': 'https://images.unsplash.com/photo-1560958089-b8a1929cea89?w=400',
                    'description': 'All-electric SUV with incredible performance and technology'
                }
            ]
            
            for vehicle in vehicles:
                session.run("""
                    MERGE (v:Vehicle {id: $id})
                    SET v.make = $make,
                        v.model = $model,
                        v.year = $year,
                        v.price = $price,
                        v.features = $features,
                        v.stock = $stock,
                        v.image = $image,
                        v.description = $description,
                        v.created_at = datetime()
                """, **vehicle)
            
            # Create leads
            leads = [
                {
                    'id': 'L001', 'name': 'Ahmed Al Maktoum', 
                    'phone': '+971-50-123-4567', 'email': 'ahmed@email.com',
                    'city': 'Dubai', 'budget': 150000, 'interest': 'Toyota Land Cruiser',
                    'status': 'hot', 'sentiment': 'positive',
                    'notes': 'Very interested, wants test drive ASAP'
                },
                {
                    'id': 'L002', 'name': 'Fatima Hassan',
                    'phone': '+971-55-234-5678', 'email': 'fatima@email.com',
                    'city': 'Abu Dhabi', 'budget': 120000, 'interest': 'BMW X5',
                    'status': 'warm', 'sentiment': 'neutral',
                    'notes': 'Comparing options with other dealers'
                },
                {
                    'id': 'L003', 'name': 'Mohammed Ali',
                    'phone': '+971-52-345-6789', 'email': 'mohammed@email.com',
                    'city': 'Sharjah', 'budget': 200000, 'interest': 'Mercedes GLE',
                    'status': 'hot', 'sentiment': 'positive',
                    'notes': 'Ready to buy this week, cash buyer'
                },
                {
                    'id': 'L004', 'name': 'Sara Abdullah',
                    'phone': '+971-56-456-7890', 'email': 'sara@email.com',
                    'city': 'Dubai', 'budget': 90000, 'interest': 'Honda CR-V',
                    'status': 'cold', 'sentiment': 'negative',
                    'notes': 'Budget concerns, looking for financing options'
                },
                {
                    'id': 'L005', 'name': 'Khalid Rahman',
                    'phone': '+971-54-567-8901', 'email': 'khalid@email.com',
                    'city': 'Dubai', 'budget': 300000, 'interest': 'Tesla Model Y',
                    'status': 'warm', 'sentiment': 'positive',
                    'notes': 'Interested in electric vehicles, eco-conscious'
                }
            ]
            
            for lead in leads:
                session.run("""
                    MERGE (l:Lead {id: $id})
                    SET l.name = $name,
                        l.phone = $phone,
                        l.email = $email,
                        l.city = $city,
                        l.budget = $budget,
                        l.interest = $interest,
                        l.status = $status,
                        l.sentiment = $sentiment,
                        l.notes = $notes,
                        l.created_at = datetime(),
                        l.last_contact = date()
                """, **lead)
            
            # Create relationships between leads and vehicles
            relationships = [
                ('L001', 'V001', 'INTERESTED_IN', {'interest_level': 'high', 'priority': 1}),
                ('L002', 'V002', 'INTERESTED_IN', {'interest_level': 'medium', 'priority': 2}),
                ('L003', 'V003', 'INTERESTED_IN', {'interest_level': 'high', 'priority': 1}),
                ('L004', 'V004', 'INTERESTED_IN', {'interest_level': 'low', 'priority': 3}),
                ('L005', 'V005', 'INTERESTED_IN', {'interest_level': 'medium', 'priority': 2}),
            ]
            
            for lead_id, vehicle_id, rel_type, props in relationships:
                session.run("""
                    MATCH (l:Lead {id: $lead_id})
                    MATCH (v:Vehicle {id: $vehicle_id})
                    MERGE (l)-[r:INTERESTED_IN]->(v)
                    SET r.interest_level = $interest_level,
                        r.priority = $priority,
                        r.created_at = datetime()
                """, lead_id=lead_id, vehicle_id=vehicle_id, **props)
            
            logger.info("✅ Initial data seeded successfully")
    
    def get_all_leads(self) -> List[Dict]:
        """Retrieve all leads from Neo4j"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (l:Lead)
                OPTIONAL MATCH (l)-[:INTERESTED_IN]->(v:Vehicle)
                RETURN l, collect(v.make + ' ' + v.model) as vehicles
                ORDER BY l.created_at DESC
            """)
            
            leads = []
            for record in result:
                lead_node = record['l']
                leads.append({
                    'id': lead_node['id'],
                    'name': lead_node['name'],
                    'phone': lead_node['phone'],
                    'email': lead_node['email'],
                    'city': lead_node['city'],
                    'budget': lead_node['budget'],
                    'interest': lead_node.get('interest', 'N/A'),
                    'status': lead_node['status'],
                    'sentiment': lead_node['sentiment'],
                    'last_contact': str(lead_node.get('last_contact', 'N/A')),
                    'notes': lead_node.get('notes', ''),
                    'vehicles': record['vehicles']
                })
            
            return leads
    
    def get_hot_leads(self) -> List[Dict]:
        """Get only hot leads"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (l:Lead {status: 'hot'})
                OPTIONAL MATCH (l)-[:INTERESTED_IN]->(v:Vehicle)
                RETURN l, v
                ORDER BY l.created_at DESC
            """)
            
            leads = []
            for record in result:
                lead_node = record['l']
                vehicle_node = record.get('v')
                
                leads.append({
                    'id': lead_node['id'],
                    'name': lead_node['name'],
                    'phone': lead_node['phone'],
                    'email': lead_node['email'],
                    'city': lead_node['city'],
                    'budget': lead_node['budget'],
                    'interest': lead_node.get('interest', 'N/A'),
                    'status': lead_node['status'],
                    'sentiment': lead_node['sentiment'],
                    'last_contact': str(lead_node.get('last_contact', 'N/A')),
                    'notes': lead_node.get('notes', ''),
                    'vehicle_details': {
                        'make': vehicle_node['make'],
                        'model': vehicle_node['model'],
                        'price': vehicle_node['price']
                    } if vehicle_node else None
                })
            
            return leads
    
    def get_vehicles(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get vehicles with filters - WITH RETRY"""
        query = "MATCH (v:Vehicle) WHERE 1=1"
        params = {}
        
        if filters:
            if 'make' in filters:
                query += " AND toLower(v.make) CONTAINS toLower($make)"
                params['make'] = filters['make']
            if 'max_price' in filters:
                query += " AND v.price <= $max_price"
                params['max_price'] = filters['max_price']
            if 'min_price' in filters:
                query += " AND v.price >= $min_price"
                params['min_price'] = filters['min_price']
        
        query += " RETURN v ORDER BY v.price LIMIT 100"
        
        logger.info(f"🔍 Query: {query}")
        logger.info(f"📝 Params: {params}")
        
        results = self.execute_with_retry(query, params, timeout=20.0)
        
        if results is None:
            logger.warning("⚠️ Returning empty vehicle list due to connection issue")
            return []
        
        vehicles = []
        for record in results:
            v = record['v']
            vehicles.append({
                'id': v['id'],
                'make': v['make'],
                'model': v['model'],
                'year': v['year'],
                'price': v['price'],
                'features': v.get('features', []),
                'stock': v.get('stock', 0),
                'image': v.get('image', ''),
                'description': v.get('description', '')
            })
        
        return vehicles
    
    def search_vehicles_by_text(self, query: str) -> List[Dict]:
        """Search vehicles using text query - WITH RETRY"""
        cypher = """
            MATCH (v:Vehicle)
            WHERE toLower(v.make) CONTAINS toLower($query)
               OR toLower(v.model) CONTAINS toLower($query)
               OR any(feature IN v.features WHERE toLower(feature) CONTAINS toLower($query))
               OR toLower(v.description) CONTAINS toLower($query)
            RETURN v
            ORDER BY v.price
            LIMIT 50
        """
        
        results = self.execute_with_retry(cypher, {'query': query}, timeout=20.0)
        
        if results is None:
            return []
        
        vehicles = []
        for record in results:
            v = record['v']
            vehicles.append({
                'id': v['id'],
                'make': v['make'],
                'model': v['model'],
                'year': v['year'],
                'price': v['price'],
                'features': v.get('features', []),
                'stock': v.get('stock', 0),
                'image': v.get('image', ''),
                'description': v.get('description', '')
            })
        
        return vehicles
    
    def create_appointment(self, lead_id: str, vehicle_id: str, 
                          date: str, time: str, appointment_type: str) -> Dict:
        """Create appointment in Neo4j"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (l:Lead {id: $lead_id})
                MATCH (v:Vehicle {id: $vehicle_id})
                CREATE (a:Appointment {
                    id: randomUUID(),
                    date: date($date),
                    time: $time,
                    type: $appointment_type,
                    status: 'confirmed',
                    created_at: datetime()
                })
                CREATE (l)-[:HAS_APPOINTMENT]->(a)
                CREATE (a)-[:FOR_VEHICLE]->(v)
                RETURN a, l, v
            """, lead_id=lead_id, vehicle_id=vehicle_id, date=date, 
                time=time, appointment_type=appointment_type)
            
            record = result.single()
            if record:
                appt = record['a']
                lead = record['l']
                vehicle = record['v']
                
                return {
                    'success': True,
                    'appointment': {
                        'id': appt['id'],
                        'customer': lead['name'],
                        'date': str(appt['date']),
                        'time': appt['time'],
                        'type': appt['type'],
                        'vehicle': f"{vehicle['make']} {vehicle['model']}",
                        'status': appt['status']
                    }
                }
            
            return {'success': False, 'error': 'Failed to create appointment'}
    
    def get_appointments(self) -> List[Dict]:
        """Get all appointments"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (l:Lead)-[:HAS_APPOINTMENT]->(a:Appointment)-[:FOR_VEHICLE]->(v:Vehicle)
                RETURN a, l, v
                ORDER BY a.date DESC, a.time
            """)
            
            appointments = []
            for record in result:
                appt = record['a']
                lead = record['l']
                vehicle = record['v']
                
                appointments.append({
                    'id': appt['id'],
                    'lead_id': lead['id'],
                    'customer': lead['name'],
                    'date': str(appt['date']),
                    'time': appt['time'],
                    'type': appt['type'],
                    'vehicle': f"{vehicle['make']} {vehicle['model']}",
                    'status': appt['status']
                })
            
            return appointments
    
    def get_knowledge_graph_stats(self) -> Dict:
        """Get knowledge graph statistics"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (l:Lead) WITH count(l) as lead_count
                MATCH (v:Vehicle) WITH lead_count, count(v) as vehicle_count
                MATCH (a:Appointment) WITH lead_count, vehicle_count, count(a) as appt_count
                MATCH ()-[r]->() WITH lead_count, vehicle_count, appt_count, count(r) as rel_count
                RETURN lead_count, vehicle_count, appt_count, rel_count
            """)
            
            record = result.single()
            return {
                'leads': record['lead_count'],
                'vehicles': record['vehicle_count'],
                'appointments': record['appt_count'],
                'relationships': record['rel_count']
            }
    
    def get_graph_visualization_data(self) -> Dict:
        """Get data for graph visualization"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (l:Lead)-[r:INTERESTED_IN]->(v:Vehicle)
                OPTIONAL MATCH (l)-[:HAS_APPOINTMENT]->(a:Appointment)
                RETURN l, r, v, collect(a) as appointments
                LIMIT 50
            """)
            
            nodes = []
            edges = []
            node_ids = set()
            
            for record in result:
                lead = record['l']
                vehicle = record['v']
                rel = record['r']
                
                # Add lead node
                if lead['id'] not in node_ids:
                    nodes.append({
                        'id': lead['id'],
                        'label': lead['name'],
                        'type': 'lead',
                        'status': lead['status'],
                        'group': 'lead'
                    })
                    node_ids.add(lead['id'])
                
                # Add vehicle node
                if vehicle['id'] not in node_ids:
                    nodes.append({
                        'id': vehicle['id'],
                        'label': f"{vehicle['make']} {vehicle['model']}",
                        'type': 'vehicle',
                        'price': vehicle['price'],
                        'group': 'vehicle'
                    })
                    node_ids.add(vehicle['id'])
                
                # Add edge
                edges.append({
                    'from': lead['id'],
                    'to': vehicle['id'],
                    'label': 'INTERESTED_IN',
                    'interest_level': rel.get('interest_level', 'unknown')
                })
            
            return {'nodes': nodes, 'edges': edges}
    
    def check_available_slots(self, days: int = 7) -> Dict[str, Any]:
        """Check available appointment slots"""
        slots = []
        today = datetime.now()
        
        for i in range(1, days + 1):
            date = (today + timedelta(days=i)).strftime('%Y-%m-%d')
            for hour in ['10:00', '12:00', '14:00', '16:00', '18:00']:
                slots.append({
                    'date': date,
                    'time': hour,
                    'available': True
                })
        
        return {'slots': slots}
    
    def update_lead_sentiment(self, lead_id: str, sentiment: str, score: float):
        """Update lead sentiment based on interaction"""
        with self.driver.session(database=self.database) as session:
            session.run("""
                MATCH (l:Lead {id: $lead_id})
                SET l.sentiment = $sentiment,
                    l.sentiment_score = $score,
                    l.last_updated = datetime()
            """, lead_id=lead_id, sentiment=sentiment, score=score)
            
            logger.info(f"Updated sentiment for lead {lead_id}: {sentiment} ({score})")
    
    def add_interaction(self, lead_id: str, interaction_type: str, 
                       content: str, sentiment: str):
        """Add interaction history to lead"""
        with self.driver.session(database=self.database) as session:
            session.run("""
                MATCH (l:Lead {id: $lead_id})
                CREATE (i:Interaction {
                    id: randomUUID(),
                    type: $interaction_type,
                    content: $content,
                    sentiment: $sentiment,
                    timestamp: datetime()
                })
                CREATE (l)-[:HAD_INTERACTION]->(i)
            """, lead_id=lead_id, interaction_type=interaction_type,
                content=content, sentiment=sentiment)


# Utility function to initialize database
def initialize_database():
    """Initialize database with schema and seed data"""
    handler = Neo4jHandler()
    try:
        handler.seed_initial_data()
        logger.info("✅ Database initialized successfully")
    finally:
        handler.close()


if __name__ == "__main__":
    # Test and initialize
    initialize_database()