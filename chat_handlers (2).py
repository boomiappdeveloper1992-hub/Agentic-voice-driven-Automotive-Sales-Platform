"""
chat_handlers.py - MESSAGES FORMAT WITH PROCESSING MESSAGES
✅ User messages visible
✅ Chat input clears after sending
✅ Email gate timing fixed
✅ Processing messages show then replaced with actual response
"""

import logging
import uuid
import re
import threading
from typing import Optional, Tuple, List, Dict
from datetime import datetime
from session_manager import get_session_manager

logger = logging.getLogger(__name__)
session_manager = get_session_manager()


# ═══════════════════════════════════════════════════════════════════════
# PROCESSING MESSAGES
# ═══════════════════════════════════════════════════════════════════════

PROCESSING_MESSAGES = {
    'booking_confirmation': """
<div style='padding: 25px; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
            border-radius: 12px; color: white; margin: 15px 0; text-align: center;'>
    <div style='font-size: 3em; margin-bottom: 10px;'>⏳</div>
    <h3 style='margin: 0 0 10px 0;'>Confirming Your Booking...</h3>
    <p style='margin: 0; opacity: 0.9;'>Creating your test drive appointment</p>
</div>
""",
    'vehicle_search': """
<div style='padding: 20px; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
            border-radius: 12px; color: white; margin: 15px 0; text-align: center;'>
    <div style='font-size: 2.5em; margin-bottom: 8px;'>🔍</div>
    <h4 style='margin: 0;'>Searching Inventory...</h4>
    <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 0.9em;'>Finding the perfect vehicles for you</p>
</div>
""",
    'booking_start': """
<div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0; text-align: center;'>
    <div style='font-size: 2.5em; margin-bottom: 8px;'>📋</div>
    <h4 style='margin: 0;'>Loading Booking Form...</h4>
    <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 0.9em;'>Preparing your test drive details</p>
</div>
""",
    'location_selection': """
<div style='padding: 20px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
            border-radius: 12px; color: white; margin: 15px 0; text-align: center;'>
    <div style='font-size: 2.5em; margin-bottom: 8px;'>📍</div>
    <h4 style='margin: 0;'>Loading Locations...</h4>
    <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 0.9em;'>Fetching available branches</p>
</div>
""",
    'time_slots': """
<div style='padding: 20px; background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%); 
            border-radius: 12px; color: white; margin: 15px 0; text-align: center;'>
    <div style='font-size: 2.5em; margin-bottom: 8px;'>⏰</div>
    <h4 style='margin: 0;'>Loading Time Slots...</h4>
    <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 0.9em;'>Finding available times</p>
</div>
""",
    'general': """
<div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 15px 0; text-align: center;'>
    <div style='font-size: 2.5em; margin-bottom: 8px;'>💭</div>
    <h4 style='margin: 0;'>Processing...</h4>
    <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 0.9em;'>Thinking about your request</p>
</div>
"""
}


def detect_message_type(message: str) -> str:
    """Detect what type of interaction this is"""
    message_lower = message.lower().strip()
    
    # Command-based detection
    if message.startswith("⏰ CONFIRM_BOOKING:"):
        return 'booking_confirmation'
    elif message.startswith("🚗 BOOK_START:"):
        return 'booking_start'
    elif message.startswith("📋 DETAILS_SUBMITTED:"):
        return 'booking_start'
    elif message.startswith("📍 LOCATION_TYPE:"):
        return 'location_selection'
    elif message.startswith("📍 BRANCH_SELECTED:"):
        return 'location_selection'
    elif message.startswith("📍 ADDRESS_SUBMITTED:"):
        return 'location_selection'
    elif message.startswith("📅 SELECT_DATE:"):
        return 'time_slots'
    
    # Vehicle search detection
    vehicle_brands = ['toyota', 'honda', 'ford', 'bmw', 'mercedes', 'audi', 'lexus', 
                     'nissan', 'mazda', 'hyundai', 'kia', 'byd', 'tesla', 'volkswagen',
                     'chevrolet', 'jeep', 'ram', 'gmc', 'subaru', 'volvo', 'porsche']
    vehicle_types = ['car', 'cars', 'vehicle', 'vehicles', 'suv', 'suvs', 'sedan', 
                    'sedans', 'truck', 'trucks', 'coupe', 'hatchback', 'wagon']
    search_words = ['show', 'find', 'search', 'looking', 'want', 'need', 'get', 
                   'give me', 'display', 'list', 'see', 'view']
    
    has_brand = any(brand in message_lower for brand in vehicle_brands)
    has_vehicle_type = any(vtype in message_lower for vtype in vehicle_types)
    has_search_intent = any(word in message_lower for word in search_words)
    
    if has_brand or (has_vehicle_type and has_search_intent) or (has_vehicle_type and len(message.split()) <= 5):
        return 'vehicle_search'
    elif any(word in message_lower for word in ['book', 'schedule', 'appointment', 'test drive']):
        return 'booking_start'
    else:
        return 'general'


