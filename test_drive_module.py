"""
test_drive_module.py - Complete Test Drive Booking System
Integrates with Neo4j to store and retrieve test drive bookings
Handles booking creation, updates, cancellations, and retrieval
WITH CONNECTION RETRY MECHANISM AND PROPER ERROR HANDLING
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import uuid
import time
from email_notification import get_email_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDriveBookingSystem:
    """Complete test drive booking system with Neo4j integration"""
    
    def __init__(self, neo4j_handler):
        """Initialize test drive system"""
        self.neo4j = neo4j_handler
        self.email_service = get_email_service()
        self.max_retries = 3
        self.retry_delay = 2
        self._ensure_constraints()
        logger.info("✅ Test Drive Booking System initialized")
    
    def _verify_connection(self) -> bool:
        """Verify Neo4j connection is active"""
        try:
            if not self.neo4j.driver:
                logger.error("❌ Neo4j driver is None")
                return False
            
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
            logger.debug("✅ Neo4j connection verified")
            return True
        except Exception as e:
            logger.error(f"❌ Neo4j connection check failed: {e}")
            return False
    
    def _execute_with_retry(self, operation, operation_name="operation"):
        """Execute Neo4j operation with retry logic"""
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                if not self._verify_connection():
                    logger.warning(f"⚠️ Connection lost, attempting to reconnect...")
                    self.neo4j.connect()  # Reconnect if connection lost
                    time.sleep(self.retry_delay)
                    continue
                
                logger.debug(f"🔄 Executing {operation_name} (attempt {attempt}/{self.max_retries})")
                result = operation()
                logger.debug(f"✅ {operation_name} completed successfully")
                return result
            
            except Exception as e:
                last_exception = e
                logger.error(f"❌ {operation_name} failed (attempt {attempt}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries:
                    logger.info(f"🔄 Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ {operation_name} failed after {self.max_retries} attempts")
        
        # If we get here, all retries failed
        raise last_exception
    
    def _ensure_constraints(self):
        """Create Neo4j constraints for test drives"""
        def create_constraints():
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                session.run("""
                    CREATE CONSTRAINT test_drive_id IF NOT EXISTS
                    FOR (td:TestDrive) REQUIRE td.id IS UNIQUE
                """)
                logger.info("✅ Neo4j constraints created")
        
        try:
            self._execute_with_retry(create_constraints, "Constraint creation")
        except Exception as e:
            logger.warning(f"⚠️ Could not create constraints: {e}")
    
    def book_test_drive(
        self, 
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        vehicle_id: str,
        preferred_date: str,
        preferred_time: str,
        notes: str = "",
        pickup_location: str = "Showroom"
    ) -> Dict[str, Any]:
        """
        Book a test drive
        
        Args:
            customer_name: Full name
            customer_email: Email address
            customer_phone: Phone number
            vehicle_id: Vehicle ID to test drive
            preferred_date: Date in YYYY-MM-DD format
            preferred_time: Time in HH:MM format
            notes: Additional notes
            pickup_location: Where to pick up vehicle (Showroom/Home)
        
        Returns:
            Dictionary with booking details
        """
        def perform_booking():
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                # ═══════════════════════════════════════════════════════════
                # STEP 1: Check for duplicate bookings (last 2 minutes)
                # ═══════════════════════════════════════════════════════════
                logger.info(f"🔍 Checking for duplicate bookings for {customer_email}")
                duplicate_check = session.run("""
                    MATCH (td:TestDrive)
                    WHERE (td.customer_email = $email OR td.customer_phone = $phone)
                      AND td.vehicle_id = $vehicle_id
                      AND td.status IN ['confirmed', 'pending']
                      AND td.created_at > datetime() - duration('PT2M')
                    RETURN td.id as booking_id, 
                           td.date as date, 
                           td.time as time,
                           td.created_at as created_at
                    ORDER BY td.created_at DESC
                    LIMIT 1
                """, email=customer_email, phone=customer_phone, vehicle_id=vehicle_id).single()
                
                if duplicate_check:
                    existing_booking_id = duplicate_check['booking_id']
                    existing_date = str(duplicate_check['date'])
                    existing_time = duplicate_check['time']
                    
                    # ✅ Calculate time difference with timezone awareness
                    try:
                        created_at = duplicate_check['created_at'].to_native()
                        now = datetime.now(timezone.utc)
                        
                        # Ensure created_at is timezone-aware
                        if created_at.tzinfo is None:
                            created_at = created_at.replace(tzinfo=timezone.utc)
                        
                        time_diff = (now - created_at).total_seconds()
                        
                        if time_diff < 60:
                            time_ago = "just now"
                        elif time_diff < 120:
                            time_ago = "1 minute ago"
                        else:
                            time_ago = f"{int(time_diff / 60)} minutes ago"
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Time calculation error: {e}")
                        time_ago = "recently"
                    
                    logger.warning(f"🚫 DUPLICATE DETECTED: {existing_booking_id} created {time_ago}")
                    
                    return {
                        'success': False,
                        'duplicate': True,
                        'existing_booking_id': existing_booking_id,
                        'message': f'You already have a booking for this vehicle!',
                        'details': {
                            'booking_id': existing_booking_id,
                            'date': existing_date,
                            'time': existing_time,
                            'created_ago': time_ago
                        }
                    }
                
                # ═══════════════════════════════════════════════════════════
                # STEP 2: Generate unique booking ID
                # ═══════════════════════════════════════════════════════════
                booking_id = f"TD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
                logger.info(f"📋 Generated booking ID: {booking_id}")
                
                # ═══════════════════════════════════════════════════════════
                # STEP 3: Check if vehicle exists and has stock
                # ═══════════════════════════════════════════════════════════
                logger.info(f"🚗 Checking vehicle {vehicle_id}")
                vehicle_check = session.run("""
                    MATCH (v:Vehicle {id: $vehicle_id})
                    RETURN v.make + ' ' + v.model as vehicle_name, 
                           v.stock as stock,
                           v.year as year
                """, vehicle_id=vehicle_id).single()
                
                if not vehicle_check:
                    logger.error(f"❌ Vehicle {vehicle_id} not found in Neo4j")
                    return {
                        'success': False,
                        'message': f'Vehicle {vehicle_id} not found'
                    }
                
                vehicle_name = vehicle_check['vehicle_name']
                stock = vehicle_check['stock']
                vehicle_year = vehicle_check.get('year', '')
                
                logger.info(f"✅ Vehicle found: {vehicle_year} {vehicle_name} (Stock: {stock})")
                
                if stock <= 0:
                    logger.warning(f"⚠️ Vehicle {vehicle_name} out of stock")
                    return {
                        'success': False,
                        'message': f'{vehicle_name} is currently out of stock'
                    }
                
                # ═══════════════════════════════════════════════════════════
                # STEP 4: Check for time slot conflicts
                # ═══════════════════════════════════════════════════════════
                logger.info(f"📅 Checking time slot: {preferred_date} at {preferred_time}")
                conflict_check = session.run("""
                    MATCH (td:TestDrive)-[:FOR_VEHICLE]->(v:Vehicle {id: $vehicle_id})
                    WHERE td.date = date($date) 
                      AND td.time = $time
                      AND td.status IN ['confirmed', 'pending']
                    RETURN count(td) as conflicts
                """, vehicle_id=vehicle_id, date=preferred_date, time=preferred_time).single()
                
                if conflict_check['conflicts'] > 0:
                    logger.warning(f"⚠️ Time slot {preferred_time} already booked for {preferred_date}")
                    return {
                        'success': False,
                        'message': f'This time slot is already booked for {vehicle_name}. Please choose another time.'
                    }
                
                logger.info(f"✅ Time slot available")
                
                # ═══════════════════════════════════════════════════════════
                # STEP 5: Create or merge customer (Lead)
                # ═══════════════════════════════════════════════════════════
                lead_id = f"L{abs(hash(customer_email)) % 100000:05d}"
                logger.info(f"👤 Creating/updating lead: {lead_id}")
                
                session.run("""
                    MERGE (l:Lead {email: $email})
                    ON CREATE SET 
                        l.id = $lead_id,
                        l.name = $name,
                        l.phone = $phone,
                        l.status = 'warm',
                        l.created_at = coalesce(l.created_at, datetime()),
                        l.updated_at = datetime()
                    ON MATCH SET
                        l.name = $name,
                        l.phone = $phone,
                        l.status = CASE
                            WHEN l.status = 'cold' THEN 'warm'
                            ELSE l.status
                        END,
                        l.updated_at = datetime()
                """, email=customer_email, lead_id=lead_id, name=customer_name, phone=customer_phone)
                
                logger.info(f"✅ Lead created/updated: {lead_id}")
                
                # ═══════════════════════════════════════════════════════════
                # STEP 6: Create test drive booking in Neo4j
                # ═══════════════════════════════════════════════════════════
                logger.info(f"💾 Creating test drive booking in Neo4j...")
                
                create_result = session.run("""
                    MATCH (l:Lead {email: $email})
                    MATCH (v:Vehicle {id: $vehicle_id})
                    CREATE (td:TestDrive {
                        id: $booking_id,
                        vehicle_id: $vehicle_id,
                        customer_name: $customer_name,
                        customer_email: $email,
                        customer_phone: $phone,
                        date: date($date),
                        time: $time,
                        status: 'confirmed',
                        pickup_location: $pickup_location,
                        notes: $notes,
                        created_at: datetime(),
                        updated_at: datetime(),
                        reminder_sent: false
                    })
                    CREATE (l)-[:BOOKED_TEST_DRIVE]->(td)
                    CREATE (td)-[:FOR_VEHICLE]->(v)
                    RETURN td.id as booking_id, td.status as status
                """, 
                    booking_id=booking_id, customer_name=customer_name,
                    email=customer_email, phone=customer_phone,
                    vehicle_id=vehicle_id, date=preferred_date, time=preferred_time,
                    pickup_location=pickup_location, notes=notes
                ).single()
                
                if not create_result:
                    logger.error(f"❌ Failed to create booking in Neo4j - No result returned")
                    return {
                        'success': False,
                        'message': 'Failed to create booking in database'
                    }
                
                logger.info(f"✅ Test drive booking created in Neo4j: {create_result['booking_id']}")
                
                # ═══════════════════════════════════════════════════════════
                # STEP 7: Verify booking was actually stored
                # ═══════════════════════════════════════════════════════════
                logger.info(f"🔍 Verifying booking was stored...")
                verify = session.run("""
                    MATCH (td:TestDrive {id: $booking_id})
                    OPTIONAL MATCH (td)-[:FOR_VEHICLE]->(v:Vehicle)
                    OPTIONAL MATCH (l:Lead)-[:BOOKED_TEST_DRIVE]->(td)
                    RETURN td.id as id, 
                           td.status as status, 
                           td.date as date,
                           td.time as time,
                           v.id as vehicle_id,
                           l.email as lead_email
                """, booking_id=booking_id).single()
                
                if verify:
                    logger.info(f"✅ BOOKING VERIFIED IN NEO4J:")
                    logger.info(f"   ID: {verify['id']}")
                    logger.info(f"   Status: {verify['status']}")
                    logger.info(f"   Date: {verify['date']}")
                    logger.info(f"   Time: {verify['time']}")
                    logger.info(f"   Vehicle: {verify['vehicle_id']}")
                    logger.info(f"   Lead: {verify['lead_email']}")
                else:
                    logger.error(f"❌ CRITICAL: Booking NOT found in Neo4j after creation!")
                    return {
                        'success': False,
                        'message': 'Booking created but verification failed'
                    }
                
                # ═══════════════════════════════════════════════════════════
                # STEP 8: Send confirmation email
                # ═══════════════════════════════════════════════════════════
                email_sent = False
                try:
                    vehicle_result = session.run("""
                        MATCH (v:Vehicle {id: $vehicle_id})
                        RETURN v.year as year, v.make as make, v.model as model
                    """, vehicle_id=vehicle_id).single()
                    
                    vehicle_full_name = f"{vehicle_result['year']} {vehicle_result['make']} {vehicle_result['model']}" if vehicle_result else vehicle_name
                    
                    email_data = {
                        'customer_email': customer_email,
                        'customer_name': customer_name,
                        'vehicle_name': vehicle_full_name,
                        'date': preferred_date,
                        'time': preferred_time,
                        'booking_id': booking_id,
                        'pickup_location': pickup_location
                    }
                    
                    logger.info(f"📧 Sending confirmation email to {customer_email}...")
                    email_result = self.email_service.send_test_drive_confirmation(email_data)
                    
                    if email_result['success']:
                        logger.info(f"✅ Email sent to {customer_email}")
                        email_sent = True
                    else:
                        logger.warning(f"⚠️ Email failed: {email_result['message']}")
                        
                except Exception as e:
                    logger.error(f"❌ Email error: {e}")
                
                # ═══════════════════════════════════════════════════════════
                # STEP 9: Return success response
                # ═══════════════════════════════════════════════════════════
                logger.info(f"✅ Test drive booking completed successfully: {booking_id}")
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'customer_name': customer_name,
                    'vehicle_name': vehicle_name,
                    'date': preferred_date,
                    'time': preferred_time,
                    'pickup_location': pickup_location,
                    'message': f'✅ Test drive confirmed for {vehicle_name}',
                    'email_sent': email_sent,
                    'details': {
                        'booking_id': booking_id,
                        'vehicle': vehicle_name,
                        'date': preferred_date,
                        'time': preferred_time,
                        'location': pickup_location,
                        'customer': customer_name,
                        'email': customer_email,
                        'phone': customer_phone
                    }
                }
        
        try:
            return self._execute_with_retry(perform_booking, "Test drive booking")
        except Exception as e:
            logger.error(f"❌ Booking error after all retries: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Error creating booking: {str(e)}'
            }
    
    def get_my_test_drives(self, customer_email: str) -> List[Dict[str, Any]]:
        """
        Get all test drives for a customer
        
        Args:
            customer_email: Customer email address
        
        Returns:
            List of test drive bookings
        """
        def fetch_bookings():
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                logger.info(f"🔍 Fetching test drives for {customer_email}")
                
                result = session.run("""
                    MATCH (td:TestDrive {customer_email: $email})
                    OPTIONAL MATCH (td)-[:FOR_VEHICLE]->(v:Vehicle)
                    RETURN td, v.make + ' ' + v.model as vehicle_name, v.image as vehicle_image
                    ORDER BY td.date DESC, td.time DESC
                """, email=customer_email)
                
                bookings = []
                for record in result:
                    td = record['td']
                    bookings.append({
                        'booking_id': td['id'],
                        'customer_name': td['customer_name'],
                        'customer_email': td['customer_email'],
                        'customer_phone': td['customer_phone'],
                        'vehicle_name': record.get('vehicle_name', 'Unknown'),
                        'vehicle_image': record.get('vehicle_image', ''),
                        'date': str(td['date']),
                        'time': td['time'],
                        'status': td['status'],
                        'pickup_location': td.get('pickup_location', 'Showroom'),
                        'notes': td.get('notes', ''),
                        'created_at': str(td['created_at'])
                    })
                
                logger.info(f"✅ Retrieved {len(bookings)} bookings for {customer_email}")
                return bookings
        
        try:
            return self._execute_with_retry(fetch_bookings, "Fetch test drives")
        except Exception as e:
            logger.error(f"❌ Retrieval error: {e}")
            return []
    
    def get_all_test_drives(
        self, 
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all test drives (for admin)
        
        Args:
            status: Filter by status (confirmed/completed/cancelled)
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
        
        Returns:
            List of all test drive bookings
        """
        def fetch_all_bookings():
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                conditions = ["1=1"]
                params = {}
                
                if status:
                    conditions.append("td.status = $status")
                    params['status'] = status
                
                if date_from:
                    conditions.append("td.date >= date($date_from)")
                    params['date_from'] = date_from
                
                if date_to:
                    conditions.append("td.date <= date($date_to)")
                    params['date_to'] = date_to
                
                where_clause = " AND ".join(conditions)
                
                query = f"""
                    MATCH (td:TestDrive)
                    WHERE {where_clause}
                    OPTIONAL MATCH (td)-[:FOR_VEHICLE]->(v:Vehicle)
                    RETURN td, v.make + ' ' + v.model as vehicle_name, v.id as vehicle_id
                    ORDER BY td.date DESC, td.time DESC
                """
                
                logger.info(f"🔍 Fetching all test drives with filters: {params}")
                result = session.run(query, params)
                
                bookings = []
                for record in result:
                    td = record['td']
                    bookings.append({
                        'booking_id': td['id'],
                        'customer_name': td['customer_name'],
                        'customer_email': td['customer_email'],
                        'customer_phone': td['customer_phone'],
                        'vehicle_name': record.get('vehicle_name', 'Unknown'),
                        'vehicle_id': record.get('vehicle_id', ''),
                        'date': str(td['date']),
                        'time': td['time'],
                        'status': td['status'],
                        'pickup_location': td.get('pickup_location', 'Showroom'),
                        'notes': td.get('notes', ''),
                        'created_at': str(td['created_at'])
                    })
                
                logger.info(f"✅ Retrieved {len(bookings)} total bookings")
                return bookings
        
        try:
            return self._execute_with_retry(fetch_all_bookings, "Fetch all test drives")
        except Exception as e:
            logger.error(f"❌ Retrieval error: {e}")
            return []
    
    def update_test_drive(
        self,
        booking_id: str,
        new_date: Optional[str] = None,
        new_time: Optional[str] = None,
        new_pickup_location: Optional[str] = None,
        new_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update test drive booking (reschedule)
        
        Args:
            booking_id: Test drive booking ID
            new_date: New date (optional)
            new_time: New time (optional)
            new_pickup_location: New pickup location (optional)
            new_notes: New notes (optional)
        
        Returns:
            Success status and updated details
        """
        def perform_update():
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                # Check if booking exists
                logger.info(f"🔍 Checking booking {booking_id}")
                check = session.run("""
                    MATCH (td:TestDrive {id: $booking_id})
                    RETURN td.status as status
                """, booking_id=booking_id).single()
                
                if not check:
                    logger.error(f"❌ Booking {booking_id} not found")
                    return {
                        'success': False,
                        'message': f'Booking {booking_id} not found'
                    }
                
                if check['status'] == 'cancelled':
                    logger.warning(f"⚠️ Cannot update cancelled booking")
                    return {
                        'success': False,
                        'message': 'Cannot update a cancelled booking'
                    }
                
                # Build update query
                set_clauses = ["td.updated_at = datetime()"]
                params = {'booking_id': booking_id}
                
                if new_date:
                    set_clauses.append("td.date = date($new_date)")
                    params['new_date'] = new_date
                
                if new_time:
                    set_clauses.append("td.time = $new_time")
                    params['new_time'] = new_time
                
                if new_pickup_location:
                    set_clauses.append("td.pickup_location = $new_pickup_location")
                    params['new_pickup_location'] = new_pickup_location
                
                if new_notes is not None:
                    set_clauses.append("td.notes = $new_notes")
                    params['new_notes'] = new_notes
                
                set_clause = ", ".join(set_clauses)
                
                # Update booking
                logger.info(f"💾 Updating test drive {booking_id}")
                result = session.run(f"""
                    MATCH (td:TestDrive {{id: $booking_id}})
                    OPTIONAL MATCH (td)-[:FOR_VEHICLE]->(v:Vehicle)
                    SET {set_clause}
                    RETURN td, v.make + ' ' + v.model as vehicle_name
                """, params).single()
                
                td = result['td']
                vehicle_name = result.get('vehicle_name', 'Unknown')
                
                logger.info(f"✅ Test drive updated: {booking_id}")
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'message': f'✅ Test drive updated successfully',
                    'details': {
                        'booking_id': booking_id,
                        'vehicle': vehicle_name,
                        'date': str(td['date']),
                        'time': td['time'],
                        'pickup_location': td.get('pickup_location', 'Showroom'),
                        'status': td['status']
                    }
                }
        
        try:
            return self._execute_with_retry(perform_update, "Update test drive")
        except Exception as e:
            logger.error(f"❌ Update error: {e}")
            return {
                'success': False,
                'message': f'Error updating booking: {str(e)}'
            }
    
    def cancel_test_drive(
        self,
        booking_id: str,
        cancellation_reason: str = "Customer request"
    ) -> Dict[str, Any]:
        """
        Cancel a test drive booking
        
        Args:
            booking_id: Test drive booking ID
            cancellation_reason: Reason for cancellation
        
        Returns:
            Success status
        """
        def perform_cancellation():
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                logger.info(f"❌ Cancelling test drive {booking_id}")
                
                result = session.run("""
                    MATCH (td:TestDrive {id: $booking_id})
                    SET td.status = 'cancelled',
                        td.cancellation_reason = $reason,
                        td.cancelled_at = datetime(),
                        td.updated_at = datetime()
                    RETURN td.customer_name as customer_name
                """, booking_id=booking_id, reason=cancellation_reason).single()
                
                if not result:
                    logger.error(f"❌ Booking {booking_id} not found")
                    return {
                        'success': False,
                        'message': f'Booking {booking_id} not found'
                    }
                
                logger.info(f"✅ Test drive cancelled: {booking_id}")
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'message': f'✅ Test drive cancelled successfully',
                    'customer_name': result['customer_name']
                }
        
        try:
            return self._execute_with_retry(perform_cancellation, "Cancel test drive")
        except Exception as e:
            logger.error(f"❌ Cancellation error: {e}")
            return {
                'success': False,
                'message': f'Error cancelling booking: {str(e)}'
            }
    
    def complete_test_drive(
        self,
        booking_id: str,
        feedback: str = "",
        rating: int = 5,
        interested_in_purchase: bool = False
    ) -> Dict[str, Any]:
        """
        Mark test drive as completed
        
        Args:
            booking_id: Test drive booking ID
            feedback: Customer feedback
            rating: Rating (1-5)
            interested_in_purchase: Is customer interested?
        
        Returns:
            Success status
        """
        def perform_completion():
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                logger.info(f"✅ Completing test drive {booking_id}")
                
                result = session.run("""
                    MATCH (td:TestDrive {id: $booking_id})
                    SET td.status = 'completed',
                        td.feedback = $feedback,
                        td.rating = $rating,
                        td.interested_in_purchase = $interested,
                        td.completed_at = datetime(),
                        td.updated_at = datetime()
                    RETURN td
                """, booking_id=booking_id, feedback=feedback, 
                    rating=rating, interested=interested_in_purchase).single()
                
                if not result:
                    logger.error(f"❌ Booking {booking_id} not found")
                    return {
                        'success': False,
                        'message': f'Booking {booking_id} not found'
                    }
                
                # Update lead status if interested in purchase
                if interested_in_purchase:
                    session.run("""
                        MATCH (td:TestDrive {id: $booking_id})<-[:BOOKED_TEST_DRIVE]-(l:Lead)
                        SET l.status = 'hot',
                            l.updated_at = datetime()
                    """, booking_id=booking_id)
                    logger.info(f"🔥 Lead upgraded to HOT status")
                
                logger.info(f"✅ Test drive completed: {booking_id}")
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'message': '✅ Test drive marked as completed',
                    'rating': rating,
                    'interested': interested_in_purchase
                }
        
        try:
            return self._execute_with_retry(perform_completion, "Complete test drive")
        except Exception as e:
            logger.error(f"❌ Completion error: {e}")
            return {
                'success': False,
                'message': f'Error completing booking: {str(e)}'
            }
    
    def get_available_slots(
        self,
        vehicle_id: str,
        date: str
    ) -> List[str]:
        """
        Get available time slots for a vehicle on a specific date
        
        Args:
            vehicle_id: Vehicle ID
            date: Date in YYYY-MM-DD format
        
        Returns:
            List of available time slots
        """
        def fetch_available_slots():
            # Define all possible time slots
            all_slots = [
                "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
                "12:00", "12:30", "14:00", "14:30", "15:00", "15:30",
                "16:00", "16:30", "17:00", "17:30"
            ]
            
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                # Get booked slots
                logger.info(f"🔍 Checking available slots for {vehicle_id} on {date}")
                
                result = session.run("""
                    MATCH (td:TestDrive)-[:FOR_VEHICLE]->(v:Vehicle {id: $vehicle_id})
                    WHERE td.date = date($date)
                      AND td.status IN ['confirmed', 'pending']
                    RETURN td.time as time
                """, vehicle_id=vehicle_id, date=date)
                
                booked_slots = {record['time'] for record in result}
                
                # Filter available slots
                available = [slot for slot in all_slots if slot not in booked_slots]
                
                logger.info(f"✅ Found {len(available)} available slots for {date}")
                return available
        
        try:
            return self._execute_with_retry(fetch_available_slots, "Fetch available slots")
        except Exception as e:
            logger.error(f"❌ Slot check error: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get test drive statistics (for admin dashboard)
        
        Returns:
            Dictionary with statistics
        """
        def fetch_statistics():
            with self.neo4j.driver.session(database=self.neo4j.database) as session:
                logger.info(f"📊 Fetching test drive statistics")
                
                stats = session.run("""
                    MATCH (td:TestDrive)
                    RETURN 
                        count(td) as total,
                        count(CASE WHEN td.status = 'confirmed' THEN 1 END) as confirmed,
                        count(CASE WHEN td.status = 'completed' THEN 1 END) as completed,
                        count(CASE WHEN td.status = 'cancelled' THEN 1 END) as cancelled,
                        count(CASE WHEN td.status = 'completed' AND td.interested_in_purchase = true THEN 1 END) as conversions,
                        avg(CASE WHEN td.rating IS NOT NULL THEN td.rating END) as avg_rating
                """).single()
                
                # Get popular vehicles
                popular = session.run("""
                    MATCH (td:TestDrive)-[:FOR_VEHICLE]->(v:Vehicle)
                    WHERE td.status IN ['confirmed', 'completed']
                    RETURN v.make + ' ' + v.model as vehicle, count(td) as bookings
                    ORDER BY bookings DESC
                    LIMIT 5
                """)
                
                popular_vehicles = [
                    {'vehicle': record['vehicle'], 'bookings': record['bookings']}
                    for record in popular
                ]
                
                logger.info(f"✅ Statistics retrieved")
                
                return {
                    'total_bookings': stats['total'],
                    'confirmed': stats['confirmed'],
                    'completed': stats['completed'],
                    'cancelled': stats['cancelled'],
                    'conversions': stats['conversions'],
                    'conversion_rate': (stats['conversions'] / stats['completed'] * 100) if stats['completed'] > 0 else 0,
                    'average_rating': float(stats['avg_rating']) if stats['avg_rating'] else 0,
                    'popular_vehicles': popular_vehicles
                }
        
        try:
            return self._execute_with_retry(fetch_statistics, "Fetch statistics")
        except Exception as e:
            logger.error(f"❌ Statistics error: {e}")
            return {}


# Integration functions for Gradio app
def create_test_drive_booking_interface(test_drive_system: TestDriveBookingSystem):
    """
    Create Gradio interface for test drive booking
    To be integrated into your existing app.py
    """
    import gradio as gr
    from datetime import datetime, timedelta
    
    def get_next_30_days():
        """Get next 30 days for date picker"""
        today = datetime.now()
        return [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    
    def book_test_drive_ui(name, email, phone, vehicle_id, date, time, location, notes):
        """Book test drive from UI"""
        result = test_drive_system.book_test_drive(
            customer_name=name,
            customer_email=email,
            customer_phone=phone,
            vehicle_id=vehicle_id,
            preferred_date=date,
            preferred_time=time,
            notes=notes,
            pickup_location=location
        )
        
        if result['success']:
            # Get updated bookings
            bookings = test_drive_system.get_my_test_drives(email)
            bookings_table = [
                [b['booking_id'], b['vehicle_name'], b['date'], b['time'], b['status']]
                for b in bookings
            ]
            
            confirmation = f"""✅ **Test Drive Booked Successfully!**

📋 **Booking ID:** {result['booking_id']}
🚗 **Vehicle:** {result['vehicle_name']}
📅 **Date:** {result['date']}
⏰ **Time:** {result['time']}
📍 **Location:** {result['pickup_location']}

We'll send a confirmation email to {email}
"""
            return confirmation, bookings_table
        else:
            return f"❌ {result['message']}", None
    
    def view_my_bookings(email):
        """View customer bookings"""
        bookings = test_drive_system.get_my_test_drives(email)
        if not bookings:
            return [["No test drives found", "", "", "", ""]]
        
        return [
            [b['booking_id'], b['vehicle_name'], b['date'], b['time'], b['status']]
            for b in bookings
        ]
    
    def cancel_booking_ui(booking_id, reason):
        """Cancel booking from UI"""
        result = test_drive_system.cancel_test_drive(booking_id, reason)
        return result['message'] if result['success'] else f"❌ {result['message']}"
    
    with gr.Blocks() as interface:
        gr.Markdown("# 🚗 Test Drive Booking System")
        
        with gr.Tabs():
            # Tab 1: Book Test Drive
            with gr.Tab("📅 Book Test Drive"):
                gr.Markdown("### Schedule Your Test Drive")
                
                with gr.Row():
                    with gr.Column():
                        book_name = gr.Textbox(label="Full Name *", placeholder="Amit Sarkar")
                        book_email = gr.Textbox(label="Email *", placeholder="john@example.com")
                        book_phone = gr.Textbox(label="Phone *", placeholder="+971-50-123-4567")
                    
                    with gr.Column():
                        book_vehicle = gr.Textbox(label="Vehicle ID *", placeholder="V00001")
                        book_date = gr.Dropdown(choices=get_next_30_days(), label="Select Date *")
                        book_time = gr.Dropdown(
                            choices=["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"],
                            label="Select Time *"
                        )
                
                book_location = gr.Radio(
                    choices=["Showroom", "Home Delivery"],
                    value="Showroom",
                    label="Pickup Location"
                )
                book_notes = gr.Textbox(label="Additional Notes", lines=2)
                
                book_btn = gr.Button("📅 Book Test Drive", variant="primary", size="lg")
                booking_status = gr.Markdown()
                
                gr.Markdown("### Your Test Drives")
                my_bookings = gr.Dataframe(
                    headers=["Booking ID", "Vehicle", "Date", "Time", "Status"],
                    label="My Test Drive Bookings"
                )
                
                book_btn.click(
                    book_test_drive_ui,
                    [book_name, book_email, book_phone, book_vehicle, book_date, book_time, book_location, book_notes],
                    [booking_status, my_bookings]
                )
            
            # Tab 2: View My Bookings
            with gr.Tab("📋 My Bookings"):
                view_email = gr.Textbox(label="Your Email", placeholder="john@example.com")
                view_btn = gr.Button("🔍 View My Bookings")
                
                view_bookings_table = gr.Dataframe(
                    headers=["Booking ID", "Vehicle", "Date", "Time", "Status"]
                )
                
                view_btn.click(view_my_bookings, view_email, view_bookings_table)
            
            # Tab 3: Cancel Booking
            with gr.Tab("❌ Cancel Booking"):
                cancel_id = gr.Textbox(label="Booking ID *")
                cancel_reason = gr.Textbox(label="Cancellation Reason", lines=2)
                cancel_btn = gr.Button("❌ Cancel Booking", variant="stop")
                cancel_status = gr.Markdown()
                
                cancel_btn.click(cancel_booking_ui, [cancel_id, cancel_reason], cancel_status)
    
    return interface


# Test function
def test_test_drive_system():
    """Test the test drive booking system"""
    from neo4j_handler import Neo4jHandler
    
    print("="*60)
    print("TESTING TEST DRIVE BOOKING SYSTEM")
    print("="*60)
    
    neo4j = Neo4jHandler()
    tds = TestDriveBookingSystem(neo4j)
    
    # Test 1: Book a test drive
    print("\n1. BOOKING TEST DRIVE...")
    result = tds.book_test_drive(
        customer_name="Amit Sarkar",
        customer_email="ahmed@example.com",
        customer_phone="+971-50-123-4567",
        vehicle_id="V00001",
        preferred_date="2025-11-20",
        preferred_time="10:00",
        notes="First time test drive",
        pickup_location="Showroom"
    )
    print(f"Result: {result['message']}")
    if result['success']:
        booking_id = result['booking_id']
        print(f"Booking ID: {booking_id}")
    
    # Test 2: View bookings
    print("\n2. VIEWING CUSTOMER BOOKINGS...")
    bookings = tds.get_my_test_drives("ahmed@example.com")
    print(f"Found {len(bookings)} booking(s)")
    for b in bookings:
        print(f"  - {b['booking_id']}: {b['vehicle_name']} on {b['date']} at {b['time']}")
    
    # Test 3: Get statistics
    print("\n3. GETTING STATISTICS...")
    stats = tds.get_statistics()
    print(f"Total bookings: {stats.get('total_bookings', 0)}")
    print(f"Confirmed: {stats.get('confirmed', 0)}")
    print(f"Completed: {stats.get('completed', 0)}")
    print(f"Conversion rate: {stats.get('conversion_rate', 0):.1f}%")
    
    neo4j.close()
    print("\n" + "="*60)
    print("✅ TEST DRIVE SYSTEM TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    test_test_drive_system()