def initialize_session(app, session_token: Optional[str]) -> Tuple[str, str, str, str]:
    """Initialize or resume session"""
    try:
        if session_token:
            payload = session_manager.verify_session_token(session_token)
            
            if payload:
                session_id = payload['session_id']
                user_id = payload['user_id']
                email = payload.get('email')
                
                logger.info(f"🔄 Resuming: {session_id[:20]}...")
                
                session_data = app.chatbot._load_session_from_neo4j(session_id)
                
                if session_data:
                    app.chatbot.user_sessions[user_id] = session_data
                    
                    welcome = f"""
<div style='padding: 15px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 10px 0;'>
    <h3 style='margin: 0;'>👋 Welcome Back!</h3>
    <p style='margin: 5px 0 0 0;'>Loaded {session_data['message_count']} messages.</p>
    {f"<p style='margin: 5px 0 0 0;'>📧 {email}</p>" if email else ""}
</div>
"""
                    return session_token, session_id, user_id, welcome
        
        # New session
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        new_token = session_manager.create_session_token(user_id, session_id=session_id)
        
        logger.info(f"🆕 New session: {session_id[:20]}...")
        
        welcome = """
<div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 15px 0; text-align: center;'>
    <div style='font-size: 3em; margin-bottom: 10px;'>👋</div>
    <h2 style='margin: 0 0 10px 0;'>Welcome!</h2>
    <p style='margin: 0;'>I'm here to help you find your perfect vehicle.</p>
</div>
"""
        return new_token, session_id, user_id, welcome
        
    except Exception as e:
        logger.error(f"❌ Init error: {e}")
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        token = session_manager.create_session_token(user_id, session_id=session_id)
        return token, session_id, user_id, "👋 Welcome!"


def on_chat_open(app, session_token):
    """
    ✅ MESSAGES FORMAT: [{'role': 'assistant', 'content': '...'}]
    """
    try:
        logger.info("🚀 Chat opened")
        token, session_id, user_id, welcome = initialize_session(app, session_token)
        
        # ✅ MESSAGES FORMAT
        return [{'role': 'assistant', 'content': welcome}], token, session_id, user_id
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return [{'role': 'assistant', 'content': "👋 Welcome!"}], None, f"session_{uuid.uuid4().hex[:12]}", f"user_{uuid.uuid4().hex[:12]}"


def process_text_chat_with_session(app, message, history, session_token, session_id, user_id, user_email):
    """
    ✅ MESSAGES FORMAT VERSION - WITH PROCESSING MESSAGES
    ✅ Shows processing, then replaces with actual response
    """
    if not message or not message.strip():
        return history, "", None, session_token, session_id, user_id, user_email
    
    try:
        logger.info(f"📥 Processing: '{message[:50]}...'")
        
        # Verify token
        if session_token:
            payload = session_manager.verify_session_token(session_token)
            if not payload:
                logger.warning("⚠️ Token expired")
                session_token, session_id, user_id, _ = initialize_session(app, None)
        
        # Initialize history if None
        if history is None:
            history = []
        
        # Get/create session
        if user_id not in app.chatbot.user_sessions:
            is_new_session = (history is None or len(history) <= 1)
            app.chatbot.user_sessions[user_id] = {
                'session_id': session_id,
                'start_time': datetime.now(),
                'message_count': 0 if is_new_session else 0,
                'conversation_history': [],
                'user_email': user_email,
                'preferred_language': 'en',
                'email_collected': bool(user_email),
                'email_gate_shown': False,
                'viewed_vehicles': [],
                'interests': [],
                'last_intent': None,
                'email_prompted': False
            }
        
        session = app.chatbot.user_sessions[user_id]
        
        # Check if booking command
        is_booking_command = any(cmd in message for cmd in [
            '🚗 BOOK_START:', '📋 DETAILS_SUBMITTED:', '📍 LOCATION_TYPE:', 
            '📍 BRANCH_SELECTED:', '📍 ADDRESS_SUBMITTED:', '📅 SELECT_DATE:', 
            '⏰ CONFIRM_BOOKING:'
        ])
        
        # ✅ Email gate logic (before incrementing count)
        should_show_gate = (
            not session.get('email_collected') and 
            not session.get('email_gate_shown') and 
            not user_email and
            (session['message_count'] >= 1 or is_booking_command)
        )
        
        # ✅ ALWAYS add user message to history first
        new_history = list(history)
        new_history.append({'role': 'user', 'content': message})
        
        # ✅ INCREMENT MESSAGE COUNT AFTER CHECKING GATE CONDITION
        session['message_count'] += 1
        
        # Handle email gate
        if should_show_gate:
            session['email_gate_shown'] = True
            
            gate_msg = """
<div style='padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 16px; color: white; margin: 20px 0; text-align: center;'>
    <div style='font-size: 4em; margin-bottom: 15px;'>🔒</div>
    <h2 style='margin: 0 0 15px 0;'>Email Required to Continue</h2>
    <p style='margin: 0 0 25px 0;'>Please provide your email to unlock our AI assistant.</p>
    
    <div style='padding: 20px; background: rgba(255,255,255,0.15); border-radius: 12px;'>
        <h3 style='margin: 0 0 12px 0;'>✨ What you'll get:</h3>
        <ul style='margin: 0; padding-left: 20px; text-align: left; line-height: 1.8;'>
            <li>🔍 AI-powered vehicle search</li>
            <li>🎤 Voice commands in 99+ languages</li>
            <li>📅 Instant test drive booking</li>
            <li>💬 24/7 assistance</li>
        </ul>
    </div>
    
    <div style='padding: 15px; background: rgba(251,191,36,0.25); border-radius: 8px; margin-top: 15px;'>
        <p style='margin: 0; font-weight: 600;'>💡 Simply type your email below</p>
    </div>
</div>
"""
            
            new_history.append({'role': 'assistant', 'content': gate_msg})
            logger.info(f"🔒 Email gate shown")
            return new_history, "", None, session_token, session_id, user_id, user_email
        
        # Handle email validation
        if not session.get('email_collected') and session.get('email_gate_shown') and not user_email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            if re.match(email_pattern, message.strip()):
                user_email = message.strip()
                session['user_email'] = user_email
                session['email_collected'] = True
                
                session_token = session_manager.create_session_token(
                    user_id=user_id, email=user_email, session_id=session_id
                )
                
                try:
                    app.chatbot._update_session_email(session_id, user_email)
                except Exception as e:
                    logger.error(f"Failed to update email: {e}")
                
                logger.info(f"✅ Email collected: {user_email}")
                
                welcome_msg = f"""
<div style='padding: 25px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 16px; color: white; margin: 20px 0; text-align: center;'>
    <div style='font-size: 3.5em; margin-bottom: 10px;'>🎉</div>
    <h2 style='margin: 0 0 10px 0;'>Welcome to Our Showroom!</h2>
    <p style='margin: 0; opacity: 0.95;'>Your email <strong>{user_email}</strong> has been verified.</p>
</div>
<div style='padding: 20px; background: white; border-radius: 12px; margin: 15px 0; border: 2px solid #e5e7eb;'>
    <h3 style='margin: 0 0 15px 0; color: #374151;'>🚀 You can now:</h3>
    <ul style='margin: 0; padding-left: 20px; line-height: 2; color: #4b5563;'>
        <li>🔍 Search thousands of vehicles</li>
        <li>🎤 Use voice commands</li>
        <li>📅 Book test drives instantly</li>
    </ul>
</div>
"""
                
                new_history.append({'role': 'assistant', 'content': welcome_msg})
                return new_history, "", None, session_token, session_id, user_id, user_email
            
            else:
                logger.warning(f"❌ Invalid email: {message}")
                
                error_msg = f"""
<div style='padding: 20px; background: #fee2e2; border-left: 4px solid #ef4444; 
            border-radius: 12px; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0; color: #991b1b;'>⚠️ Invalid Email Format</h3>
    <p style='margin: 0 0 15px 0; color: #7f1d1d;'>"<strong>{message}</strong>" is not a valid email address.</p>
    <div style='padding: 15px; background: rgba(255,255,255,0.5); border-radius: 8px;'>
        <p style='margin: 0 0 10px 0; color: #7f1d1d; font-weight: 600;'>✅ Valid examples:</p>
        <ul style='margin: 0; padding-left: 20px; color: #7f1d1d;'>
            <li>john.doe@example.com</li>
            <li>ahmed@gmail.com</li>
        </ul>
    </div>
    <div style='padding: 10px; background: rgba(251,191,36,0.2); border-radius: 8px; margin-top: 10px;'>
        <p style='margin: 0; color: #92400e;'>💡 Please try again with a valid email.</p>
    </div>
</div>
"""
                
                new_history.append({'role': 'assistant', 'content': error_msg})
                return new_history, "", None, session_token, session_id, user_id, user_email
        
        # ═══════════════════════════════════════════════════════════
        # ✅ ADDED: PROCESSING MESSAGES FEATURE
        # ═══════════════════════════════════════════════════════════
        
        # Detect message type
        msg_type = detect_message_type(message)
        logger.info(f"📊 Message type: {msg_type}")
        
        # Show processing message temporarily
        processing_msg = PROCESSING_MESSAGES.get(msg_type, PROCESSING_MESSAGES['general'])
        new_history.append({'role': 'assistant', 'content': processing_msg})
        logger.info(f"⏳ Showing '{msg_type}' processing message")
        
        # ═══════════════════════════════════════════════════════════
        # HANDLE BOOKING CONFIRMATION
        # ═══════════════════════════════════════════════════════════
        
        if message.startswith("⏰ CONFIRM_BOOKING:"):
            parts = message.replace("⏰ CONFIRM_BOOKING:", "").strip().split("|")
            if len(parts) == 3:
                vehicle_id, date_str, time_str = parts
                logger.info(f"📅 Booking confirmation: {vehicle_id} on {date_str} at {time_str}")
                
                # Get confirmation response from chatbot
                response_html = app.chatbot._confirm_booking(vehicle_id, date_str, time_str, session)
                
                # ✅ REPLACE processing with actual response
                new_history[-1] = {'role': 'assistant', 'content': response_html}
                
                # Save to Neo4j
                try:
                    app.chatbot._save_message_to_neo4j(session_id, response_html, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response_html,
                        'role': 'assistant'
                    })
                    app.chatbot._save_session_to_neo4j(session_id, session)
                except Exception as e:
                    logger.error(f"Failed to save to Neo4j: {e}")
                
                logger.info(f"✅ Booking confirmation sent | History: {len(new_history)} messages")
                return new_history, "", None, session_token, session_id, user_id, user_email
        
        # ═══════════════════════════════════════════════════════════
        # NORMAL CHAT PROCESSING
        # ═══════════════════════════════════════════════════════════
        
        # Process message through chatbot
        response_html, _ = app.chatbot.process_message(
            message.strip(),
            user_id=user_id,
            user_email=user_email,
            session_id=session_id
        )
        
        # ✅ REPLACE processing with actual response
        new_history[-1] = {'role': 'assistant', 'content': response_html}
        
        logger.info(f"✅ Got response: {len(response_html)} chars")
        logger.info(f"✅ Displayed result | History: {len(new_history)} messages")
        
        # Generate voice in background (non-blocking)
        preferred_lang = session.get('preferred_language', 'en')
        
        def generate_voice_async():
            try:
                logger.info("🔊 Generating voice (async)...")
                audio_path = app.chatbot._generate_voice_response(response_html, preferred_lang)
                if audio_path:
                    logger.info(f"✅ Voice ready: {audio_path}")
                    session['latest_audio'] = audio_path
            except Exception as e:
                logger.error(f"❌ Voice error: {e}")
        
        threading.Thread(target=generate_voice_async, daemon=True).start()
        
        # ✅ Return empty string to clear input
        return new_history, "", None, session_token, session_id, user_id, user_email
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}", exc_info=True)
        
        error_msg = """
<div style='padding: 15px; background: #fee2e2; border-left: 4px solid #ef4444; border-radius: 8px; margin: 10px 0;'>
    <strong style='color: #991b1b;'>❌ Error</strong>
    <p style='margin: 5px 0 0 0; color: #7f1d1d;'>Something went wrong. Please try again.</p>
</div>
"""
        
        if history is None:
            history = []
        new_history = list(history)
        new_history.append({'role': 'user', 'content': message})
        new_history.append({'role': 'assistant', 'content': error_msg})
        
        return new_history, "", None, session_token, session_id, user_id, user_email