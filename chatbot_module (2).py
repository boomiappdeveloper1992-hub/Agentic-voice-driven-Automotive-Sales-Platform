"""
chatbot_module.py - FIXED VERSION
✅ Translation integrated throughout
✅ Enhanced sentiment analysis with ML + keywords
✅ Voice responses translated to user's language
✅ Proper multilingual support
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import uuid
import re
from sentiment_response_handler import SentimentResponseHandler
from gradio_agent_transfer import GradioAgentTransfer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutomotiveChatbot:
    """Enhanced Chatbot with Translation, Voice, and Neo4j"""
    
    def __init__(self, app):
        self.app = app
        self.agent = app.agent
        self.speech_system = app.speech
        self.neo4j = app.neo4j
        
        # ✅ ADD: Translation and Sentiment systems
        self.translation = app.translator
        self.sentiment_analyzer = app.sentiment
        
        self.user_sessions = {}
        self.financial_rag = None
        self.sentiment_handler = SentimentResponseHandler()
        self.gradio_transfer = GradioAgentTransfer(self.neo4j)
        self.agent_check_interval = 2
        
        logger.info("✅ Gradio Agent Transfer integrated")
        
        # Initialize financial RAG if available
        try:
            if hasattr(app, 'financial_rag'):
                self.financial_rag = app.financial_rag
                logger.info("✅ Financial RAG integrated")
        except:
            logger.warning("⚠️ Financial RAG not available")
        
        self._initialize_conversation_schema()
        
        logger.info("✅ Chatbot initialized with Translation + Sentiment + Voice")
    
    def _initialize_conversation_schema(self):
        """Create Neo4j schema for conversations"""
        queries = [
            "CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT message_id IF NOT EXISTS FOR (m:Message) REQUIRE m.id IS UNIQUE",
            "CREATE INDEX conversation_session IF NOT EXISTS FOR (c:Conversation) ON (c.session_id)",
            "CREATE INDEX conversation_email IF NOT EXISTS FOR (c:Conversation) ON (c.user_email)",
            "CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
        ]
        
        for query in queries:
            try:
                self.neo4j.execute_with_retry(query, timeout=10.0)
            except Exception as e:
                logger.debug(f"Schema creation (may exist): {e}")
        
        logger.info("✅ Conversation schema initialized")
    
    def process_voice_input(self, audio_file: str, user_id: str = "default") -> Tuple[str, str, Optional[str]]:
        """Process voice input with translation support"""
        try:
            logger.info(f"🎤 Processing voice input from user {user_id}")
            
            # Step 1: Transcribe audio (Speech-to-Text) with language detection
            transcription_result = self.speech_system.transcribe_audio(audio_file)
            
            if not transcription_result or not transcription_result.get('text'):
                return (
                    "⚠️ Could not understand audio",
                    self._error_response("Could not transcribe audio. Please try again."),
                    None
                )
            
            transcribed_text = transcription_result['text']
            detected_language = transcription_result.get('detected_language', 'en')
            confidence = transcription_result.get('confidence', 0.0)
            
            logger.info(f"✅ Transcribed: '{transcribed_text[:50]}...'")
            logger.info(f"   Language: {detected_language}, Confidence: {confidence:.2%}")
            
            # Step 2: Process the message (with translation)
            response_html, email_prompt = self.process_message(
                transcribed_text, 
                user_id=user_id,
                detected_language=detected_language  # Pass detected language
            )
            
            if email_prompt:
                response_html += email_prompt
            
            # Step 3: Generate voice response in user's language
            response_audio = self._generate_voice_response(
                response_html, 
                detected_language
            )
            
            return transcribed_text, response_html, response_audio
            
        except Exception as e:
            logger.error(f"❌ Voice input error: {e}", exc_info=True)
            return (
                "Error processing voice",
                self._error_response("Voice processing failed. Please try typing your message."),
                None
            )

    def _check_vip_status(self, user_email: str) -> bool:
        """Check if customer is VIP"""
        try:
            if not user_email or user_email == 'unknown':
                return False
        
            query = """
            MATCH (u:User {email: $email})
            RETURN u.is_vip as is_vip, u.tier as tier
            """
        
            result = self.neo4j.execute_with_retry(query, {'email': user_email})
        
            if result and len(result) > 0:
                is_vip = result[0].get('is_vip', False)
                if is_vip:
                    logger.info(f"👑 VIP CUSTOMER: {user_email}")
                    return True
        
            return False
        
        except Exception as e:
            logger.error(f"VIP check error: {e}")
            return False

    
    def process_message(self, message: str, user_id: str = "default", 
                       user_email: Optional[str] = None,
                       session_id: Optional[str] = None,
                       detected_language: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        ✅ FIXED: Process message with full translation support
        
        Returns:
            Tuple of (response_html, prompt_for_email_if_needed)
        """
        message_lower = message.lower().strip()
        
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = self._get_or_create_session_id(user_id)
            
            # Get or create session
            if user_id not in self.user_sessions:
                session_data = self._load_session_from_neo4j(session_id)
                
                if session_data:
                    self.user_sessions[user_id] = session_data
                    logger.info(f"📂 Loaded session from Neo4j: {session_id}")
                else:
                    self.user_sessions[user_id] = {
                        'session_id': session_id,
                        'start_time': datetime.now(),
                        'message_count': 0,
                        'last_intent': None,
                        'conversation_history': [],
                        'user_email': user_email,
                        'viewed_vehicles': [],
                        'interests': [],
                        'preferred_language': detected_language or 'en',
                        'email_prompted': False
                    }
            
            session = self.user_sessions[user_id]
            session['message_count'] += 1
            
            # Update email if provided
            if user_email and not session.get('user_email'):
                session['user_email'] = user_email
                self._update_session_email(session_id, user_email)

            # ═══════════════════════════════════════════════════════════
            # ✅ STEP 1: CHECK BUTTON COMMANDS FIRST (BEFORE TRANSLATION!)
            # ═══════════════════════════════════════════════════════════
            
            is_button_command = message.startswith(('🚗 BOOK_START:', '📋 DETAILS_SUBMITTED:', 
                                        '📍 LOCATION_TYPE:', '📍 BRANCH_SELECTED:', 
                                        '📍 ADDRESS_SUBMITTED:', '📅 SELECT_DATE:', 
                                        '⏰ CONFIRM_BOOKING:', '🔄 RESCHEDULE:', 
                                        '❌ CANCEL:', '💬 FEEDBACK:', '💬 DRIVE_FEEDBACK:',
                                        '🆘 ESCALATE:', '🔚 END_AGENT_SESSION',
                                        'CONFIRM_AGENT_TRANSFER:'))

            # ═══════════════════════════════════════════════════════════
            # HANDLE INTERACTIVE BUTTON COMMANDS (unchanged)
            # ═══════════════════════════════════════════════════════════
            
            if is_button_command:
                logger.info(f"⏭️ Processing button command (skipping translation)")
                
                # Book test drive start
                if message.startswith("🚗 BOOK_START:"):
                    response = self._handle_test_drive_booking(message, session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None
                
                # Details submitted
                if message.startswith("📋 DETAILS_SUBMITTED:"):
                    response = self._process_booking_details(message, session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None

                # Location selection
                if message.startswith("📍 LOCATION_TYPE:"):
                    response = self._handle_location_selection(message, session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None

                # Branch selection
                if message.startswith("📍 BRANCH_SELECTED:"):
                    response = self._handle_branch_selection(message, session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None

                # Address submission
                if message.startswith("📍 ADDRESS_SUBMITTED:"):
                    response = self._handle_address_submission(message, session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None

                # Date selection
                if message.startswith("📅 SELECT_DATE:"):
                    date_str = message.replace("📅 SELECT_DATE:", "").strip()
                    vehicle_id = session.get('pending_booking', {}).get('vehicle_id')
                    
                    if vehicle_id:
                        user_name = session.get('user_name', 'there')
                        
                        response = f"""
<div style='padding: 15px; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <p style='margin: 0; font-size: 1.05em;'>
        <strong>Perfect choice, {user_name}!</strong> 📅
    </p>
    <p style='margin: 5px 0 0 0; opacity: 0.95; font-size: 0.95em;'>
        I've got your date. Now, let's pick a time that works best for you.
    </p>
</div>

{self._show_time_slots(vehicle_id, date_str)}
"""
                        session['pending_booking']['date'] = date_str
                        self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                        session['conversation_history'].append({
                            'timestamp': datetime.now().isoformat(),
                            'message': response,
                            'role': 'assistant'
                        })
                        self._save_session_to_neo4j(session_id, session)
                        return response, None
                
                # Time selection and booking confirmation
                if message.startswith("⏰ CONFIRM_BOOKING:"):
                    parts = message.replace("⏰ CONFIRM_BOOKING:", "").strip().split("|")
                    if len(parts) == 3:
                        vehicle_id, date_str, time_str = parts
                        user_name = session.get('user_name', 'Customer')
                        
                        confirmation_msg = f"""
<div style='padding: 15px; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <p style='margin: 0; font-size: 1.05em;'>
        <strong>Excellent, {user_name}!</strong> 🎯
    </p>
    <p style='margin: 5px 0 0 0; opacity: 0.95; font-size: 0.95em;'>
        I'm finalizing your booking right now...
    </p>
</div>
"""
                        
                        response = confirmation_msg + self._confirm_booking(vehicle_id, date_str, time_str, session)
                        self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                        session['conversation_history'].append({
                            'timestamp': datetime.now().isoformat(),
                            'message': response,
                            'role': 'assistant'
                        })
                        self._save_session_to_neo4j(session_id, session)
                        return response, None
                
                # Reschedule command
                if message.startswith("🔄 RESCHEDULE:"):
                    booking_id = message.replace("🔄 RESCHEDULE:", "").strip()
                    response = self._handle_reschedule_request(f"Reschedule booking {booking_id}", session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None
                
                # Cancel command
                if message.startswith("❌ CANCEL:"):
                    booking_id = message.replace("❌ CANCEL:", "").strip()
                    response = self._handle_cancel_request(f"Cancel booking {booking_id}", session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None
                
                # Handle reschedule flow
                if 'reschedule_booking' in session:
                    reschedule_data = session['reschedule_booking']
                    user_name = session.get('user_name', 'there')
                    
                    if message.startswith("📅 SELECT_DATE:"):
                        date_str = message.replace("📅 SELECT_DATE:", "").strip()
                        
                        response = self._show_time_slots(reschedule_data['vehicle_id'], date_str)
                        self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                        session['conversation_history'].append({
                            'timestamp': datetime.now().isoformat(),
                            'message': response,
                            'role': 'assistant'
                        })
                        self._save_session_to_neo4j(session_id, session)
                        return response, None
                    
                    if message.startswith("⏰ CONFIRM_BOOKING:"):
                        parts = message.replace("⏰ CONFIRM_BOOKING:", "").strip().split("|")
                        if len(parts) == 3:
                            _, new_date, new_time = parts
                            
                            response = self._complete_reschedule_booking(
                                reschedule_data['booking_id'], 
                                new_date, 
                                new_time,
                                session
                            )
                            self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                            session['conversation_history'].append({
                                'timestamp': datetime.now().isoformat(),
                                'message': response,
                                'role': 'assistant'
                            })
                            session.pop('reschedule_booking', None)
                            self._save_session_to_neo4j(session_id, session)
                            return response, None

                # Handle feedback submission
                if message.startswith("💬 FEEDBACK:"):
                    response = self._process_feedback(message, session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None

                # Handle escalation
                if message.startswith("🆘 ESCALATE:"):
                    response = self._handle_escalation(message, session)
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    return response, None

                # End agent session
                if message.startswith("🔚 END_AGENT_SESSION"):
                    response = self.gradio_transfer.end_transfer(session_id, ended_by='customer')
                    
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    
                    if 'active_agent_transfer' in session:
                        del session['active_agent_transfer']
                    
                    self._save_session_to_neo4j(session_id, session)
                    
                    return response, None
            
            # ═══════════════════════════════════════════════════════════
            # ✅ STEP 1.5: CHECK FOR LANGUAGE CHANGE COMMANDS (BEFORE TRANSLATION!)
            # ═══════════════════════════════════════════════════════════

            language_change_patterns = [
                (r'\b(change|switch|set|use)\s+(to|language to|lang to)?\s*(en|english)\b', 'en'),
                (r'\b(change|switch|set|use)\s+(to|language to|lang to)?\s*(ar|arabic)\b', 'ar'),
                (r'\b(change|switch|set|use)\s+(to|language to|lang to)?\s*(fr|french)\b', 'fr'),
                (r'\b(change|switch|set|use)\s+(to|language to|lang to)?\s*(es|spanish)\b', 'es'),
                (r'\b(change|switch|set|use)\s+(to|language to|lang to)?\s*(de|german)\b', 'de'),
                (r'\b(change|switch|set|use)\s+(to|language to|lang to)?\s*(zh|chinese)\b', 'zh'),
                (r'\b(change|switch|set|use)\s+(to|language to|lang to)?\s*(hi|hindi)\b', 'hi'),
                (r'\b(change|switch|set|use)\s+(to|language to|lang to)?\s*(ur|urdu)\b', 'ur'),
            ]

            message_lower_check = message.lower()

            for pattern, lang_code in language_change_patterns:
                if re.search(pattern, message_lower_check, re.IGNORECASE):
                    logger.info(f"🌐 Language change detected: switching to {lang_code}")
                    
                    # Update session language
                    session['preferred_language'] = lang_code
                    
                    # Language names
                    language_names = {
                        'en': 'English', 'ar': 'Arabic', 'fr': 'French', 
                        'es': 'Spanish', 'de': 'German', 'zh': 'Chinese',
                        'hi': 'Hindi', 'ur': 'Urdu'
                    }
                    
                    lang_name = language_names.get(lang_code, lang_code)
                    
                    response = f"""
<div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>🌐</span>
        <span>Language Updated!</span>
    </h3>
    <p style='margin: 0; opacity: 0.95; font-size: 1.05em;'>
        I've switched to {lang_name}. How can I help you today?
    </p>
</div>
"""
                    
                    # Save and return immediately
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    
                    return response, None

            # ═══════════════════════════════════════════════════════════
            # ✅ STEP 2: LANGUAGE DETECTION & TRANSLATION TO ENGLISH
            # (Now runs AFTER language command checks)
            # ═══════════════════════════════════════════════════════════
            
            original_language = detected_language or session.get('preferred_language', 'en')
            
            # If not explicitly detected, auto-detect from text
            if original_language == 'en' and not detected_language:
                try:
                    text_to_detect = message.strip().lower()
                    
                    # If very short (< 10 chars) and contains common English words, assume English
                    if len(text_to_detect) < 10:
                        english_greetings = ['hi', 'hello', 'hey', 'hiya', 'yo', 'bye', 'goodbye', 'later',
                                            'good', 'morning', 'afternoon', 'evening', 'night',
                                            'thanks', 'thank', 'ok', 'okay', 'yes', 'no', 'sure', 'fine',
                                            'great', 'awesome', 'cool', 'nice', 'perfect', 'excellent',
                                            'wonderful', 'amazing', 'fantastic', 'brilliant', 'superb', 'super',
                                            'home', 'address', 'book', 'booking', 'drive', 'test',
                                            'vehicle', 'car', 'cars', 'show', 'find', 'search', 'help',
                                            'want', 'need', 'like', 'love',
                                            'what', 'when', 'where', 'who', 'why', 'how', 'can', 'let it be']
                        if any(word in text_to_detect for word in english_greetings):
                            original_language = 'en'
                            logger.info(f"🔍 Short text with English word detected → 'en'")
                        else:
                            original_language = self.translation.detect_language(message)
                            logger.info(f"🔍 Auto-detected language: {original_language}")
                    elif text_to_detect.isascii() and len(text_to_detect) < 20:
                        original_language = 'en'
                        logger.info(f"🔍 Short ASCII text detected → 'en'")
                    else:
                        original_language = self.translation.detect_language(message)
                        logger.info(f"🔍 Auto-detected language: {original_language}")
                        
                except Exception as e:
                    logger.warning(f"Language detection failed: {e}")
                    original_language = 'en'
            
            # Only update language from actual user messages (not button commands)
            if not is_button_command:
                session['preferred_language'] = original_language
                logger.info(f"📝 Updated preferred language to: {original_language}")
            else:
                logger.info(f"⏭️ Keeping existing language: {session.get('preferred_language', 'en')} (button command)")
            
            # Translate to English for processing
            message_to_process = message
            if original_language not in ['en', 'en-US', 'en-GB'] and not is_button_command:
                try:
                    logger.info(f"🌍 Translating {original_language} → en")
                    logger.info(f"   Original: '{message[:100]}...'")
                    
                    message_to_process = self._safe_translate_to_english(message, original_language)
                    
                    logger.info(f"   English: '{message_to_process[:100]}...'")
                except Exception as e:
                    logger.error(f"❌ Translation error: {e}")
                    message_to_process = message  # Fallback to original
            elif is_button_command:
                logger.info(f"⏭️ Skipping translation for button command")
            
            # ═══════════════════════════════════════════════════════════
            # CHECK IF BOOKING WITHOUT VEHICLE
            # ═══════════════════════════════════════════════════════════
            
            booking_keywords = ['book', 'booking', 'test drive', 'appointment', 
                           'schedule', 'reserve', 'arrange', 'appoint']
        
            if (any(keyword in message_to_process.lower() for keyword in booking_keywords) and 
                not message.startswith("🚗 BOOK_START:")):
            
                viewed_vehicles = session.get('viewed_vehicles', [])
            
                if not viewed_vehicles or len(viewed_vehicles) == 0:
                    logger.info("🚫 Booking requested but no vehicles viewed")
                
                    response = """
<div style='padding: 30px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
            border-radius: 16px; color: white; margin: 20px 0; text-align: center;'>
    <div style='font-size: 4em; margin-bottom: 15px;'>🔍</div>
    <h2 style='margin: 0 0 15px 0;'>Let's Find Your Perfect Car First!</h2>
</div>
<div style='padding: 25px; background: white; border-radius: 12px; margin: 15px 0;'>
    <h3 style='margin: 0 0 20px 0; color: #374151;'>🚗 What type of vehicle interests you?</h3>
    <ul style='margin: 0; padding-left: 20px; line-height: 2.2; color: #374151;'>
        <li><strong>"Show me SUVs"</strong></li>
        <li><strong>"I need a family car under 200k"</strong></li>
        <li><strong>"Show Toyota vehicles"</strong></li>
    </ul>
</div>
"""
                    
                    # ✅ Translate response if needed
                    if original_language not in ['en', 'en-US', 'en-GB']:
                        response = self._translate_response(response, original_language)
                
                    self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': response,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                
                    return response, None
            # ═══════════════════════════════════════════════════════════
            # PRIORITY 2.5: AGENT TRANSFER DETECTION & DECISION LOGIC
            # ═══════════════════════════════════════════════════════════

            agent_transfer_phrases = [
                'talk to human', 'speak to human', 'human agent', 'real person',
                'talk to agent', 'speak to agent', 'connect me to agent',
                'transfer to agent', 'i want agent', 'need human help',
                'speak to someone', 'talk to person', 'live agent',
                'live support', 'customer service', 'representative'
            ]

            auto_transfer_conditions = {
                'explicit_request': False,
                'severe_negative_sentiment': False,
                'multiple_failed_attempts': False,
                'repeated_negative_feedback': False
            }

            # ✅ FIXED: Check for agent transfer confirmation FIRST (before other checks)
            is_confirming_transfer = message.startswith("CONFIRM_AGENT_TRANSFER:")
            
            if is_confirming_transfer:
                logger.info("✅ Agent transfer CONFIRMED by user")
                session.pop('pending_agent_transfer', None)
                auto_transfer_conditions['explicit_request'] = True
                # Will skip showing confirmation screen below

            # Check for explicit transfer request (use English message)
            elif any(phrase in message_to_process.lower() for phrase in agent_transfer_phrases):
                auto_transfer_conditions['explicit_request'] = True
                logger.info(f"👨 EXPLICIT AGENT TRANSFER requested")

            # Check for severe negative sentiment
            if session.get('last_sentiment') == 'severe_negative':
                auto_transfer_conditions['severe_negative_sentiment'] = True
                logger.warning(f"🚨 AUTO-TRANSFER: Severe negative sentiment detected")

            # Track sentiment history
            if 'sentiment_history' not in session:
                session['sentiment_history'] = []

            # Check for repeated negative feedback
            if len(session.get('sentiment_history', [])) >= 5:
                recent_sentiments = session['sentiment_history'][-5:]
                negative_count = sum(1 for s in recent_sentiments if s in ['negative', 'severe_negative'])
    
                if negative_count >= 3:
                    auto_transfer_conditions['repeated_negative_feedback'] = True
                    logger.warning(f"🚨 AUTO-TRANSFER: {negative_count} negative in last 5")

            # Track failed interactions
            if 'failed_interactions' not in session:
                session['failed_interactions'] = 0

            if session.get('failed_interactions', 0) >= 3:
                auto_transfer_conditions['multiple_failed_attempts'] = True
                logger.warning(f"🚨 AUTO-TRANSFER: {session['failed_interactions']} failures")

            # Check for frustration keywords (use English message)
            frustration_keywords = [
                'frustrated', 'annoyed', 'waste of time', 'useless',
                'not helping', 'not working', 'give up', 'forget it',
                'terrible service', 'worst', 'horrible experience'
            ]

            if any(kw in message_to_process.lower() for kw in frustration_keywords):
                auto_transfer_conditions['severe_negative_sentiment'] = True
                logger.warning(f"🚨 AUTO-TRANSFER: Frustration detected")

            is_vip = self._check_vip_status(session.get('user_email'))
            priority = 'normal'
            if is_vip and any(auto_transfer_conditions.values()):
                priority = 'urgent'
                logger.info(f"👑 VIP transfer - upgrading to URGENT")

            # Should we transfer?
            should_transfer = any(auto_transfer_conditions.values())

            if should_transfer:
                # ✅ FIXED: Show confirmation ONLY for first-time explicit requests (not for confirmations or severe issues)
                if (auto_transfer_conditions['explicit_request'] and 
                    not auto_transfer_conditions['severe_negative_sentiment'] and
                    not auto_transfer_conditions['repeated_negative_feedback'] and
                    not auto_transfer_conditions['multiple_failed_attempts'] and
                    not is_confirming_transfer and  # ✅ Skip if already confirming
                    not session.get('pending_agent_transfer')):
                    
                    session['pending_agent_transfer'] = True
                    
                    confirmation = f"""
<div style='padding: 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 16px; color: white; margin: 20px 0;'>
    <h3 style='margin: 0 0 15px 0;'>👋 I'm Here to Help!</h3>
    <p style='margin: 0; font-size: 1.1em; line-height: 1.6;'>
        Before connecting you to our team, let me see if I can help right away!
    </p>
</div>

<div style='padding: 25px; background: white; border-radius: 12px; border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 20px 0;'>💡 I Can Instantly Help With:</h4>
    
    <div style='display: grid; gap: 12px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {{
                chatInput.value = "Show me available vehicles";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }}
        ' style='padding: 15px; background: #f3f4f6; border: 2px solid #e5e7eb; border-radius: 10px;
                 cursor: pointer; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="#f3f4f6";'>
            <strong>🚗 Search & Book Test Drives</strong><br>
            <span style='color: #6b7280; font-size: 0.9em;'>Find your perfect vehicle instantly</span>
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {{
                chatInput.value = "What are my booking options?";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }}
        ' style='padding: 15px; background: #f3f4f6; border: 2px solid #e5e7eb; border-radius: 10px;
                 cursor: pointer; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="#f3f4f6";'>
            <strong>📅 View/Manage Bookings</strong><br>
            <span style='color: #6b7280; font-size: 0.9em;'>Check or modify your appointments</span>
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {{
                chatInput.value = "Tell me about financing options";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }}
        ' style='padding: 15px; background: #f3f4f6; border: 2px solid #e5e7eb; border-radius: 10px;
                 cursor: pointer; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="#f3f4f6";'>
            <strong>💰 Pricing & Financing</strong><br>
            <span style='color: #6b7280; font-size: 0.9em;'>Get immediate answers on costs</span>
        </button>
    </div>
    
    <div style='margin-top: 20px; padding-top: 20px; border-top: 2px solid #e5e7eb;'>
        <p style='margin: 0 0 12px 0; color: #6b7280; font-size: 0.95em;'>
            Still need to speak with someone?
        </p>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {{
                chatInput.value = "CONFIRM_AGENT_TRANSFER:yes";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }}
        ' style='width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 color: white; border: none; padding: 15px; border-radius: 10px; 
                 cursor: pointer; font-weight: 600; font-size: 1.05em;'>
            👨 Yes, Connect Me to Human Agent →
        </button>
    </div>
</div>
"""
                    # Translate if needed
                    if original_language not in ['en', 'en-US', 'en-GB']:
                        confirmation = self._translate_response(confirmation, original_language)
                    
                    self._save_message_to_neo4j(session_id, confirmation, 'assistant', user_email)
                    session['conversation_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'message': confirmation,
                        'role': 'assistant'
                    })
                    self._save_session_to_neo4j(session_id, session)
                    
                    return confirmation, None
                
                # ✅ PROCEED WITH ACTUAL TRANSFER (for confirmations or severe cases)
                logger.info(f"🔄 Proceeding with agent transfer")
                
                # Determine reason and priority for actual transfer
                if auto_transfer_conditions['severe_negative_sentiment'] or auto_transfer_conditions['repeated_negative_feedback']:
                    reason = 'severe_negative_sentiment'
                    priority = 'urgent'
                    logger.error(f"🚨 URGENT TRANSFER: Severe negative")
    
                elif auto_transfer_conditions['multiple_failed_attempts']:
                    reason = 'multiple_failures'
                    priority = 'high'
                    logger.warning(f"⚠️ HIGH PRIORITY TRANSFER: Multiple failures")
    
                elif auto_transfer_conditions['explicit_request']:
                    reason = 'customer_request'
                    priority = 'normal'
                    logger.info(f"ℹ️ NORMAL TRANSFER: Customer requested")
    
                else:
                    reason = 'general_support'
                    priority = 'normal'
    
                logger.info(f"🔄 Transfer - Reason: {reason}, Priority: {priority}")
    
                response, transfer_state = self.gradio_transfer.request_transfer(
                    session_id=session_id,
                    reason=reason,
                    user_email=session.get('user_email', 'unknown'),
                    conversation_history=session['conversation_history'],
                    user_context={
                        'viewed_vehicles': session.get('viewed_vehicles', []),
                        'interests': session.get('interests', []),
                        'message_count': session['message_count'],
                        'failed_interactions': session.get('failed_interactions', 0),
                        'last_sentiment': session.get('last_sentiment', 'neutral'),
                        'sentiment_history': session.get('sentiment_history', [])
                    },
                    priority=priority
                )
    
                if transfer_state:
                    session['active_agent_transfer'] = transfer_state
                    session['transfer_initiated_at'] = datetime.now().isoformat()
                    session['transfer_reason'] = reason
                    logger.info(f"✅ Transfer state saved: {transfer_state}")
                
                # ✅ Translate response if needed
                if original_language not in ['en', 'en-US', 'en-GB']:
                    response = self._translate_response(response, original_language)
    
                self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                session['conversation_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'message': response,
                    'role': 'assistant'
                })
                self._save_session_to_neo4j(session_id, session)
    
                return response, None

            # Check if agent is active
            if self.gradio_transfer.is_agent_active(session_id):
                logger.info(f"👨 Human agent active for session: {session_id}")
    
                typing_html, is_typing = self.gradio_transfer.get_agent_response(session_id, message)
                
                # ✅ NEW: Add end session button to typing indicator
                if "Agent is typing" in typing_html or "waiting for" in typing_html.lower():
                    typing_html += """
<div style='padding: 15px; background: #fef3c7; border-radius: 10px; margin: 15px 0;'>
    <button onclick='
        if (confirm("Are you sure you want to end this conversation with the human agent?")) {
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {
                chatInput.value = "🔚 END_AGENT_SESSION";
                chatInput.dispatchEvent(new Event("input", { bubbles: true }));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }
        }
    ' style='width: 100%; background: #ef4444; color: white; border: none; padding: 12px;
             border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.2s;'
       onmouseover='this.style.background="#dc2626";'
       onmouseout='this.style.background="#ef4444";'>
        ❌ End Conversation with Agent
    </button>
</div>
"""
    
                self._save_message_to_neo4j(session_id, message, 'user', user_email)
                session['conversation_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'message': message,
                    'role': 'user'
                })
    
                return typing_html, None
        
            # ═══════════════════════════════════════════════════════════
            # ✅ STEP 3: CHECK SENTIMENT (CAREFUL FILTERING)
            # ═══════════════════════════════════════════════════════════
            
            word_count = len(message_to_process.split())
            
            # Check for command emojis (exclude these)
            has_command_emoji = any(cmd in message for cmd in ['🚗', '📅', '⏰', '✅', '❌', '⭐', '📝', '🆘'])
            
            # Check if vehicle query
            vehicle_query_indicators = [
                'show', 'find', 'search', 'looking for', 'want', 'need',
                'vehicles', 'cars', 'suv', 'sedan', 'truck', 'toyota', 'honda',
                'ford', 'bmw', 'mercedes', 'audi', 'lexus', 'tesla', 'byd',
                'price', 'budget', 'under', 'between', 'luxury', 'cheap',
                'compare', 'difference', 'features', 'model', 'year'
            ]
            is_vehicle_query = any(indicator in message_to_process.lower() for indicator in vehicle_query_indicators)
            
            # Check for social patterns
            social_patterns = [
                r'\bhi\b', r'\bhello\b', r'\bhey\b', r'\bhiya\b', r'\byo\b',
                r'\bbye\b', r'\bgoodbye\b', r'^see you', r'\blater\b',
                r'\bthanks?\b', r'\bthank you\b', r'\bthx\b', r'\bty\b',
                r'\bok\b', r'\bokay\b', r'\balright\b', r'\bsure\b',
                r'^good morning', r'^good afternoon', r'^good evening', r'^good night'
            ]
            is_social = any(re.search(pattern, message_to_process.lower()) for pattern in social_patterns)
            
            # Strong positive keywords
            strong_positive_keywords = [
                'excellent', 'amazing', 'perfect', 'fantastic', 'wonderful', 'love', 
                'great', 'awesome', 'brilliant', 'outstanding', 'superb', 'magnificent',
                'super happy', 'so happy', 'very happy', 'extremely happy', 'really happy',
                'super good', 'so good', 'very good', 'really good',
                'super excited', 'so excited', 'very excited',
                'love it', 'loved it', 'absolutely love'
            ]
            has_positive_keyword = any(kw in message_to_process.lower() for kw in strong_positive_keywords)
            
            # Strong negative keywords
            strong_negative_keywords = [
                'you are bad', 'you are wrong', 'you are terrible', 'you are incorrect',
                'you\'re bad', 'you\'re wrong', 'you\'re terrible', 'you\'re incorrect',
                'not correct', 'not right', 'not accurate', 'not working', 'not helpful',
                'answer is wrong', 'answer is incorrect', 'answer is not correct',
                'this is wrong', 'this is incorrect', 'this is bad', 'this is terrible'
            ]
            has_negative_keyword = any(kw in message_to_process.lower() for kw in strong_negative_keywords)
            
            # Simple negative words (only if very short message)
            simple_negative_words = ['bad', 'terrible', 'awful', 'horrible', 'worst', 'wrong', 'incorrect']
            is_simple_negative = (word_count <= 4 and 
                                 any(message_to_process.lower().strip() == word or 
                                     message_to_process.lower().strip().startswith(word + ' ') or
                                     message_to_process.lower().strip().endswith(' ' + word)
                                     for word in simple_negative_words))
            
            # ✅ DECISION: Should we check sentiment?
            should_check_sentiment = (
                (is_social or has_negative_keyword or has_positive_keyword or is_simple_negative) and 
                not has_command_emoji and 
                not is_vehicle_query and
                word_count <= 10
            )
            
            if should_check_sentiment:
                logger.info(f"🎭 Checking sentiment for: '{message_to_process}'")
                
                # ✅ USE ML-BASED SENTIMENT ANALYZER + KEYWORD RULES
                sentiment_result = self._enhanced_sentiment_check(message_to_process, session)
                
                # Track sentiment
                if sentiment_result:
                    detected_sentiment = sentiment_result.get('sentiment', 'neutral')
                    session['last_sentiment'] = detected_sentiment
        
                    if 'sentiment_history' not in session:
                        session['sentiment_history'] = []
                    session['sentiment_history'].append(detected_sentiment)
                    session['sentiment_history'] = session['sentiment_history'][-10:]
                
                    # Check message type (only if sentiment_result exists)
                    message_type = sentiment_result.get('message_type', 'sentiment')
                    
                    if message_type in ['greeting', 'farewell', 'night_farewell', 'thank_you', 'acknowledgment']:
                        response = sentiment_result['response']
                        
                        # ✅ Translate if needed
                        if original_language not in ['en', 'en-US', 'en-GB']:
                            response = self._translate_response(response, original_language)
                        
                        # ✅ NEW: Check if email prompt needed
                        email_prompt = None
                        if (not session.get('user_email') and 
                            session['message_count'] >= 3 and 
                            not session.get('email_prompted')):
                            email_prompt = self._generate_email_prompt()
                            session['email_prompted'] = True
                            logger.info("📧 Email prompt generated")
    
                        self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                        session['conversation_history'].append({
                            'timestamp': datetime.now().isoformat(),
                            'message': response,
                            'role': 'assistant'
                        })
                        self._save_session_to_neo4j(session_id, session)
                        logger.info(f"✅ Responded with {message_type}")
                        return response, email_prompt

                    elif sentiment_result['sentiment'] in ['positive', 'negative', 'severe_negative', 'mixed']:
                        response = sentiment_result['response']
                        
                        if sentiment_result.get('show_support_options'):
                            response += self.sentiment_handler.generate_support_options()
                        
                        if sentiment_result.get('should_escalate'):
                            response += sentiment_result['escalation_message']
                            logger.warning(f"🚨 ESCALATION TRIGGERED for {user_email}")
                        
                        # ✅ Translate if needed
                        if original_language not in ['en', 'en-US', 'en-GB']:
                            response = self._translate_response(response, original_language)
                        
                        # ✅ NEW: Check if email prompt needed
                        email_prompt = None
                        if (not session.get('user_email') and 
                            session['message_count'] >= 3 and 
                            not session.get('email_prompted')):
                            email_prompt = self._generate_email_prompt()
                            session['email_prompted'] = True
                            logger.info("📧 Email prompt generated")
    
                        self._save_message_to_neo4j(session_id, response, 'assistant', user_email)
                        session['conversation_history'].append({
                            'timestamp': datetime.now().isoformat(),
                            'message': response,
                            'role': 'assistant'
                        })
                        self._save_session_to_neo4j(session_id, session)
                        logger.info(f"✅ Responded with {message_type}")
                        return response, email_prompt
                    
                    logger.info(f"⏭️ Sentiment detected but not strong enough, continuing to agent")
                else:
                    logger.info(f"⏭️ Neutral sentiment, continuing to agent")

            # ═══════════════════════════════════════════════════════════
            # ✅ STEP 4: PROCESS WITH AGENT (using English message)
            # ═══════════════════════════════════════════════════════════
            
            # Check if email needed
            email_prompt = None
            if (not session.get('user_email') and 
                session['message_count'] >= 3 and 
                not session.get('email_prompted')):
                email_prompt = self._generate_email_prompt()
                session['email_prompted'] = True
            
            # Build context
            context = {
                'user_id': user_id,
                'session_id': session_id,
                'user_email': session.get('user_email'),
                'session_messages': session['message_count'],
                'last_intent': session.get('last_intent'),
                'conversation_history': session['conversation_history'][-5:],
                'viewed_vehicles': session.get('viewed_vehicles', []),
                'interests': session.get('interests', []),
                'preferred_language': session.get('preferred_language', 'en')
            }
            
            logger.info(f"💬 Processing with agent: '{message_to_process[:50]}...'")
            
            # Store user message
            self._save_message_to_neo4j(
                session_id=session_id,
                message=message,  # Save original language
                role='user',
                user_email=session.get('user_email')
            )
            
            session['conversation_history'].append({
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'role': 'user'
            })
            
            # Check if financial query
            if self._is_financial_query(message_to_process):
                response = self._handle_financial_query(message_to_process, session)
            else:
                # Use agent with ENGLISH message
                agent_result = self.agent.act(message_to_process, context=context)
                session['last_intent'] = agent_result['reasoning']['intent']['type']
                response = self._generate_rich_response(agent_result, session, message_to_process)
            
            # ═══════════════════════════════════════════════════════════
            # ✅ STEP 5: TRANSLATE RESPONSE BACK TO USER'S LANGUAGE
            # ═══════════════════════════════════════════════════════════
            
            if original_language not in ['en', 'en-US', 'en-GB']:
                logger.info(f"🌍 Translating response back to {original_language}")
                response = self._translate_response(response, original_language)
            
            # Store assistant response
            self._save_message_to_neo4j(
                session_id=session_id,
                message=response,
                role='assistant',
                user_email=session.get('user_email')
            )
            
            session['conversation_history'].append({
                'timestamp': datetime.now().isoformat(),
                'message': response,
                'role': 'assistant'
            })
            
            # Save session
            self._save_session_to_neo4j(session_id, session)
            
            # Add recommendations
            if session['message_count'] >= 3 and session['message_count'] % 5 == 0:
                recommendations = self._get_smart_recommendations(session)
                if recommendations:
                    response += recommendations
            
            return response, email_prompt
            
        except Exception as e:
            logger.error(f"❌ Chatbot error: {e}", exc_info=True)
            return self._error_response(), None
           

    # ═══════════════════════════════════════════════════════════
    # ✅ NEW HELPER METHODS FOR TRANSLATION & SENTIMENT
    # ═══════════════════════════════════════════════════════════
    
    def _translate_response(self, html_response: str, target_lang: str) -> str:
        """
        Translate HTML response while preserving structure
        Extracts text, translates, wraps back in simple HTML
        """
        try:
            # Extract clean text
            has_complex_html = (
                '<div' in html_response and 
                ('gradient' in html_response or '<h' in html_response)
            )
        
            if has_complex_html:
                logger.info(f"⏭️ Skipping translation (preserves formatting)")
                return html_response  # Keep original formatting
            clean_text = self._extract_text_from_html(html_response)
            
            if not clean_text or len(clean_text.strip()) < 5:
                return html_response
            
            # Translate
            translated_text = self.translation.translate_from_english(clean_text, target_lang)
            
            # Wrap in simple HTML with same styling
            translated_html = f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #667eea; margin: 15px 0;'>
    <p style='color: #374151; line-height: 1.6; white-space: pre-line;'>{translated_text}</p>
</div>
"""
            
            logger.info(f"✅ Response translated to {target_lang}")
            return translated_html
            
        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            return html_response  # Fallback to original

    def _safe_translate_to_english(self, text: str, source_lang: str) -> str:
        """
        Wrapper for translation with validation to prevent corruption
        """
        if not text or not text.strip():
            return text
    
        # Clean whitespace
        text = ' '.join(text.split())
    
        try:
            result = self.translation.translate_to_english(text, source_lang)
        
            # Validate result - check for corruption
            if result and len(result) > 0:
                # Check for unexpected scripts (Cyrillic/Chinese)
                has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in result)
                has_chinese = any('\u4E00' <= char <= '\u9FFF' for char in result)
            
                # If translating from Arabic and getting Cyrillic/Chinese, it's corrupted
                if source_lang in ['ar', 'ur', 'fa'] and (has_cyrillic or has_chinese):
                    logger.error(f"❌ Translation corrupted (unexpected script)")
                    return text  # Return original instead of corrupted
            
                # Check if translation identical to original (likely failed)
                if result == text and source_lang not in ['en', 'en-US', 'en-GB']:
                    logger.warning(f"⚠️ Translation returned same text")
                    return text
            
                return result
            else:
                return text
            
        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            return text
    
    def _enhanced_sentiment_check(self, message: str, session: Dict) -> Optional[Dict]:
        """
        Enhanced sentiment analysis combining ML + keyword-based rules + NEGATION detection
        """
        message_lower = message.lower().strip()
        
        # ✅ FIX: NEGATION DETECTION (Check this FIRST before any other processing!)
        negation_patterns = [
            'no ', 'not ', "don't", "doesn't", "didn't", "won't", "can't", 
            "isn't", "aren't", "wasn't", "weren't", "haven't", "hasn't",
            "couldn't", "wouldn't", "shouldn't", "never"
        ]
        
        has_negation = any(neg in message_lower for neg in negation_patterns)
        
        if has_negation:
            logger.info(f"🔄 Negation detected in: '{message}'")
            
            # Check what's being negated
            positive_words = ['happy', 'good', 'great', 'excellent', 'perfect', 'love', 'satisfied', 'pleased', 'wonderful']
            negative_words = ['bad', 'terrible', 'awful', 'horrible', 'hate', 'angry', 'frustrated', 'upset', 'disappointed']
            
            has_positive_word = any(word in message_lower for word in positive_words)
            has_negative_word = any(word in message_lower for word in negative_words)
            
            if has_positive_word:
                # "not happy", "no good", "not satisfied" → NEGATIVE
                logger.info("   → Negated positive word = NEGATIVE sentiment")
                return {
                    'sentiment': 'negative',
                    'confidence': 0.85,
                    'message': message,
                    'handler_type': 'negative_sentiment_negation'
                }
            elif has_negative_word:
                # "not bad", "no problem" → NEUTRAL/POSITIVE
                logger.info("   → Negated negative word = NEUTRAL/POSITIVE sentiment")
                return None  # Let it go to neutral handling
        
        logger.info(f"🎭 Checking sentiment for: '{message}'")
        
        # STEP 1: Use ML-based sentiment analyzer
        ml_result = self.sentiment_analyzer.analyze(message)
        ml_sentiment = ml_result.get('label', 'NEUTRAL')
        ml_score = ml_result.get('score', 0.5)
        
        logger.info(f"🤖 ML Sentiment: {ml_sentiment} ({ml_score:.2f})")
        
        # ✅ FIX: Override ML if negation was detected but ML still says POSITIVE
        if has_negation and ml_sentiment == 'POSITIVE':
            logger.info("   ⚠️ ML says POSITIVE but negation found → Overriding to NEGATIVE")
            ml_sentiment = 'NEGATIVE'
            ml_score = 0.75
        
        # ✅ STEP 2: Check keyword-based rules (sentiment_handler)
        keyword_result = self.sentiment_handler.get_response(message)
        
        # ✅ FALLBACK: If sentiment_handler doesn't recognize greeting, handle it here
        if not keyword_result:
            # Check for basic greetings
            greeting_words = ['hi', 'hello', 'hey', 'hiya', 'yo', 'good morning', 'good afternoon', 'good evening','greetings', 'what’s up', 'howdy', 'sup', 'hey there', 'morning', 'afternoon', 'evening','heya', 'yo yo', 'hiya!', 'hiya!!', 'heyyo', 'hii', 'hiii', 'hellooo', 'hiya there', '👋', '🙋', 'hey buddy', 'hey friend']
            farewell_words = ['bye', 'goodbye', 'see you', 'later', 'good night', 'catch you later', 'take care','farewell', 'see ya', 'talk to you later', 'ciao', 'adios', 'peace out', 'until next time','bye bye', 'bye!', 'byee', 'laters', 'ttyl', '✌️', '👋', 'sleep tight', 'have a good one', 'see you soon']
            thanks_words = ['thanks', 'thank you', 'thx', 'ty', 'much appreciated', 'thanks a lot', 'thank you very much', 'thanks so much', 'thanks a bunch', 'thanks heaps', 'ta', 'thnx', 'cheers', 'grateful', 'many thanks', '🙏', 'thanks!', 'thanks!!', 'tyvm', 'thank u', 'thanks friend', 'thanks buddy', 'thankies', 'thx a lot', 'thanks heaps!', 'thx so much']
            apology_words = ['sorry', 'my bad', 'oops', 'forgive me', 'apologies', 'i apologize', 'pardon me','so sorry', 'sry', 'sorry!', 'sorry!!', 'mea culpa', 'oopsie', '🙁', '😔', '😢', 'forgive', 'forgive me please']
            congrats_words = ['congratulations', 'congrats', 'well done', 'good job', 'kudos', 'bravo', 'nice work','great job', 'way to go', 'awesome', 'fantastic', 'amazing', '👏', '🎉', '🥳', 'cheers', 'hats off', 'good going','you did it', 'way to crush it', 'well played', 'nicely done', 'congrats!', 'brilliant', 'perfect','great']

            
            if any(word in message_lower for word in greeting_words):
                return {
                    'sentiment': 'neutral',
                    'response': """
<div style='padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 16px; color: white; margin: 20px 0; text-align: center;'>
    <div style='font-size: 4em; margin-bottom: 15px;'>👋</div>
    <h2 style='margin: 0 0 10px 0;'>Hey! Great to see you!</h2>
    <p style='margin: 0; opacity: 0.95; font-size: 1.1em;'>
        Whether you're looking for luxury, performance, or family-friendly vehicles, 
        I'm here to help you find the perfect match!
    </p>
</div>
""",
                    'message_type': 'greeting',
                    'confidence': 0.95
                }
            
            elif any(word in message_lower for word in farewell_words):
                return {
                    'sentiment': 'neutral',
                    'response': "👋 Goodbye! Feel free to come back anytime you need help finding your perfect vehicle!",
                    'message_type': 'farewell',
                    'confidence': 0.95
                }
            
            elif any(word in message_lower for word in thanks_words):
                return {
                    'sentiment': 'positive',
                    'response': "😊 You're welcome! Happy to help. Is there anything else you'd like to know?",
                    'message_type': 'thank_you',
                    'confidence': 0.95
                }

            # Apologies detection
            elif any(word in message_lower for word in apology_words):
                return {
                    'sentiment': 'neutral',
                    'response': "No worries! 😊 Everyone makes mistakes. How can I help you further?",
                    'message_type': 'apology',
                    'confidence': 0.95
                }

            elif any(word in message_lower for word in congrats_words):
                return {
                    'sentiment': 'positive',
                    'response': "🎉 Congratulations! That’s amazing to hear! Do you want to share more details?",
                    'message_type': 'congratulations',
                    'confidence': 0.95
                }
                      
        
        if not keyword_result:
            # No keyword match, use ML result
            if ml_sentiment == 'POSITIVE' and ml_score > 0.5:
                return {
                    'sentiment': 'positive',
                    'response': "😊 That's great to hear! How can I help you today?",
                    'message_type': 'sentiment',
                    'confidence': ml_score
                }
            elif ml_sentiment == 'NEGATIVE' and ml_score > 0.5:
                return {
                    'sentiment': 'negative',
                    'response': "😔 I'm sorry to hear that. What can I do to help?",
                    'message_type': 'sentiment',
                    'confidence': ml_score,
                    'show_support_options': True
                }
            else:
                # Neutral or low confidence - don't respond
                return None
        
        # ✅ STEP 3: Keyword match found - use it (higher priority)
        logger.info(f"📋 Handler: {keyword_result.get('sentiment')} | Type: {keyword_result.get('message_type')}")
        return keyword_result

            
    # [REST OF THE METHODS REMAIN UNCHANGED - BOOKING, RESCHEDULE, CANCEL, etc.]
    # I'll include the most critical ones that might need translation:
    
    def _handle_location_selection(self, message: str, session: Dict) -> str:
        """Handle location type selection (Showroom vs Home)"""
        try:
            parts = message.replace("📍 LOCATION_TYPE:", "").strip().split("|")
            if len(parts) != 2:
                return self._error_response("Invalid location selection format")
        
            location_type = parts[0].strip().lower()
            vehicle_id = parts[1].strip()
        
            if not session.get('pending_booking'):
                session['pending_booking'] = {}
            session['pending_booking']['vehicle_id'] = vehicle_id
        
            user_name = session.get('user_name', 'there')
        
            if location_type == 'showroom':
                session['pending_booking']['location_type'] = 'Showroom'
            
                return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>🏢 Excellent Choice, {user_name}!</h3>
    <p style='margin: 0; opacity: 0.95;'>
        Now let's choose which showroom location works best for you.
    </p>
</div>

{self._show_showroom_branches(vehicle_id)}
"""
        
            elif location_type == 'home':
                session['pending_booking']['location_type'] = 'Home Delivery'
            
                return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>🏠 Perfect, {user_name}!</h3>
    <p style='margin: 0; opacity: 0.95;'>
        We'll bring the vehicle right to your door. Let me get your delivery address.
    </p>
</div>

{self._show_address_form(vehicle_id)}
"""
        
            else:
                return self._error_response("Invalid location type. Please choose Showroom or Home Delivery.")
            
        except Exception as e:
            logger.error(f"❌ Location selection error: {e}", exc_info=True)
            return self._error_response("Unable to process location selection.")
            
    def _show_showroom_branches(self, vehicle_id: str) -> str:
        """Show showroom branch selection"""
        return f"""
<div style='padding: 25px; background: white; border-radius: 16px; border: 2px solid #667eea; margin: 20px 0;
            box-shadow: 0 4px 12px rgba(102,126,234,0.2);'>
    <h3 style='color: #667eea; margin: 0 0 15px 0; font-size: 1.3em;'>🏢 Choose Showroom Branch</h3>
    <p style='margin: 0 0 20px 0; color: #374151;'>
        Select your preferred showroom location:
    </p>
    
    <div style='display: grid; gap: 12px;'>
        <!-- Branch 1: Al Badiya, Dubai -->
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "📍 BRANCH_SELECTED:Al Badiya Showroom, Dubai|{vehicle_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='padding: 18px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                 color: white; border: none; border-radius: 12px; cursor: pointer;
                 text-align: left; box-shadow: 0 4px 12px rgba(102,126,234,0.3);
                 transition: all 0.2s;'
           onmouseover='this.style.transform="scale(1.02)";'
           onmouseout='this.style.transform="scale(1)";'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='font-size: 2em;'>🏢</div>
                <div style='flex: 1;'>
                    <h4 style='margin: 0 0 5px 0; font-size: 1.1em;'>Al Badiya Showroom</h4>
                    <p style='margin: 0; opacity: 0.9; font-size: 0.85em;'>📍 Al Badiya, Dubai, UAE</p>
                </div>
            </div>
        </button>
        
        <!-- Branch 2: Sheikh Zayed Road, Dubai -->
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "📍 BRANCH_SELECTED:Sheikh Zayed Road Showroom, Dubai|{vehicle_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='padding: 18px; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                 color: white; border: none; border-radius: 12px; cursor: pointer;
                 text-align: left; box-shadow: 0 4px 12px rgba(59,130,246,0.3);
                 transition: all 0.2s;'
           onmouseover='this.style.transform="scale(1.02)";'
           onmouseout='this.style.transform="scale(1)";'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='font-size: 2em;'>🏢</div>
                <div style='flex: 1;'>
                    <h4 style='margin: 0 0 5px 0; font-size: 1.1em;'>Sheikh Zayed Road Showroom</h4>
                    <p style='margin: 0; opacity: 0.9; font-size: 0.85em;'>📍 Sheikh Zayed Road, Dubai, UAE</p>
                </div>
            </div>
        </button>
        
        <!-- Branch 3: Sharjah Toyota -->
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "📍 BRANCH_SELECTED:Sharjah Toyota, Sharjah|{vehicle_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='padding: 18px; background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
                 color: white; border: none; border-radius: 12px; cursor: pointer;
                 text-align: left; box-shadow: 0 4px 12px rgba(6,182,212,0.3);
                 transition: all 0.2s;'
           onmouseover='this.style.transform="scale(1.02)";'
           onmouseout='this.style.transform="scale(1)";'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='font-size: 2em;'>🏢</div>
                <div style='flex: 1;'>
                    <h4 style='margin: 0 0 5px 0; font-size: 1.1em;'>Sharjah Toyota</h4>
                    <p style='margin: 0; opacity: 0.9; font-size: 0.85em;'>📍 Sharjah, UAE</p>
                </div>
            </div>
        </button>
        
        <!-- Branch 4: Abu Dhabi Toyota -->
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "📍 BRANCH_SELECTED:Abu Dhabi Toyota, Abu Dhabi|{vehicle_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='padding: 18px; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
                 color: white; border: none; border-radius: 12px; cursor: pointer;
                 text-align: left; box-shadow: 0 4px 12px rgba(139,92,246,0.3);
                 transition: all 0.2s;'
           onmouseover='this.style.transform="scale(1.02)";'
           onmouseout='this.style.transform="scale(1)";'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='font-size: 2em;'>🏢</div>
                <div style='flex: 1;'>
                    <h4 style='margin: 0 0 5px 0; font-size: 1.1em;'>Abu Dhabi Toyota</h4>
                    <p style='margin: 0; opacity: 0.9; font-size: 0.85em;'>📍 Abu Dhabi, UAE</p>
                </div>
            </div>
        </button>
    </div>
    
    <div style='margin-top: 20px; padding: 15px; background: #f0f9ff; border-radius: 8px;'>
        <p style='margin: 0; color: #0369a1; font-size: 0.9em;'>
            💡 <strong>Tip:</strong> Click on your preferred branch!
        </p>
    </div>
</div>
"""

    def _show_address_form(self, vehicle_id: str) -> str:
        """Show home delivery address form"""
        return f"""
<div style='padding: 25px; background: white; border-radius: 16px; border: 2px solid #10b981; margin: 20px 0;
            box-shadow: 0 4px 12px rgba(16,185,129,0.2);'>
    <h3 style='color: #10b981; margin: 0 0 15px 0; font-size: 1.3em;'>🏠 Delivery Address</h3>
    <p style='margin: 0 0 20px 0; color: #374151; line-height: 1.6;'>
        Please provide your complete delivery address for the test drive vehicle.
    </p>
    
    <div style='padding: 20px; background: #f9fafb; border-radius: 12px; margin-bottom: 20px;'>
        <p style='margin: 0 0 15px 0; font-weight: 600; color: #374151; font-size: 1.05em;'>
            📝 Required Information:
        </p>
        <ul style='margin: 0; padding-left: 20px; color: #6b7280; line-height: 2;'>
            <li><strong>Street Address</strong> / Building Name</li>
            <li><strong>Area</strong> / Neighborhood</li>
            <li><strong>City</strong></li>
            <li><strong>Landmark</strong> (optional, but helpful)</li>
        </ul>
    </div>
    
    <div style='padding: 20px; background: #eff6ff; border-radius: 12px; margin-bottom: 20px;'>
        <p style='margin: 0 0 10px 0; color: #1e40af; font-weight: 600; font-size: 1.05em;'>
            📋 Example Format:
        </p>
        <div style='padding: 15px; background: white; border-radius: 8px; border: 1px solid #dbeafe;'>
            <code style='color: #1e3a8a; font-size: 0.95em; line-height: 1.8; display: block;'>
                Villa 123, Springs Community<br>
                Near Emirates Hills<br>
                Dubai, UAE<br>
                Landmark: Next to Springs Town Centre
            </code>
        </div>
    </div>
    
    <!-- Address Input Textarea -->
    <div style='margin-bottom: 20px;'>
        <label style='display: block; color: #374151; font-weight: 600; 
                      margin-bottom: 8px; font-size: 0.95em;'>
            📍 Your Complete Address <span style='color: #ef4444;'>*</span>
        </label>
        <textarea id='delivery_address' 
                  placeholder='Villa 123, Springs Community
Near Emirates Hills
Dubai, UAE
Landmark: Next to Springs Town Centre'
                  rows='5'
                  style='width: 100%; padding: 15px; border: 2px solid #e5e7eb; 
                         border-radius: 8px; font-size: 1em; box-sizing: border-box;
                         font-family: inherit; resize: vertical;'
                  onfocus='this.style.borderColor="#10b981";'
                  onblur='this.style.borderColor="#e5e7eb";'></textarea>
    </div>
    
    <!-- Submit Button -->
    <button onclick='
        var address = document.getElementById("delivery_address").value.trim();
        
        if (!address || address.length < 20) {{
            alert("⚠️ Please provide a complete address with at least:\\n• Street/Building\\n• Area\\n• City\\n• Landmark (optional)");
            document.getElementById("delivery_address").focus();
            return;
        }}
        
        var chatInput = document.querySelector("#chat_input textarea") || 
                       document.querySelector("textarea[placeholder*=\\"message\\"]");
        if (chatInput) {{
            chatInput.value = "📍 ADDRESS_SUBMITTED:" + address + "|{vehicle_id}";
            chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
            var sendBtn = document.querySelector("#send_btn") || 
                         document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
            if (sendBtn) sendBtn.click();
        }}
    ' style='width: 100%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
             color: white; border: none; padding: 15px; border-radius: 10px; 
             cursor: pointer; font-weight: 600; font-size: 1em;
             transition: all 0.3; box-shadow: 0 4px 12px rgba(16,185,129,0.4);'
       onmouseover='this.style.transform="scale(1.02)"; this.style.boxShadow="0 6px 16px rgba(16,185,129,0.6)";'
       onmouseout='this.style.transform="scale(1)"; this.style.boxShadow="0 4px 12px rgba(16,185,129,0.4)";'>
        ✅ Confirm Address & Continue
    </button>
    
    <div style='margin-top: 15px; padding: 15px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 8px;'>
        <p style='margin: 0; color: #92400e; font-size: 0.9em;'>
            💡 <strong>Tip:</strong> Include landmarks to help our driver find you easily!
        </p>
    </div>
</div>
"""
    
    def _generate_voice_response(self, html_response: str, language: str = 'en') -> Optional[str]:
        """Generate voice output from HTML response in user's language"""
        try:
            clean_text = self._extract_text_from_html(html_response)
            
            # Limit to reasonable length for TTS
            if len(clean_text) > 300:
                clean_text = clean_text[:300].rsplit('.', 1)[0] + '.'
            
            if not clean_text or len(clean_text.strip()) < 5:
                logger.warning("⚠️ Text too short for TTS")
                return None
            
            logger.info(f"🔊 Generating voice in '{language}': '{clean_text[:50]}...'")
            
            audio_path = self.speech_system.synthesize_speech(clean_text, language=language)
            
            if audio_path:
                logger.info(f"✅ Voice generated: {audio_path}")
                return audio_path
            else:
                logger.warning("⚠️ TTS failed")
                return None
                
        except Exception as e:
            logger.error(f"❌ Voice error: {e}")
            return None
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract clean text from HTML"""
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        text = re.sub(r'(Quick Actions|Try asking|Coming soon)', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def set_user_language(self, user_id: str, language: str):
        """Set preferred language for user"""
        if user_id in self.user_sessions:
            self.user_sessions[user_id]['preferred_language'] = language
            logger.info(f"🌐 Set language for {user_id}: {language}")
    

    def _handle_test_drive_booking(self, message: str, session: Dict) -> str:
        """Handle test drive booking request with interactive form"""
        
        # Check if this is auto-triggered from button
        if message.startswith("🚗 BOOK_START:"):
            vehicle_id = message.replace("🚗 BOOK_START:", "").strip()
            session['pending_booking'] = {
                'vehicle_id': vehicle_id,
                'step': 'collect_details'
            }
            
            # Get vehicle details
            try:
                with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                    vehicle_result = neo_session.run("""
                        MATCH (v:Vehicle {id: $vehicle_id})
                        RETURN v.make + ' ' + v.model + ' ' + v.year as vehicle_name,
                               v.image as image
                    """, vehicle_id=vehicle_id).single()
                    
                    if vehicle_result:
                        vehicle_name = vehicle_result['vehicle_name']
                        vehicle_image = vehicle_result.get('image', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400')
                    else:
                        vehicle_name = vehicle_id
                        vehicle_image = 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'
            except:
                vehicle_name = vehicle_id
                vehicle_image = 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'
            
            # Get user's existing info if available
            user_email = session.get('user_email', '')
            user_name = session.get('user_name', '')
            user_phone = session.get('user_phone', '')
            
            return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>🎉</span>
        <span>Great Choice!</span>
    </h3>
    <p style='margin: 0; opacity: 0.95; font-size: 1.05em;'>
        Let's book your test drive for the {vehicle_name}
    </p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    
    <!-- Vehicle Summary -->
    <div style='display: flex; gap: 15px; margin-bottom: 20px; padding: 15px; 
                background: #f9fafb; border-radius: 10px;'>
        <img src='{vehicle_image}' 
             style='width: 100px; height: 80px; object-fit: cover; border-radius: 8px;'
             onerror="this.src='https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'">
        <div>
            <h4 style='margin: 0 0 5px 0; color: #1f2937;'>{vehicle_name}</h4>
            <p style='margin: 0; color: #6b7280; font-size: 0.9em;'>Vehicle ID: {vehicle_id}</p>
        </div>
    </div>
    
    <h4 style='color: #374151; margin: 0 0 15px 0;'>📝 Your Details</h4>
    <p style='color: #6b7280; font-size: 0.9em; margin: 0 0 15px 0;'>
        Please fill in your information below
    </p>
    
    <!-- Name Input -->
    <div style='margin-bottom: 15px;'>
        <label style='display: block; color: #374151; font-weight: 600; 
                      margin-bottom: 5px; font-size: 0.9em;'>
            👤 Full Name <span style='color: #ef4444;'>*</span>
        </label>
        <input type='text' 
               id='booking_name' 
               value='{user_name}'
               placeholder='e.g., Ahmed Hassan'
               style='width: 100%; padding: 12px; border: 2px solid #e5e7eb; 
                      border-radius: 8px; font-size: 1em; box-sizing: border-box;'
               onfocus='this.style.borderColor="#667eea";'
               onblur='this.style.borderColor="#e5e7eb";'>
    </div>
    
    <!-- Email Input -->
    <div style='margin-bottom: 15px;'>
        <label style='display: block; color: #374151; font-weight: 600; 
                      margin-bottom: 5px; font-size: 0.9em;'>
            📧 Email Address <span style='color: #ef4444;'>*</span>
        </label>
        <input type='email' 
               id='booking_email' 
               value='{user_email}'
               placeholder='e.g., ahmed@email.com'
               style='width: 100%; padding: 12px; border: 2px solid #e5e7eb; 
                      border-radius: 8px; font-size: 1em; box-sizing: border-box;'
               onfocus='this.style.borderColor="#667eea";'
               onblur='this.style.borderColor="#e5e7eb";'>
    </div>
    
    <!-- Phone Input -->
    <div style='margin-bottom: 20px;'>
        <label style='display: block; color: #374151; font-weight: 600; 
                      margin-bottom: 5px; font-size: 0.9em;'>
            📱 Phone Number <span style='color: #ef4444;'>*</span>
        </label>
        <input type='tel' 
               id='booking_phone' 
               value='{user_phone}'
               placeholder='e.g., +971-50-123-4567'
               style='width: 100%; padding: 12px; border: 2px solid #e5e7eb; 
                      border-radius: 8px; font-size: 1em; box-sizing: border-box;'
               onfocus='this.style.borderColor="#667eea";'
               onblur='this.style.borderColor="#e5e7eb";'>
    </div>
    
    <!-- Continue Button -->
    <button onclick='
        var name = document.getElementById("booking_name").value.trim();
        var email = document.getElementById("booking_email").value.trim();
        var phone = document.getElementById("booking_phone").value.trim();
        
        if (!name) {{
            alert("⚠️ Please enter your name");
            document.getElementById("booking_name").focus();
            return;
        }}
        
        if (!email || !email.includes("@")) {{
            alert("⚠️ Please enter a valid email address");
            document.getElementById("booking_email").focus();
            return;
        }}
        
        if (!phone || phone.length < 10) {{
            alert("⚠️ Please enter a valid phone number");
            document.getElementById("booking_phone").focus();
            return;
        }}
        
        var chatInput = document.querySelector("#chat_input textarea") || 
                       document.querySelector("textarea[placeholder*=\\"message\\"]");
        if (chatInput) {{
            chatInput.value = "📋 DETAILS_SUBMITTED:name=" + name + "|email=" + email + "|phone=" + phone;
            chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
            var sendBtn = document.querySelector("#send_btn") || 
                         document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
            if (sendBtn) {{
                sendBtn.click();
            }}
        }}
    ' style='width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
             color: white; border: none; padding: 15px; border-radius: 10px; 
             cursor: pointer; font-weight: 600; font-size: 1em;
             transition: all 0.3s; box-shadow: 0 4px 12px rgba(102,126,234,0.4);'
       onmouseover='this.style.transform="scale(1.02)"; this.style.boxShadow="0 6px 16px rgba(102,126,234,0.6)";'
       onmouseout='this.style.transform="scale(1)"; this.style.boxShadow="0 4px 12px rgba(102,126,234,0.4)";'>
        ✨ Continue to Date Selection
    </button>
</div>

<div style='padding: 15px; background: #f0f9ff; border-radius: 10px; 
            border-left: 4px solid #3b82f6; margin: 15px 0;'>
    <p style='margin: 0; color: #1e40af; font-size: 0.9em;'>
        🔒 <strong>Your privacy matters:</strong> We'll only use this information for your test drive booking.
    </p>
</div>
"""
        
        # Extract vehicle ID from text message
        vehicle_id_match = re.search(r'V\d{5}', message)
        
        if vehicle_id_match:
            vehicle_id = vehicle_id_match.group(0)
            session['pending_booking'] = {
                'vehicle_id': vehicle_id,
                'step': 'collect_details'
            }
            
            return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0;'>🚗 Book Test Drive</h3>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <p style='color: #374151; margin: 0;'>
        Great! I see you want to book a test drive for vehicle <strong>{vehicle_id}</strong>.
    </p>
</div>
"""
        else:
            return """
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #667eea; margin: 0 0 15px 0;'>🚗 Book Your Test Drive</h4>
    <p style='color: #374151; margin: 0 0 15px 0;'>
        To get started, please click the <strong>"📅 Book Test Drive"</strong> button on any vehicle from your search results!
    </p>
    
    <div style='background: #f0f9ff; padding: 15px; border-radius: 8px;'>
        <p style='margin: 0; color: #1e40af; font-size: 0.9em;'>
            💡 <strong>Tip:</strong> Search for vehicles first, then click the booking button on your preferred car.
        </p>
    </div>
</div>
"""

    def _process_booking_details(self, message: str, session: Dict) -> str:
        """Process submitted booking details and show calendar"""
        try:
            # Parse the details
            details_str = message.replace("📋 DETAILS_SUBMITTED:", "").strip()
            details_parts = details_str.split("|")
            
            details = {}
            for part in details_parts:
                key, value = part.split("=", 1)
                details[key] = value
            
            # Store in session
            session['user_name'] = details.get('name', '')
            session['user_email'] = details.get('email', '')
            session['user_phone'] = details.get('phone', '')
            
            vehicle_id = session.get('pending_booking', {}).get('vehicle_id')
            
            if not vehicle_id:
                return self._error_response("Session expired. Please start again.")
            
            # Update session step
            session['pending_booking']['step'] = 'select_date'
            
            # Get vehicle name
            try:
                with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                    vehicle_result = neo_session.run("""
                        MATCH (v:Vehicle {id: $vehicle_id})
                        RETURN v.make + ' ' + v.model + ' ' + v.year as vehicle_name
                    """, vehicle_id=vehicle_id).single()
                    
                    vehicle_name = vehicle_result['vehicle_name'] if vehicle_result else vehicle_id
            except:
                vehicle_name = vehicle_id
            
            # Show thank you message and location selection
            return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>✅</span>
        <span>Thank You, {details.get('name', 'Customer')}!</span>
    </h3>
    <p style='margin: 0; opacity: 0.95;'>
        Your details have been saved. Now let's choose how you'd like to receive the vehicle!
    </p>
</div>

<div style='padding: 15px; background: white; border-radius: 10px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <div style='display: grid; grid-template-columns: auto 1fr; gap: 10px; 
                font-size: 0.9em; color: #4b5563;'>
        <span>👤</span> <span><strong>Name:</strong> {details.get('name', '')}</span>
        <span>📧</span> <span><strong>Email:</strong> {details.get('email', '')}</span>
        <span>📱</span> <span><strong>Phone:</strong> {details.get('phone', '')}</span>
        <span>🚗</span> <span><strong>Vehicle:</strong> {vehicle_name}</span>
    </div>
</div>

{self._show_location_selection(vehicle_id)}
"""
            
        except Exception as e:
            logger.error(f"❌ Details processing error: {e}", exc_info=True)
            return self._error_response("Unable to process details. Please try again.")

    def _show_interactive_calendar(self, vehicle_id: str) -> str:
        """Show interactive calendar with clickable date buttons"""
        try:
            from datetime import datetime, timedelta
            
            today = datetime.now()
            
            # Get booked slots from Neo4j
            with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                result = neo_session.run("""
                    MATCH (b:TestDriveBooking)
                    WHERE b.vehicle_id = $vehicle_id
                      AND b.status IN ['confirmed', 'rescheduled']
                      AND b.date >= date($today)
                    RETURN b.date as date, b.time as time
                """, vehicle_id=vehicle_id, today=today.strftime('%Y-%m-%d'))
                
                booked_slots = {f"{record['date']}_{record['time']}" for record in result}
            
            # Get vehicle details
            with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                vehicle_result = neo_session.run("""
                    MATCH (v:Vehicle {id: $vehicle_id})
                    RETURN v.make + ' ' + v.model + ' ' + v.year as vehicle_name
                """, vehicle_id=vehicle_id).single()
                
                vehicle_name = vehicle_result['vehicle_name'] if vehicle_result else vehicle_id
            
            calendar_html = f"""
<div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>📅 Select Your Date & Time</h3>
    <p style='margin: 0; opacity: 0.95;'>Vehicle: {vehicle_name}</p>
    <p style='margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.9;'>ID: {vehicle_id}</p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>📆 Step 1: Choose a Date</h4>
    <div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
                gap: 10px; margin-bottom: 20px;'>
"""
            
            # Generate next 14 days as clickable buttons
            time_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]
            
            for i in range(14):
                date = today + timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                day_name = date.strftime('%A')
                day_short = date.strftime('%b %d')
                
                # Count available slots
                available_count = sum(
                    1 for slot in time_slots 
                    if f"{date_str}_{slot}" not in booked_slots
                )
                
                if available_count > 0:
                    bg_color = '#d1fae5' if available_count > 4 else '#fef3c7'
                    text_color = '#065f46' if available_count > 4 else '#92400e'
                    
                    calendar_html += f"""
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "📅 SELECT_DATE:{date_str}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: {bg_color}; color: {text_color}; 
                 border: 2px solid {text_color}; padding: 15px; 
                 border-radius: 10px; cursor: pointer; 
                 font-weight: 600; text-align: center; 
                 transition: all 0.2s; font-size: 0.95em;'
           onmouseover='this.style.transform="scale(1.05)"; this.style.boxShadow="0 4px 12px rgba(0,0,0,0.15)";'
           onmouseout='this.style.transform="scale(1)"; this.style.boxShadow="none";'>
            <div style='font-size: 1.1em; margin-bottom: 5px;'>{day_name}</div>
            <div style='font-size: 0.9em; opacity: 0.8;'>{day_short}</div>
            <div style='font-size: 0.85em; margin-top: 5px;'>
                ✅ {available_count} slots
            </div>
        </button>
"""
            
            calendar_html += """
    </div>
</div>

<div style='padding: 15px; background: #f0f9ff; border-radius: 10px; 
            border-left: 4px solid #3b82f6; margin: 15px 0;'>
    <p style='margin: 0; color: #1e40af;'>
        💡 <strong>Tip:</strong> Click on any date to see available time slots
    </p>
</div>
"""
            
            return calendar_html
            
        except Exception as e:
            logger.error(f"❌ Calendar error: {e}", exc_info=True)
            return self._error_response("Unable to load calendar. Please try again.")

    def _show_location_selection(self, vehicle_id: str) -> str:
        """Show location selection (Showroom vs Home Delivery)"""
        return f"""
<div style='padding: 25px; background: white; border-radius: 16px; border: 2px solid #667eea; margin: 20px 0;
            box-shadow: 0 4px 12px rgba(102,126,234,0.2);'>
    <h3 style='color: #667eea; margin: 0 0 15px 0; font-size: 1.3em;'>📍 Choose Pickup Method</h3>
    <p style='margin: 0 0 20px 0; color: #374151; line-height: 1.6;'>
        How would you like to receive the vehicle for your test drive?
    </p>
    
    <div style='display: grid; gap: 15px;'>
        <!-- Showroom Option -->
        <div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; border-radius: 12px; text-align: center;
                    box-shadow: 0 4px 12px rgba(102,126,234,0.3);'>
            <div style='font-size: 2.5em; margin-bottom: 10px;'>🏢</div>
            <h4 style='margin: 0 0 8px 0; font-size: 1.2em;'>Visit Our Showroom</h4>
            <p style='margin: 0 0 12px 0; opacity: 0.9; font-size: 0.95em;'>
                Choose from 4 convenient locations across UAE
            </p>
            <button onclick='
                var chatInput = document.querySelector("#chat_input textarea") || 
                               document.querySelector("textarea[placeholder*=\\"message\\"]");
                if (chatInput) {{
                    chatInput.value = "📍 LOCATION_TYPE:showroom|{vehicle_id}";
                    chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    var sendBtn = document.querySelector("#send_btn") || 
                                 document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                    if (sendBtn) sendBtn.click();
                }}
            ' style='background: rgba(255,255,255,0.9); color: #667eea; border: none; 
                     padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600;
                     transition: all 0.2s;'
               onmouseover='this.style.background="white";'
               onmouseout='this.style.background="rgba(255,255,255,0.9)";'>
                🏢 Choose Showroom
            </button>
        </div>
        
        <!-- Home Delivery Option -->
        <div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    color: white; border-radius: 12px; text-align: center;
                    box-shadow: 0 4px 12px rgba(16,185,129,0.3);'>
            <div style='font-size: 2.5em; margin-bottom: 10px;'>🏠</div>
            <h4 style='margin: 0 0 8px 0; font-size: 1.2em;'>Home Delivery</h4>
            <p style='margin: 0 0 12px 0; opacity: 0.9; font-size: 0.95em;'>
                We'll bring the vehicle to your doorstep
            </p>
            <button onclick='
                var chatInput = document.querySelector("#chat_input textarea") || 
                               document.querySelector("textarea[placeholder*=\\"message\\"]");
                if (chatInput) {{
                    chatInput.value = "📍 LOCATION_TYPE:home|{vehicle_id}";
                    chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    var sendBtn = document.querySelector("#send_btn") || 
                                 document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                    if (sendBtn) sendBtn.click();
                }}
            ' style='background: rgba(255,255,255,0.9); color: #10b981; border: none; 
                     padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600;
                     transition: all 0.2s;'
               onmouseover='this.style.background="white";'
               onmouseout='this.style.background="rgba(255,255,255,0.9)";'>
                🏠 Deliver to Home
            </button>
        </div>
    </div>
    
    <div style='margin-top: 20px; padding: 15px; background: #f0f9ff; border-radius: 8px;'>
        <p style='margin: 0; color: #0369a1; font-size: 0.9em;'>
            💡 <strong>Tip:</strong> Select your preferred option above!
        </p>
    </div>
</div>
"""

    def _handle_branch_selection(self, message: str, session: Dict) -> str:
        """Handle showroom branch selection"""
        try:
            # Parse: "📍 BRANCH_SELECTED:Sheikh Zayed Road Showroom, Dubai|V00001"
            parts = message.replace("📍 BRANCH_SELECTED:", "").strip().split("|")
            if len(parts) != 2:
                return self._error_response("Invalid branch selection")
        
            branch_name = parts[0].strip()
            vehicle_id = parts[1].strip()
        
            # Save to session
            if not session.get('pending_booking'):
                session['pending_booking'] = {}
            session['pending_booking']['pickup_location'] = branch_name
            session['pending_booking']['vehicle_id'] = vehicle_id
        
            user_name = session.get('user_name', 'there')
        
            return f"""
    <div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                border-radius: 12px; color: white; margin: 15px 0;'>
        <h3 style='margin: 0 0 10px 0;'>✅ Branch Confirmed, {user_name}!</h3>
        <p style='margin: 0; opacity: 0.95;'>
            Perfect! Your test drive will be at <strong>{branch_name}</strong>.
        </p>
    </div>

    <div style='padding: 15px; background: white; border-radius: 10px; 
                border: 2px solid #e5e7eb; margin: 15px 0;'>
        <p style='margin: 0; color: #4b5563;'>
            📍 <strong>Pickup Location:</strong> {branch_name}
        </p>
    </div>

    {self._show_interactive_calendar(vehicle_id)}
    """
        
        except Exception as e:
            logger.error(f"❌ Branch selection error: {e}", exc_info=True)
            return self._error_response("Unable to process branch selection.")


    def _handle_address_submission(self, message: str, session: Dict) -> str:
        """Handle home delivery address submission"""
        try:
            # Parse: "📍 ADDRESS_SUBMITTED:Villa 123...|V00001"
            parts = message.replace("📍 ADDRESS_SUBMITTED:", "").strip().split("|")
            if len(parts) != 2:
                return self._error_response("Invalid address submission")
        
            address = parts[0].strip()
            vehicle_id = parts[1].strip()
        
            # Validate
            if len(address) < 20:
                return """
    <div style='padding: 20px; background: #fee2e2; border-left: 4px solid #ef4444; 
                border-radius: 12px; margin: 15px 0;'>
        <p style='margin: 0; color: #991b1b;'>
            ❌ <strong>Incomplete Address</strong>
        </p>
        <p style='margin: 10px 0 0 0; color: #7f1d1d;'>
            Please provide a complete address including street, area, and city.
        </p>
    </div>
    """
        
            # Save to session
            if not session.get('pending_booking'):
                session['pending_booking'] = {}
            session['pending_booking']['pickup_location'] = f"Home Delivery: {address}"
            session['pending_booking']['vehicle_id'] = vehicle_id
        
            user_name = session.get('user_name', 'there')
        
            return f"""
    <div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                border-radius: 12px; color: white; margin: 15px 0;'>
        <h3 style='margin: 0 0 10px 0;'>✅ Address Confirmed, {user_name}!</h3>
        <p style='margin: 0; opacity: 0.95;'>
            Great! We'll deliver the vehicle to your address.
        </p>
    </div>

    <div style='padding: 20px; background: white; border-radius: 12px; 
                border: 2px solid #e5e7eb; margin: 15px 0;'>
        <h4 style='margin: 0 0 10px 0; color: #374151;'>📍 Delivery Address:</h4>
        <div style='padding: 15px; background: #f9fafb; border-radius: 8px;'>
            <p style='margin: 0; color: #4b5563; line-height: 1.8; white-space: pre-line;'>{address}</p>
        </div>
    </div>

    {self._show_interactive_calendar(vehicle_id)}
    """
        
        except Exception as e:
            logger.error(f"❌ Address submission error: {e}", exc_info=True)
            return self._error_response("Unable to process address.")
    

    def _show_time_slots(self, vehicle_id: str, date_str: str) -> str:
        """Show interactive time slot buttons for selected date"""
        try:
            from datetime import datetime
            
            # Get booked slots
            with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                result = neo_session.run("""
                    MATCH (b:TestDriveBooking)
                    WHERE b.vehicle_id = $vehicle_id
                      AND b.date = date($date)
                      AND b.status IN ['confirmed', 'rescheduled']
                    RETURN b.time as time
                """, vehicle_id=vehicle_id, date=date_str)
                
                booked_times = {record['time'] for record in result}
            
            # Get vehicle details
            with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                vehicle_result = neo_session.run("""
                    MATCH (v:Vehicle {id: $vehicle_id})
                    RETURN v.make + ' ' + v.model + ' ' + v.year as vehicle_name
                """, vehicle_id=vehicle_id).single()
                
                vehicle_name = vehicle_result['vehicle_name'] if vehicle_result else vehicle_id
            
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_display = date_obj.strftime('%A, %B %d, %Y')
            
            time_html = f"""
<div style='padding: 20px; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>⏰ Select Your Time</h3>
    <p style='margin: 0; opacity: 0.95;'>Vehicle: {vehicle_name}</p>
    <p style='margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.9;'>Date: {date_display}</p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>⏰ Step 2: Choose a Time</h4>
    
    <div style='margin-bottom: 20px;'>
        <p style='color: #6b7280; font-size: 0.9em; margin: 0 0 10px 0;'>
            <strong>Morning Slots</strong>
        </p>
        <div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px;'>
"""
            
            morning_slots = ["09:00", "10:00", "11:00"]
            afternoon_slots = ["14:00", "15:00", "16:00", "17:00"]
            
            # Morning slots
            for time_slot in morning_slots:
                if time_slot in booked_times:
                    time_html += f"""
            <button disabled style='background: #fee2e2; color: #991b1b; 
                     border: 2px solid #f87171; padding: 15px; 
                     border-radius: 10px; cursor: not-allowed; 
                     font-weight: 600; text-align: center; opacity: 0.5;'>
                <div style='font-size: 1.2em;'>{time_slot}</div>
                <div style='font-size: 0.75em; margin-top: 5px;'>❌ Booked</div>
            </button>
"""
                else:
                    time_html += f"""
            <button onclick='
                var chatInput = document.querySelector("#chat_input textarea") || 
                               document.querySelector("textarea[placeholder*=\\"message\\"]");
                if (chatInput) {{
                    chatInput.value = "⏰ CONFIRM_BOOKING:{vehicle_id}|{date_str}|{time_slot}";
                    chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    var sendBtn = document.querySelector("#send_btn") || 
                                 document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                    if (sendBtn) sendBtn.click();
                }}
            ' style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                     color: white; border: none; padding: 15px; 
                     border-radius: 10px; cursor: pointer; 
                     font-weight: 600; text-align: center; 
                     transition: all 0.2s; box-shadow: 0 2px 8px rgba(16,185,129,0.3);'
               onmouseover='this.style.transform="scale(1.08)"; this.style.boxShadow="0 4px 16px rgba(16,185,129,0.5)";'
               onmouseout='this.style.transform="scale(1)"; this.style.boxShadow="0 2px 8px rgba(16,185,129,0.3)";'>
                <div style='font-size: 1.2em;'>{time_slot}</div>
                <div style='font-size: 0.75em; margin-top: 5px;'>✅ Available</div>
            </button>
"""
            
            time_html += """
        </div>
    </div>
    
    <div>
        <p style='color: #6b7280; font-size: 0.9em; margin: 0 0 10px 0;'>
            <strong>Afternoon Slots</strong>
        </p>
        <div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px;'>
"""
            
            # Afternoon slots
            for time_slot in afternoon_slots:
                if time_slot in booked_times:
                    time_html += f"""
            <button disabled style='background: #fee2e2; color: #991b1b; 
                     border: 2px solid #f87171; padding: 15px; 
                     border-radius: 10px; cursor: not-allowed; 
                     font-weight: 600; text-align: center; opacity: 0.5;'>
                <div style='font-size: 1.2em;'>{time_slot}</div>
                <div style='font-size: 0.75em; margin-top: 5px;'>❌ Booked</div>
            </button>
"""
                else:
                    time_html += f"""
            <button onclick='
                var chatInput = document.querySelector("#chat_input textarea") || 
                               document.querySelector("textarea[placeholder*=\\"message\\"]");
                if (chatInput) {{
                    chatInput.value = "⏰ CONFIRM_BOOKING:{vehicle_id}|{date_str}|{time_slot}";
                    chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    var sendBtn = document.querySelector("#send_btn") || 
                                 document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                    if (sendBtn) sendBtn.click();
                }}
            ' style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                     color: white; border: none; padding: 15px; 
                     border-radius: 10px; cursor: pointer; 
                     font-weight: 600; text-align: center; 
                     transition: all 0.2s; box-shadow: 0 2px 8px rgba(16,185,129,0.3);'
               onmouseover='this.style.transform="scale(1.08)"; this.style.boxShadow="0 4px 16px rgba(16,185,129,0.5)";'
               onmouseout='this.style.transform="scale(1)"; this.style.boxShadow="0 2px 8px rgba(16,185,129,0.3)";'>
                <div style='font-size: 1.2em;'>{time_slot}</div>
                <div style='font-size: 0.75em; margin-top: 5px;'>✅ Available</div>
            </button>
"""
            
            time_html += """
        </div>
    </div>
</div>

<div style='padding: 15px; background: #ecfdf5; border-radius: 10px; 
            border-left: 4px solid #10b981; margin: 15px 0;'>
    <p style='margin: 0; color: #065f46;'>
        💡 <strong>Tip:</strong> Click on any available time to book your test drive instantly!
    </p>
</div>
"""
            
            return time_html
            
        except Exception as e:
            logger.error(f"❌ Time slots error: {e}", exc_info=True)
            return self._error_response("Unable to load time slots. Please try again.")

    # confirm booking Id
    def _confirm_booking(self, vehicle_id: str, date_str: str, time_str: str, session: Dict) -> str:
        """Confirm and create the booking"""
        try:
            user_email = session.get('user_email')
            user_name = session.get('user_name', 'Customer')
            user_phone = session.get('user_phone', '')
            pickup_location = session.get('pending_booking', {}).get('pickup_location', 'Showroom')
            
            if not user_email:
                return self._error_response("Email not found. Please start booking again.")

            logger.info(f"📅 Confirming booking: {vehicle_id} on {date_str} at {time_str}")

            booking_result = self.app.test_drive.book_test_drive(
                customer_name=user_name,
                customer_email=user_email,
                customer_phone=user_phone,
                vehicle_id=vehicle_id,
                preferred_date=date_str,
                preferred_time=time_str,
                notes=f"Booked via chatbot. Location: {pickup_location}",
                pickup_location=pickup_location
            )
            
            # Check if slot is still available
            with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                check_result = neo_session.run("""
                    MATCH (b:TestDriveBooking)
                    WHERE b.vehicle_id = $vehicle_id
                      AND b.date = date($date)
                      AND b.time = $time
                      AND b.status IN ['confirmed', 'rescheduled']
                    RETURN count(b) as count
                """, vehicle_id=vehicle_id, date=date_str, time=time_str).single()
                
                if check_result['count'] > 0:
                    return """
<div style='padding: 20px; background: #fef2f2; border-left: 4px solid #ef4444; 
            border-radius: 12px; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0; color: #991b1b;'>❌ Oops! Slot Just Taken</h3>
    <p style='margin: 0; color: #dc2626;'>
        Someone just booked this slot. Please choose another time - I'll show you what's available.
    </p>
</div>
"""
        # ═══════════════════════════════════════════════════════════
        # ✅ HANDLE DUPLICATE BOOKING RESPONSE
        # ═══════════════════════════════════════════════════════════
            if not booking_result.get('success'):
                if booking_result.get('duplicate'):
                # Show existing booking with options
                    existing_id = booking_result['details']['booking_id']
                    existing_date = booking_result['details']['date']
                    existing_time = booking_result['details']['time']
                    created_ago = booking_result['details']['created_ago']
                
                    logger.warning(f"🚫 Duplicate booking attempt blocked: {existing_id}")
                
                # Get vehicle details for display
                    try:
                        with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                            vehicle_result = neo_session.run("""
                                MATCH (v:Vehicle {id: $vehicle_id})
                                RETURN v.make + ' ' + v.model + ' ' + v.year as vehicle_name,
                                       v.image as image
                            """, vehicle_id=vehicle_id).single()
                        
                            vehicle_name = vehicle_result['vehicle_name'] if vehicle_result else vehicle_id
                            vehicle_image = vehicle_result.get('image', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400') if vehicle_result else 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'
                    except:
                        vehicle_name = vehicle_id
                        vehicle_image = 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'
                
                    from datetime import datetime
                    date_obj = datetime.strptime(existing_date, '%Y-%m-%d')
                    date_display = date_obj.strftime('%A, %B %d, %Y')
                
                    return f"""
    <div style='padding: 25px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                border-radius: 16px; color: white; margin: 20px 0; 
                box-shadow: 0 8px 24px rgba(245,158,11,0.4);'>
        <div style='text-align: center; margin-bottom: 20px;'>
            <div style='font-size: 4em; margin-bottom: 10px;'>⚠️</div>
            <h2 style='margin: 0 0 10px 0; font-size: 2em;'>Already Booked, {user_name}!</h2>
            <p style='margin: 0; opacity: 0.95; font-size: 1.15em;'>
                You already have an active booking for this vehicle (created {created_ago})
            </p>
        </div>
    
        <div style='text-align: center; margin: 20px 0;'>
            <img src='{vehicle_image}' 
                 style='width: 100%; max-width: 300px; height: 180px; object-fit: cover; 
                        border-radius: 12px; border: 3px solid rgba(255,255,255,0.3);'
                 onerror="this.src='https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'">
        </div>
    
        <div style='background: rgba(255,255,255,0.15); padding: 20px; border-radius: 10px;'>
            <div style='margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.2);'>
                <strong style='font-size: 0.85em; opacity: 0.9;'>Existing Booking ID</strong>
                <div style='font-size: 1.4em; font-weight: 700; margin-top: 5px; letter-spacing: 1px;'>
                    {existing_id}
                </div>
            </div>
        
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px;'>
                <div>
                    <strong style='font-size: 0.85em; opacity: 0.9;'>🚗 Vehicle</strong>
                    <div style='margin-top: 5px; line-height: 1.4;'>{vehicle_name}</div>
                    <div style='font-size: 0.85em; opacity: 0.8; margin-top: 2px;'>{vehicle_id}</div>
                </div>
            
                <div>
                    <strong style='font-size: 0.85em; opacity: 0.9;'>📅 Date</strong>
                    <div style='margin-top: 5px;'>{date_display}</div>
                </div>
            
                <div>
                    <strong style='font-size: 0.85em; opacity: 0.9;'>⏰ Time</strong>
                    <div style='margin-top: 5px; font-size: 1.2em; font-weight: 600;'>{existing_time}</div>
                </div>
            
                <div>
                    <strong style='font-size: 0.85em; opacity: 0.9;'>📍 Location</strong>
                    <div style='margin-top: 5px;'>{pickup_location}</div>
                </div>
            </div>
        </div>
    </div>

    <div style='padding: 20px; background: white; border-radius: 12px; 
                border: 2px solid #fbbf24; margin: 15px 0;'>
        <h4 style='color: #f59e0b; margin: 0 0 15px 0;'>💡 What would you like to do?</h4>
    
        <div style='display: grid; gap: 10px;'>
            <button onclick='
                var chatInput = document.querySelector("#chat_input textarea");
                if (chatInput) {{
                    chatInput.value = "🔄 RESCHEDULE:{existing_id}";
                    chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    var sendBtn = document.querySelector("#send_btn");
                    if (sendBtn) sendBtn.click();
                }}
            ' style='background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
                     color: white; border: none; padding: 14px; border-radius: 10px; 
                     cursor: pointer; font-weight: 600;'>
                🔄 Reschedule to Different Date/Time
            </button>
        
            <button onclick='
                var chatInput = document.querySelector("#chat_input textarea");
                if (chatInput) {{
                    chatInput.value = "Show me other vehicles";
                    chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    var sendBtn = document.querySelector("#send_btn");
                    if (sendBtn) sendBtn.click();
                }}
            ' style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                     color: white; border: none; padding: 14px; border-radius: 10px; 
                     cursor: pointer; font-weight: 600;'>
                🚗 Book Different Vehicle
            </button>
        
            <button onclick='
                if (confirm("Cancel booking {existing_id}?")) {{
                    var chatInput = document.querySelector("#chat_input textarea");
                    if (chatInput) {{
                        chatInput.value = "❌ CANCEL:{existing_id}";
                        chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                        var sendBtn = document.querySelector("#send_btn");
                        if (sendBtn) sendBtn.click();
                    }}
                }}
            ' style='background: white; color: #ef4444; border: 2px solid #ef4444; 
                     padding: 14px; border-radius: 10px; cursor: pointer; font-weight: 600;'>
                ❌ Cancel Existing Booking
            </button>
        </div>
    </div>

    <div style='padding: 15px; background: #fef3c7; border-radius: 10px; 
                border-left: 4px solid #f59e0b; margin: 15px 0;'>
        <p style='margin: 0; color: #92400e;'>
            📧 Confirmation email was sent to <strong>{user_email}</strong>
        </p>
    </div>
    """
            
                else:
                    # Other booking error
                    logger.error(f"❌ Booking failed: {booking_result.get('message')}")
                    return f"""
    <div style='padding: 20px; background: #fee2e2; border-left: 4px solid #ef4444; 
                border-radius: 12px; margin: 15px 0;'>
        <h3 style='margin: 0 0 10px 0; color: #991b1b;'>❌ Booking Failed</h3>
        <p style='margin: 0; color: #7f1d1d;'>{booking_result.get('message', 'Please try again.')}</p>
    </div>
    """
        
            # ✅ Get booking details from result
            booking_id = booking_result['booking_id']
            vehicle_name = booking_result['vehicle_name']
            email_sent = booking_result.get('email_sent', False)


            logger.info(f"✅ Booking created: {booking_id} | Email sent: {email_sent}")
            
            # Clear booking context
            session.pop('pending_booking', None)

            from datetime import datetime
            
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_display = date_obj.strftime('%A, %B %d, %Y')

            # Get vehicle image
            try:
                with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                    vehicle_result = neo_session.run("""
                        MATCH (v:Vehicle {id: $vehicle_id})
                        RETURN v.image as image
                    """, vehicle_id=vehicle_id).single()
                
                    vehicle_image = vehicle_result['image'] if vehicle_result else 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'
            except:
                vehicle_image = 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'
        
            # ✅ Email status badge
            if email_sent:
                email_badge = """
    <div style='display: flex; align-items: center; gap: 10px; background: #d1fae5; 
                padding: 12px; border-radius: 8px; border: 1px solid #10b981;'>
        <span style='font-size: 1.5em;'>✉️</span>
        <div>
            <strong style='color: #065f46;'>Confirmation Email Sent!</strong>
            <p style='margin: 5px 0 0 0; color: #047857; font-size: 0.9em;'>
                Check <strong>{user_email}</strong> for your booking details
            </p>
        </div>
    </div>
    """
            else:
                email_badge = """
    <div style='display: flex; align-items: center; gap: 10px; background: #fef3c7; 
                padding: 12px; border-radius: 8px; border: 1px solid #f59e0b;'>
        <span style='font-size: 1.5em;'>⚠️</span>
        <div>
            <strong style='color: #92400e;'>Email Not Sent</strong>
            <p style='margin: 5px 0 0 0; color: #78350f; font-size: 0.9em;'>
                Your booking is confirmed, but we couldn't send the email. 
                Please save your booking ID: <strong>{booking_id}</strong>
            </p>
        </div>
    </div>
    """

            
            return f"""
<div style='padding: 25px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0; 
            box-shadow: 0 8px 24px rgba(16,185,129,0.4);'>
    <div style='text-align: center; margin-bottom: 20px;'>
        <div style='font-size: 4em; margin-bottom: 10px;'>🎉</div>
        <h2 style='margin: 0 0 10px 0; font-size: 2em;'>All Set, {user_name}!</h2>
        <p style='margin: 0; opacity: 0.95; font-size: 1.15em;'>
            Your test drive is confirmed and ready to go!
        </p>
    </div>
    
    <!-- Vehicle Image -->
    <div style='text-align: center; margin: 20px 0;'>
        <img src='{vehicle_image}' 
             style='width: 100%; max-width: 300px; height: 180px; object-fit: cover; 
                    border-radius: 12px; border: 3px solid rgba(255,255,255,0.3);'
             onerror="this.src='https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'">
    </div>
    
    <div style='background: rgba(255,255,255,0.15); padding: 20px; border-radius: 10px;'>
        <div style='margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.2);'>
            <strong style='font-size: 0.85em; opacity: 0.9;'>Booking ID</strong>
            <div style='font-size: 1.4em; font-weight: 700; margin-top: 5px; letter-spacing: 1px;'>
                {booking_id}
            </div>
        </div>
        
        <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px;'>
            <div>
                <strong style='font-size: 0.85em; opacity: 0.9;'>🚗 Vehicle</strong>
                <div style='margin-top: 5px; line-height: 1.4;'>{vehicle_name}</div>
                <div style='font-size: 0.85em; opacity: 0.8; margin-top: 2px;'>{vehicle_id}</div>
            </div>
            
            <div>
                <strong style='font-size: 0.85em; opacity: 0.9;'>📅 Date</strong>
                <div style='margin-top: 5px;'>{date_display}</div>
            </div>
            
            <div>
                <strong style='font-size: 0.85em; opacity: 0.9;'>⏰ Time</strong>
                <div style='margin-top: 5px; font-size: 1.2em; font-weight: 600;'>{time_str}</div>
            </div>
            
            <div>
                <strong style='font-size: 0.85em; opacity: 0.9;'>📍 Location</strong>
                <div style='margin-top: 5px;'>{pickup_location}</div>
            </div>
        </div>
    </div>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>📋 Important Reminders</h4>
    <div style='display: grid; gap: 12px;'>
        <div style='display: flex; gap: 10px; align-items: start;'>
            <span style='font-size: 1.5em;'>✉️</span>
            <div>
                <strong style='color: #1f2937;'>Confirmation Email Sent</strong>
                <p style='margin: 5px 0 0 0; color: #6b7280; font-size: 0.9em;'>
                    Check {user_email} for your booking details
                </p>
            </div>
        </div>
        
        <div style='display: flex; gap: 10px; align-items: start;'>
            <span style='font-size: 1.5em;'>⏰</span>
            <div>
                <strong style='color: #1f2937;'>Arrive Early</strong>
                <p style='margin: 5px 0 0 0; color: #6b7280; font-size: 0.9em;'>
                    Please arrive 10 minutes before your scheduled time
                </p>
            </div>
        </div>
        
        <div style='display: flex; gap: 10px; align-items: start;'>
            <span style='font-size: 1.5em;'>🪪</span>
            <div>
                <strong style='color: #1f2937;'>Bring Your License</strong>
                <p style='margin: 5px 0 0 0; color: #6b7280; font-size: 0.9em;'>
                    A valid driver's license is required for the test drive
                </p>
            </div>
        </div>
        
        <div style='display: flex; gap: 10px; align-items: start;'>
            <span style='font-size: 1.5em;'>📞</span>
            <div>
                <strong style='color: #1f2937;'>Need Help?</strong>
                <p style='margin: 5px 0 0 0; color: #6b7280; font-size: 0.9em;'>
                    We'll call you at {user_phone} if there are any changes
                </p>
            </div>
        </div>
    </div>
</div>

<div style='padding: 20px; background: #f9fafb; border-radius: 12px; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>⚙️ Manage Your Booking</h4>
    <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "🔄 RESCHEDULE:{booking_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                 color: white; border: none; padding: 14px; border-radius: 10px; 
                 cursor: pointer; font-weight: 600; transition: all 0.2s;
                 box-shadow: 0 2px 8px rgba(245,158,11,0.3);'
           onmouseover='this.style.transform="scale(1.03)"; this.style.boxShadow="0 4px 12px rgba(245,158,11,0.5)";'
           onmouseout='this.style.transform="scale(1)"; this.style.boxShadow="0 2px 8px rgba(245,158,11,0.3)";'>
            🔄 Reschedule Booking
        </button>
        
        <button onclick='
            if (confirm("Are you sure you want to cancel this booking?\\n\\nBooking: {booking_id}\\nVehicle: {vehicle_name}\\nDate: {date_display} at {time_str}")) {{
                var chatInput = document.querySelector("#chat_input textarea") || 
                               document.querySelector("textarea[placeholder*=\\"message\\"]");
                if (chatInput) {{
                    chatInput.value = "❌ CANCEL:{booking_id}";
                    chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                    var sendBtn = document.querySelector("#send_btn") || 
                                 document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                    if (sendBtn) sendBtn.click();
                }}
            }}
        ' style='background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                 color: white; border: none; padding: 14px; border-radius: 10px; 
                 cursor: pointer; font-weight: 600; transition: all 0.2s;
                 box-shadow: 0 2px 8px rgba(239,68,68,0.3);'
           onmouseover='this.style.transform="scale(1.03)"; this.style.boxShadow="0 4px 12px rgba(239,68,68,0.5)";'
           onmouseout='this.style.transform="scale(1)"; this.style.boxShadow="0 2px 8px rgba(239,68,68,0.3)";'>
            ❌ Cancel Booking
        </button>
    </div>
</div>

<div style='padding: 15px; background: #ecfdf5; border-radius: 10px; 
            border-left: 4px solid #10b981; margin: 15px 0;'>
    <p style='margin: 0; color: #065f46;'>
        🎉 <strong>We're excited to see you, {user_name}!</strong> Get ready to experience the {vehicle_name} firsthand.
    </p>
</div>
"""
            
        except Exception as e:
            logger.error(f"❌ Booking confirmation error: {e}", exc_info=True)
            return self._error_response("Unable to confirm booking. Please try again.")


    # Reschedule Booking
    
    def _handle_reschedule_request(self, message: str, session: Dict) -> str:
        """Handle reschedule with correct Neo4j property - FIXED"""
        booking_id_match = re.search(r'TD[A-Z0-9]{8,}', message)
        
        if not booking_id_match:
            return """
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #f59e0b; margin: 0 0 15px 0;'>🔄 Reschedule Test Drive</h4>
    <p style='color: #374151; margin: 0;'>
        Please provide your booking ID. You can find it in your confirmation message.
    </p>
</div>
"""
        
        booking_id = booking_id_match.group(0)
        user_email = session.get('user_email', 'unknown')
        
        try:
            with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                # ✅ FIX: Use 'TestDrive' not 'TestDriveBooking', and 'id' property
                result = neo_session.run("""
                    MATCH (b:TestDrive)
                    WHERE b.id = $booking_id
                      AND b.status IN ['confirmed', 'rescheduled']
                    RETURN b.vehicle_id as vehicle_id, 
                           b.customer_name as customer_name,
                           b.date as date, 
                           b.time as time,
                           b.customer_email as stored_email
                """, booking_id=booking_id).single()
                
                if not result:
                    logger.error(f"❌ Booking {booking_id} not found or already cancelled")
                    return f"""
<div style='padding: 20px; background: #fee2e2; border-left: 4px solid #ef4444; 
            border-radius: 12px; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0; color: #991b1b;'>❌ Booking Not Found</h3>
    <p style='margin: 0; color: #7f1d1d;'>
        Booking ID <strong>{booking_id}</strong> does not exist, has been cancelled, or is not accessible.
    </p>
    <p style='margin: 10px 0 0 0; color: #7f1d1d; font-size: 0.9em;'>
        Please check your booking confirmation email for the correct ID.
    </p>
</div>
"""
                
                # ✅ Get vehicle name
                vehicle_name = "Unknown Vehicle"
                try:
                    vehicle_result = neo_session.run("""
                        MATCH (v:Vehicle {id: $vehicle_id})
                        RETURN v.make + ' ' + v.model + ' ' + v.year as vehicle_name
                    """, vehicle_id=result['vehicle_id']).single()
                    
                    if vehicle_result:
                        vehicle_name = vehicle_result['vehicle_name']
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch vehicle name: {e}")
                
                # Store for reschedule flow
                session['reschedule_booking'] = {
                    'booking_id': booking_id,
                    'vehicle_id': result['vehicle_id'],
                    'old_date': str(result['date']),
                    'old_time': result['time']
                }
                
                logger.info(f"✅ Reschedule initiated for {booking_id}")
                
                return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>🔄 Reschedule Your Booking</h3>
    <p style='margin: 0; opacity: 0.95;'>Select a new date and time for your test drive</p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>📋 Current Booking Details</h4>
    <div style='display: grid; gap: 10px;'>
        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'>
            <span style='color: #6b7280;'>Booking ID:</span>
            <strong style='color: #1f2937;'>{booking_id}</strong>
        </div>
        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'>
            <span style='color: #6b7280;'>Customer:</span>
            <strong style='color: #1f2937;'>{result.get("customer_name", "N/A")}</strong>
        </div>
        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'>
            <span style='color: #6b7280;'>Vehicle:</span>
            <strong style='color: #1f2937;'>{vehicle_name}</strong>
        </div>
        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'>
            <span style='color: #6b7280;'>Current Date:</span>
            <strong style='color: #1f2937;'>{result['date']}</strong>
        </div>
        <div style='display: flex; justify-content: space-between; padding: 8px 0;'>
            <span style='color: #6b7280;'>Current Time:</span>
            <strong style='color: #1f2937;'>{result['time']}</strong>
        </div>
    </div>
</div>

{self._show_interactive_calendar(result['vehicle_id'])}
"""
                
        except Exception as e:
            logger.error(f"❌ Reschedule error: {e}", exc_info=True)
            return self._error_response("Unable to process reschedule request. Please try again.")
    # ═══════════════════════════════════════════════════════════════════════
    # ✅ FIXED: COMPLETE RESCHEDULE - Uses correct property 'id'
    # ═══════════════════════════════════════════════════════════════════════
    

    def _complete_reschedule_booking(self, booking_id: str, new_date: str, 
                                    new_time: str, session: Dict) -> str:
        """Complete reschedule - CORRECTED"""
        try:
            # Call test_drive module's update method
            result = self.app.test_drive.update_test_drive(
                booking_id=booking_id,
                new_date=new_date,
                new_time=new_time
            )
            
            # ✅ FIX: Check success first
            if not result.get('success'):
                logger.error(f"❌ Update failed: {result.get('message')}")
                return self._error_response(result.get('message', 'Update failed'))
            
            # ✅ Extract details from successful result
            details = result.get('details', {})
            vehicle_name = details.get('vehicle', 'Unknown Vehicle')
            customer_name = session.get('user_name', 'Customer')
            
            from datetime import datetime as dt
            try:
                date_obj = dt.strptime(new_date, '%Y-%m-%d')
                date_display = date_obj.strftime('%A, %B %d, %Y')
            except:
                date_display = new_date
            
            logger.info(f"✅ Booking {booking_id} rescheduled to {new_date} at {new_time}")
            
            return f"""
<div style='padding: 25px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0; text-align: center;
            box-shadow: 0 4px 12px rgba(16,185,129,0.4);'>
    <div style='font-size: 3em; margin-bottom: 10px;'>✅</div>
    <h2 style='margin: 0 0 10px 0;'>Booking Rescheduled Successfully!</h2>
    <p style='margin: 0; opacity: 0.95; font-size: 1.05em;'>
        {customer_name}, your test drive has been moved to the new date and time.
    </p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #10b981; margin: 15px 0;'>
    <h4 style='color: #10b981; margin: 0 0 15px 0;'>📋 Updated Booking Details</h4>
    <div style='display: grid; gap: 10px;'>
        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'>
            <span style='color: #6b7280;'>Booking ID:</span>
            <strong style='color: #1f2937;'>{booking_id}</strong>
        </div>
        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'>
            <span style='color: #6b7280;'>Vehicle:</span>
            <strong style='color: #1f2937;'>{vehicle_name}</strong>
        </div>
        <div style='display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f3f4f6;'>
            <span style='color: #6b7280;'>New Date:</span>
            <strong style='color: #10b981;'>{date_display}</strong>
        </div>
        <div style='display: flex; justify-content: space-between; padding: 8px 0;'>
            <span style='color: #6b7280;'>New Time:</span>
            <strong style='color: #10b981;'>{new_time}</strong>
        </div>
    </div>
</div>

<div style='padding: 15px; background: #ecfdf5; border-radius: 10px; 
            border-left: 4px solid #10b981; margin: 15px 0;'>
    <p style='margin: 0; color: #065f46;'>
        ✉️ A confirmation email has been sent with your updated booking details.
    </p>
</div>

<div style='padding: 20px; background: #f9fafb; border-radius: 12px; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>💭 Quick Feedback (Optional)</h4>
    <p style='color: #6b7280; font-size: 0.9em; margin: 0 0 10px 0;'>
        Why did you need to reschedule?
    </p>
    
    <div style='display: grid; gap: 8px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {{
                chatInput.value = "💬 FEEDBACK:schedule_conflict";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #374151; border: 2px solid #e5e7eb; 
                 padding: 10px; border-radius: 8px; cursor: pointer; 
                 font-size: 0.9em; text-align: left;'>
            ⏰ Time didn't work for me
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {{
                chatInput.value = "💬 FEEDBACK:changed_mind";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #374151; border: 2px solid #e5e7eb; 
                 padding: 10px; border-radius: 8px; cursor: pointer; 
                 font-size: 0.9em; text-align: left;'>
            🤔 Changed my preference
        </button>
    </div>
</div>
"""
            
        except Exception as e:
            logger.error(f"❌ Complete reschedule error: {e}", exc_info=True)
            return self._error_response("Unable to complete reschedule. Please try again.")


    # ═══════════════════════════════════════════════════════════════════════
    # ✅ HELPER METHOD: Cancellation feedback request
    # ═══════════════════════════════════════════════════════════════════════
    


    # Cancel Booking

    def _handle_cancel_request(self, message: str, session: Dict) -> str:
        """Handle cancellation request - FIXED"""
        booking_id_match = re.search(r'TD[A-Z0-9]{8,}', message)
        
        if not booking_id_match:
            return """
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #ef4444; margin: 0 0 15px 0;'>❌ Cancel Test Drive</h4>
    <p style='color: #374151; margin: 0;'>
        Please provide your booking ID to cancel.
    </p>
</div>
"""
        
        booking_id = booking_id_match.group(0)
        user_email = session.get('user_email', 'unknown')
        
        try:
            with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                # ✅ FIXED: Use correct node label 'TestDrive' and property 'id'
                result = neo_session.run("""
                    MATCH (b:TestDrive)
                    WHERE b.id = $booking_id
                      AND b.customer_email = $email
                      AND b.status IN ['confirmed', 'rescheduled']
                    RETURN b.vehicle_name as vehicle_name, 
                           b.date as date, 
                           b.time as time,
                           b.customer_name as customer_name,
                           b.customer_email as stored_email
                """, booking_id=booking_id, email=user_email).single()
                
                # ✅ Fallback: Try without email restriction
                if not result:
                    logger.warning(f"⚠️ Booking {booking_id} not found with email {user_email}, trying without email check")
                    
                    result = neo_session.run("""
                        MATCH (b:TestDrive)
                        WHERE b.id = $booking_id
                          AND b.status IN ['confirmed', 'rescheduled']
                        RETURN b.vehicle_name as vehicle_name, 
                               b.date as date, 
                               b.time as time,
                               b.customer_name as customer_name,
                               b.customer_email as stored_email
                    """, booking_id=booking_id).single()
                    
                    if result:
                        logger.info(f"✅ Found booking {booking_id} (email: {result.get('stored_email')}) without strict email match")
                    else:
                        logger.error(f"❌ Booking {booking_id} does not exist or already cancelled")
                        return f"""
<div style='padding: 15px; background: #fef2f2; border-left: 4px solid #ef4444; 
            border-radius: 8px; margin: 10px 0;'>
    <strong>❌ Booking Not Found</strong>
    <p style='margin: 5px 0 0 0;'>
        Booking ID {booking_id} does not exist or has already been cancelled.
    </p>
</div>
"""
                
                # ✅ FIXED: Use test_drive module method and correct variable name
                result = self.app.test_drive.cancel_test_drive(
                    booking_id=booking_id,
                    cancellation_reason="Customer request via chat"
                )
                
                if not result.get('success'):
                    return self._error_response(
                        result.get('message', f"Failed to cancel booking {booking_id}. Please try again.")
                    )
                
                logger.info(f"✅ Booking {booking_id} cancelled successfully")
            
            # Store cancellation info to ask for feedback
            session['pending_feedback'] = {
                'booking_id': booking_id,
                'vehicle_name': result.get('vehicle_name', 'Unknown Vehicle'),
                'customer_name': result.get('customer_name', session.get('user_name', 'Customer'))
            }
            
            # Extract details for display
            vehicle_name = result.get('vehicle_name', 'Unknown Vehicle')
            date = result.get('date', 'N/A')
            time = result.get('time', 'N/A')
            
            return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>✅ Booking Cancelled</h3>
    <p style='margin: 0; opacity: 0.95;'>Your test drive has been cancelled successfully.</p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>Cancelled Booking Details</h4>
    <p style='margin: 0 0 8px 0; color: #4b5563;'><strong>Booking ID:</strong> {booking_id}</p>
    <p style='margin: 0 0 8px 0; color: #4b5563;'><strong>Vehicle:</strong> {vehicle_name}</p>
    <p style='margin: 0 0 8px 0; color: #4b5563;'><strong>Date:</strong> {date}</p>
    <p style='margin: 0; color: #4b5563;'><strong>Time:</strong> {time}</p>
</div>

{self._request_cancellation_feedback(session)}
"""
            
        except Exception as e:
            logger.error(f"❌ Cancel error: {e}", exc_info=True)
            return self._error_response("Unable to cancel booking.")

    # cancellation FeedBack

    def _request_cancellation_feedback(self, session: Dict) -> str:
        """Request feedback after cancellation to qualify lead"""
        customer_name = session.get('pending_feedback', {}).get('customer_name', 'there')
        
        return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>💭 We Value Your Feedback</h3>
    <p style='margin: 0; opacity: 0.95;'>
        {customer_name}, we'd love to understand your decision better to serve you better in the future.
    </p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>📝 Why did you cancel?</h4>
    <p style='color: #6b7280; font-size: 0.9em; margin: 0 0 15px 0;'>
        Please select the option that best describes your reason:
    </p>
    
    <div style='display: grid; gap: 10px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 FEEDBACK:changed_mind";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #374151; border: 2px solid #e5e7eb; 
                 padding: 12px; border-radius: 8px; cursor: pointer; 
                 font-weight: 500; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="white";'>
            🤔 Changed my mind / Not interested anymore
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 FEEDBACK:schedule_conflict";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #374151; border: 2px solid #e5e7eb; 
                 padding: 12px; border-radius: 8px; cursor: pointer; 
                 font-weight: 500; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="white";'>
            📅 Schedule conflict / Will reschedule later
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 FEEDBACK:found_better";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #374151; border: 2px solid #e5e7eb; 
                 padding: 12px; border-radius: 8px; cursor: pointer; 
                 font-weight: 500; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="white";'>
            🚗 Found a better option elsewhere
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 FEEDBACK:price_concern";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #374151; border: 2px solid #e5e7eb; 
                 padding: 12px; border-radius: 8px; cursor: pointer; 
                 font-weight: 500; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="white";'>
            💰 Price concerns / Budget issues
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 FEEDBACK:poor_service";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #374151; border: 2px solid #e5e7eb; 
                 padding: 12px; border-radius: 8px; cursor: pointer; 
                 font-weight: 500; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="white";'>
            😞 Unhappy with service / experience
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 FEEDBACK:other";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #374151; border: 2px solid #e5e7eb; 
                 padding: 12px; border-radius: 8px; cursor: pointer; 
                 font-weight: 500; text-align: left; transition: all 0.2s;'
           onmouseover='this.style.borderColor="#667eea"; this.style.background="#f9fafb";'
           onmouseout='this.style.borderColor="#e5e7eb"; this.style.background="white";'>
            💭 Other reason
        </button>
    </div>
</div>

<div style='padding: 15px; background: #f0f9ff; border-radius: 10px; 
            border-left: 4px solid #3b82f6; margin: 15px 0;'>
    <p style='margin: 0; color: #1e40af; font-size: 0.9em;'>
        💙 <strong>Your feedback helps us improve!</strong> We appreciate your honesty.
    </p>
</div>
"""

    def _process_feedback(self, message: str, session: Dict) -> str:
        """Process feedback and qualify lead based on sentiment"""
        try:
            # Extract feedback type
            feedback_match = re.search(r'FEEDBACK:(\w+)', message)
            
            if not feedback_match:
                return self._error_response("Invalid feedback format")
            
            feedback_type = feedback_match.group(1)
            
            # Get pending feedback data
            pending = session.get('pending_feedback', {})
            booking_id = pending.get('booking_id')
            vehicle_name = pending.get('vehicle_name', 'the vehicle')
            customer_name = pending.get('customer_name', 'Customer')
            user_email = session.get('user_email')
            
            # Map feedback to sentiment and lead status
            feedback_mapping = {
                'changed_mind': {
                    'sentiment': 'negative',
                    'lead_status': 'cold',
                    'sentiment_score': 0.2,
                    'emoji': '😔',
                    'response': f"I understand, {customer_name}. Sometimes our needs change, and that's completely okay."
                },
                'schedule_conflict': {
                    'sentiment': 'neutral',
                    'lead_status': 'warm',
                    'sentiment_score': 0.6,
                    'emoji': '📅',
                    'response': f"No worries, {customer_name}! Life gets busy. Feel free to reschedule whenever you're ready."
                },
                'found_better': {
                    'sentiment': 'negative',
                    'lead_status': 'cold',
                    'sentiment_score': 0.3,
                    'emoji': '🤝',
                    'response': f"Thank you for considering us, {customer_name}. We hope you find the perfect vehicle!"
                },
                'price_concern': {
                    'sentiment': 'neutral',
                    'lead_status': 'warm',
                    'sentiment_score': 0.5,
                    'emoji': '💰',
                    'response': f"I understand budget is important, {customer_name}. Let me help you explore financing options or alternative vehicles within your budget."
                },
                'poor_service': {
                    'sentiment': 'negative',
                    'lead_status': 'cold',
                    'sentiment_score': 0.1,
                    'emoji': '😞',
                    'response': f"I'm truly sorry to hear that, {customer_name}. Your experience matters to us. Can you share more details so we can improve?"
                },
                'other': {
                    'sentiment': 'neutral',
                    'lead_status': 'warm',
                    'sentiment_score': 0.5,
                    'emoji': '💭',
                    'response': f"Thank you for your feedback, {customer_name}. If you'd like to share more details, I'm here to listen."
                }
            }
            
            feedback_info = feedback_mapping.get(feedback_type, feedback_mapping['other'])
            
            # Save feedback to Neo4j
            if booking_id and user_email:
                with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                    # Update booking with feedback
                    neo_session.run("""
                        MATCH (b:TestDriveBooking {id: $booking_id})
                        SET b.cancellation_feedback = $feedback_type,
                            b.feedback_sentiment = $sentiment,
                            b.feedback_score = $sentiment_score,
                            b.feedback_timestamp = datetime()
                    """, booking_id=booking_id, feedback_type=feedback_type,
                        sentiment=feedback_info['sentiment'], 
                        sentiment_score=feedback_info['sentiment_score'])
                    
                    # Create or update lead
                    lead_id = f"L{abs(hash(user_email)) % 100000:05d}"
                    
                    neo_session.run("""
                        MERGE (l:Lead {email: $email})
                        ON CREATE SET 
                            l.id = $lead_id,
                            l.name = $name,
                            l.created_at = datetime()
                        SET l.status = $status,
                            l.sentiment = $sentiment,
                            l.last_interaction = datetime(),
                            l.cancellation_reason = $feedback_type,
                            l.notes = $notes
                    """, email=user_email, lead_id=lead_id, name=customer_name,
                        status=feedback_info['lead_status'], 
                        sentiment=feedback_info['sentiment'],
                        feedback_type=feedback_type,
                        notes=f"Cancelled test drive for {vehicle_name}. Reason: {feedback_type}")
            
            # Clear pending feedback
            session.pop('pending_feedback', None)
            
            # Generate response based on feedback type
            response = f"""
<div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>{feedback_info['emoji']}</span>
        <span>Thank You for Your Feedback!</span>
    </h3>
    <p style='margin: 0; opacity: 0.95;'>
        {feedback_info['response']}
    </p>
</div>
"""
            
            # Add sentiment-based follow-up
            if feedback_info['lead_status'] == 'warm':
                response += f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #fbbf24; margin: 15px 0;'>
    <h4 style='color: #f59e0b; margin: 0 0 15px 0;'>🌟 We'd Love to Keep Helping!</h4>
    <p style='color: #374151; margin: 0 0 15px 0;'>
        Based on your feedback, here are some ways I can assist:
    </p>
    
    <div style='display: grid; gap: 10px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "Show me vehicles within my budget";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 color: white; border: none; padding: 12px; 
                 border-radius: 8px; cursor: pointer; font-weight: 600;'
           onmouseover='this.style.opacity="0.9";'
           onmouseout='this.style.opacity="1";'>
            💰 Show Budget-Friendly Options
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "Tell me about financing options";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #667eea; border: 2px solid #667eea; 
                 padding: 12px; border-radius: 8px; cursor: pointer; font-weight: 600;'
           onmouseover='this.style.background="#f9fafb";'
           onmouseout='this.style.background="white";'>
            📊 Explore Financing Options
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "Show me similar vehicles to {vehicle_name}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #667eea; border: 2px solid #667eea; 
                 padding: 12px; border-radius: 8px; cursor: pointer; font-weight: 600;'
           onmouseover='this.style.background="#f9fafb";'
           onmouseout='this.style.background="white";'>
            🔍 See Similar Vehicles
        </button>
    </div>
</div>
"""
            
            elif feedback_info['lead_status'] == 'hot':
                response += f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #10b981; margin: 15px 0;'>
    <h4 style='color: #10b981; margin: 0 0 15px 0;'>🎯 Let's Find the Perfect Time!</h4>
    <p style='color: #374151; margin: 0 0 15px 0;'>
        Since you're still interested, let me help you reschedule at a more convenient time.
    </p>
    
    <button onclick='
        var chatInput = document.querySelector("#chat_input textarea") || 
                       document.querySelector("textarea[placeholder*=\\"message\\"]");
        if (chatInput) {{
            chatInput.value = "Show me available slots for test drive";
            chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
            var sendBtn = document.querySelector("#send_btn") || 
                         document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
            if (sendBtn) sendBtn.click();
        }}
    ' style='width: 100%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
             color: white; border: none; padding: 14px; 
             border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 1em;'
       onmouseover='this.style.transform="scale(1.02)";'
       onmouseout='this.style.transform="scale(1)";'>
        📅 Book New Test Drive
    </button>
</div>
"""
            
            else:  # cold lead
                response += f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #6b7280; margin: 0 0 15px 0;'>💙 We're Here When You're Ready</h4>
    <p style='color: #374151; margin: 0;'>
        Thank you for your time, {customer_name}. If your plans change or you'd like to explore other options, 
        we're always here to help. Feel free to reach out anytime!
    </p>
</div>

<div style='padding: 15px; background: #f0f9ff; border-radius: 10px; margin: 15px 0;'>
    <p style='margin: 0; color: #1e40af; font-size: 0.9em;'>
        💡 <strong>Stay Connected:</strong> I can send you updates on new arrivals, special offers, and more.
    </p>
</div>
"""
            
            # Log lead qualification
            logger.info(f"🎯 Lead Qualified: {user_email} - Status: {feedback_info['lead_status'].upper()} | Sentiment: {feedback_info['sentiment']} | Score: {feedback_info['sentiment_score']}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Feedback processing error: {e}", exc_info=True)
            return self._error_response("Unable to process feedback. Thank you for trying!")

    def _request_post_drive_feedback(self, booking_id: str, session: Dict) -> str:
        """Request feedback after test drive is completed"""
        customer_name = session.get('user_name', 'there')
        
        return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>🎉 How Was Your Test Drive?</h3>
    <p style='margin: 0; opacity: 0.95;'>
        Hi {customer_name}! We hope you enjoyed your test drive experience.
    </p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #374151; margin: 0 0 15px 0;'>⭐ Rate Your Experience</h4>
    <p style='color: #6b7280; font-size: 0.9em; margin: 0 0 15px 0;'>
        Your feedback helps us improve our service
    </p>
    
    <div style='display: grid; gap: 10px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 DRIVE_FEEDBACK:excellent|{booking_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                 color: white; border: none; padding: 15px; 
                 border-radius: 10px; cursor: pointer; 
                 font-weight: 600; text-align: center; transition: all 0.2s;'
           onmouseover='this.style.transform="scale(1.02)";'
           onmouseout='this.style.transform="scale(1)";'>
            😍 Excellent - I loved it!
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 DRIVE_FEEDBACK:good|{booking_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
                 color: white; border: none; padding: 15px; 
                 border-radius: 10px; cursor: pointer; 
                 font-weight: 600; text-align: center; transition: all 0.2s;'
           onmouseover='this.style.transform="scale(1.02)";'
           onmouseout='this.style.transform="scale(1)";'>
            😊 Good - It was nice
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 DRIVE_FEEDBACK:neutral|{booking_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                 color: white; border: none; padding: 15px; 
                 border-radius: 10px; cursor: pointer; 
                 font-weight: 600; text-align: center; transition: all 0.2s;'
           onmouseover='this.style.transform="scale(1.02)";'
           onmouseout='this.style.transform="scale(1)";'>
            😐 Okay - It was average
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "💬 DRIVE_FEEDBACK:poor|{booking_id}";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                 color: white; border: none; padding: 15px; 
                 border-radius: 10px; cursor: pointer; 
                 font-weight: 600; text-align: center; transition: all 0.2s;'
           onmouseover='this.style.transform="scale(1.02)";'
           onmouseout='this.style.transform="scale(1)";'>
            😞 Poor - Not satisfied
        </button>
    </div>
</div>

<div style='padding: 15px; background: #ecfdf5; border-radius: 10px; 
            border-left: 4px solid #10b981; margin: 15px 0;'>
    <p style='margin: 0; color: #065f46; font-size: 0.9em;'>
        💚 <strong>Your honest feedback matters!</strong> It helps us serve you better.
    </p>
</div>
"""

    def _process_drive_feedback(self, message: str, session: Dict) -> str:
        """Process post-drive feedback and qualify as hot lead"""
        try:
            # Extract feedback rating and booking ID
            match = re.search(r'DRIVE_FEEDBACK:(\w+)\|([A-Z0-9]+)', message)
            
            if not match:
                return self._error_response("Invalid feedback format")
            
            rating = match.group(1)
            booking_id = match.group(2)
            
            customer_name = session.get('user_name', 'Customer')
            user_email = session.get('user_email')
            
            # Map rating to lead qualification
            rating_mapping = {
                'excellent': {
                    'sentiment': 'positive',
                    'lead_status': 'hot',
                    'sentiment_score': 0.95,
                    'emoji': '🔥',
                    'response': f"That's wonderful, {customer_name}! I'm thrilled you loved the experience!"
                },
                'good': {
                    'sentiment': 'positive',
                    'lead_status': 'hot',
                    'sentiment_score': 0.75,
                    'emoji': '😊',
                    'response': f"Great to hear, {customer_name}! I'm glad you enjoyed it."
                },
                'neutral': {
                    'sentiment': 'neutral',
                    'lead_status': 'warm',
                    'sentiment_score': 0.5,
                    'emoji': '🤔',
                    'response': f"Thank you for your honest feedback, {customer_name}. How can we make it better for you?"
                },
                'poor': {
                    'sentiment': 'negative',
                    'lead_status': 'warm',
                    'sentiment_score': 0.2,
                    'emoji': '😞',
                    'response': f"I'm sorry to hear that, {customer_name}. Your experience is important to us. Can you tell me what went wrong?"
                }
            }
            
            rating_info = rating_mapping.get(rating, rating_mapping['neutral'])
            
            # Save to Neo4j
            if booking_id and user_email:
                with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                    # Update booking
                    neo_session.run("""
                        MATCH (b:TestDriveBooking {booking_id: $booking_id})
                        SET b.drive_rating = $rating,
                            b.drive_sentiment = $sentiment,
                            b.drive_sentiment_score = $sentiment_score,
                            b.feedback_timestamp = datetime(),
                            b.status = 'completed'
                    """, booking_id=booking_id, rating=rating,
                        sentiment=rating_info['sentiment'],
                        sentiment_score=rating_info['sentiment_score'])
                    
                    # Update lead to HOT if positive feedback
                    lead_id = f"L{abs(hash(user_email)) % 100000:05d}"
                    
                    neo_session.run("""
                        MERGE (l:Lead {email: $email})
                        ON CREATE SET 
                            l.id = $lead_id,
                            l.name = $name,
                            l.created_at = datetime()
                        SET l.status = $status,
                            l.sentiment = $sentiment,
                            l.last_interaction = datetime(),
                            l.test_drive_rating = $rating,
                            l.notes = $notes
                    """, email=user_email, lead_id=lead_id, name=customer_name,
                        status=rating_info['lead_status'],
                        sentiment=rating_info['sentiment'],
                        rating=rating,
                        notes=f"Completed test drive. Rating: {rating}")
            
            # Generate response
            response = f"""
<div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>{rating_info['emoji']}</span>
        <span>Thank You for Your Feedback!</span>
    </h3>
    <p style='margin: 0; opacity: 0.95; font-size: 1.05em;'>
        {rating_info['response']}
    </p>
</div>
"""
            
            # Add next steps based on rating
            if rating_info['lead_status'] == 'hot':
                response += f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #10b981; margin: 15px 0;'>
    <h4 style='color: #10b981; margin: 0 0 15px 0;'>🎯 Ready to Make It Yours?</h4>
    <p style='color: #374151; margin: 0 0 15px 0;'>
        Since you loved the test drive, let's talk about the next steps to make this vehicle yours!
    </p>
    
    <div style='display: grid; gap: 10px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "Tell me about financing options";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                 color: white; border: none; padding: 14px; 
                 border-radius: 10px; cursor: pointer; font-weight: 600;'
           onmouseover='this.style.opacity="0.9";'
           onmouseout='this.style.opacity="1";'>
            💰 Explore Financing Options
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "I want to make an offer";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 color: white; border: none; padding: 14px; 
                 border-radius: 10px; cursor: pointer; font-weight: 600;'
           onmouseover='this.style.opacity="0.9";'
           onmouseout='this.style.opacity="1";'>
            🤝 Make an Offer
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea") || 
                           document.querySelector("textarea[placeholder*=\\"message\\"]");
            if (chatInput) {{
                chatInput.value = "What documents do I need to purchase?";
                chatInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
                var sendBtn = document.querySelector("#send_btn") || 
                             document.querySelectorAll("button")[document.querySelectorAll("button").length - 2];
                if (sendBtn) sendBtn.click();
            }}
        ' style='background: white; color: #667eea; border: 2px solid #667eea; 
                 padding: 14px; border-radius: 10px; cursor: pointer; font-weight: 600;'
           onmouseover='this.style.background="#f9fafb";'
           onmouseout='this.style.background="white";'>
            📄 Purchase Information
        </button>
    </div>
</div>

<div style='padding: 15px; background: #fef3c7; border-radius: 10px; 
            border-left: 4px solid #f59e0b; margin: 15px 0;'>
    <p style='margin: 0; color: #92400e;'>
        🔥 <strong>Hot Lead Alert!</strong> Our team will contact you shortly with a special offer!
    </p>
</div>
"""
            
            # Log lead qualification
            logger.info(f"🔥 HOT LEAD: {user_email} - Positive test drive feedback! Status: {rating_info['lead_status'].upper()} | Score: {rating_info['sentiment_score']}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Drive feedback processing error: {e}", exc_info=True)
            return self._error_response("Thank you for your feedback!")
    
            
    def _get_or_create_session_id(self, user_id: str) -> str:
        """Generate unique session ID"""
        return f"session_{user_id}_{uuid.uuid4().hex[:12]}"
    
    def _save_message_to_neo4j(self, session_id: str, message: str, 
                               role: str, user_email: Optional[str] = None):
        """Save message with sentiment analysis to Neo4j"""
        try:
            message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
            # Clean message for storage
            clean_message = re.sub(r'<[^>]+>', ' ', message)
            clean_message = re.sub(r'\s+', ' ', clean_message).strip()[:1000]
        
            # ═══════════════════════════════════════════════════════════
            # ✅ ANALYZE SENTIMENT FOR USER MESSAGES
            # ═══════════════════════════════════════════════════════════
            sentiment_label = None
            sentiment_score = None
        
            if role == 'user' and len(clean_message) > 5:
                try:
                    sentiment_result = self.sentiment_handler.get_response(clean_message)
                    if sentiment_result:
                        sentiment_label = sentiment_result.get('sentiment', 'neutral')
                        # Map confidence to score (0-1 range)
                        confidence = sentiment_result.get('confidence', 0.5)
                    
                        # Convert sentiment to numeric score
                        if sentiment_label == 'positive':
                            sentiment_score = 0.5 + (confidence * 0.5)  # 0.5-1.0
                        elif sentiment_label == 'negative':
                            sentiment_score = 0.5 - (confidence * 0.3)  # 0.2-0.5
                        elif sentiment_label == 'severe_negative':
                            sentiment_score = 0.2 - (confidence * 0.2)  # 0.0-0.2
                        else:  # neutral or mixed
                            sentiment_score = 0.5
                    
                        logger.debug(f"💭 Sentiment: {sentiment_label} | Score: {sentiment_score:.2f}")
                except Exception as e:
                    logger.warning(f"Sentiment analysis failed: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # ✅ SAVE TO NEO4J WITH SENTIMENT DATA
        # ═══════════════════════════════════════════════════════════
            query = """
                MERGE (c:Conversation {session_id: $session_id})
                ON CREATE SET 
                    c.id = randomUUID(),
                    c.created_at = datetime(),
                    c.user_email = $user_email
            
                CREATE (m:Message {
                    id: $message_id,
                    content: $content,
                    clean_content: $clean_content,
                    role: $role,
                    timestamp: datetime(),
                    sentiment: $sentiment_label,
                    sentiment_score: $sentiment_score
                })
            
                CREATE (c)-[:HAS_MESSAGE]->(m)
            
                // ✅ Update conversation-level sentiment aggregation
                 WITH c, m.id as message_id
                OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(msg:Message)
                WHERE msg.role = 'user' AND msg.sentiment IS NOT NULL
                WITH c, message_id, 
                     count(msg) as total_messages,
                     sum(CASE WHEN msg.sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
                     sum(CASE WHEN msg.sentiment IN ['negative', 'severe_negative'] THEN 1 ELSE 0 END) as negative_count,
                     sum(CASE WHEN msg.sentiment = 'severe_negative' THEN 1 ELSE 0 END) as severe_negative_count,
                     avg(msg.sentiment_score) as avg_sentiment_score
                SET c.total_user_messages = total_messages,
                    c.positive_count = positive_count,
                    c.negative_count = negative_count,
                    c.severe_negative_count = severe_negative_count,
                    c.avg_sentiment_score = avg_sentiment_score,
                    c.last_updated = datetime()
            
                RETURN message_id
            """
        
            self.neo4j.execute_with_retry(
                query,
                {
                    'session_id': session_id,
                    'message_id': message_id,
                    'content': message[:5000],
                    'clean_content': clean_message,
                    'role': role,
                    'user_email': user_email or 'anonymous',
                    'sentiment_label': sentiment_label,
                    'sentiment_score': sentiment_score
                },
                timeout=10.0
            )
        
            logger.debug(f"💾 Saved message to Neo4j: {message_id}")
        
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
    
    def _save_session_to_neo4j(self, session_id: str, session: Dict):
        """Save session metadata to Neo4j"""
        try:
            query = """
                MERGE (c:Conversation {session_id: $session_id})
                SET c.message_count = $message_count,
                    c.last_intent = $last_intent,
                    c.user_email = $user_email,
                    c.viewed_vehicles = $viewed_vehicles,
                    c.preferred_language = $preferred_language,
                    c.last_updated = datetime()
                RETURN c
            """
            
            self.neo4j.execute_with_retry(
                query,
                {
                    'session_id': session_id,
                    'message_count': session['message_count'],
                    'last_intent': session.get('last_intent', 'unknown'),
                    'user_email': session.get('user_email', 'anonymous'),
                    'viewed_vehicles': session.get('viewed_vehicles', []),
                    'preferred_language': session.get('preferred_language', 'en')
                },
                timeout=10.0
            )
            
            logger.debug(f"💾 Saved session to Neo4j: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _load_session_from_neo4j(self, session_id: str) -> Optional[Dict]:
        """Load session from Neo4j"""
        try:
            query = """
                MATCH (c:Conversation {session_id: $session_id})
                OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
                RETURN c, collect(m) as messages
                ORDER BY m.timestamp
            """
            
            results = self.neo4j.execute_with_retry(
                query,
                {'session_id': session_id},
                timeout=10.0
            )
            
            if results and len(results) > 0:
                record = results[0]
                conv = record['c']
                messages = record['messages']
                
                session = {
                    'session_id': session_id,
                    'start_time': conv.get('created_at', datetime.now()),
                    'message_count': conv.get('message_count', 0),
                    'last_intent': conv.get('last_intent'),
                    'conversation_history': [
                        {
                            'timestamp': str(m['timestamp']),
                            'message': m['content'],
                            'role': m['role']
                        }
                        for m in messages if m
                    ],
                    'user_email': conv.get('user_email'),
                    'viewed_vehicles': conv.get('viewed_vehicles', []),
                    'interests': [],
                    'preferred_language': conv.get('preferred_language', 'en'),
                    'email_prompted': False
                }
                
                return session
            
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
        
        return None
    
    def _update_session_email(self, session_id: str, email: str):
        """Update email for existing session"""
        try:
            query = """
                MATCH (c:Conversation {session_id: $session_id})
                SET c.user_email = $email,
                    c.email_captured_at = datetime()
                RETURN c
            """
            
            self.neo4j.execute_with_retry(
                query,
                {'session_id': session_id, 'email': email},
                timeout=10.0
            )
            
            logger.info(f"✅ Updated email for session {session_id}: {email}")
            
        except Exception as e:
            logger.error(f"Failed to update email: {e}")
    
    def _generate_email_prompt(self) -> str:
        """Generate friendly email capture prompt"""
        return """
<div style='padding: 20px; background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); 
            border-radius: 12px; color: white; margin: 20px 0; box-shadow: 0 4px 12px rgba(251,191,36,0.3);'>
    <h3 style='margin: 0 0 12px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>📧</span>
        <span>Stay Connected!</span>
    </h3>
    <p style='margin: 0 0 15px 0; opacity: 0.95; line-height: 1.6;'>
        I'd love to keep you updated on:
    </p>
    <ul style='margin: 0 0 15px 0; opacity: 0.95; line-height: 1.8;'>
        <li>✨ New vehicle arrivals matching your interests</li>
        <li>💰 Exclusive deals and offers</li>
        <li>📅 Your test drive appointments</li>
    </ul>
    <p style='margin: 0; font-size: 0.9em; opacity: 0.9;'>
        💡 <strong>Type:</strong> "My email is your@email.com" to get started!
    </p>
</div>
"""
    
    def get_conversation_history_by_email(self, email: str, limit: int = 10) -> List[Dict]:
        """Get conversation history for a customer by email"""
        try:
            query = """
                MATCH (c:Conversation {user_email: $email})
                OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
                WITH c, m
                ORDER BY m.timestamp DESC
                RETURN c.session_id as session_id, 
                       c.created_at as started_at,
                       c.message_count as message_count,
                       collect({
                           role: m.role,
                           message: m.clean_content,
                           timestamp: m.timestamp
                       }) as messages
                ORDER BY c.created_at DESC
                LIMIT $limit
            """
            
            results = self.neo4j.execute_with_retry(
                query,
                {'email': email, 'limit': limit},
                timeout=15.0
            )
            
            conversations = []
            if results:
                for record in results:
                    conversations.append({
                        'session_id': record['session_id'],
                        'started_at': str(record['started_at']),
                        'message_count': record['message_count'],
                        'messages': record['messages'][:20]  # Limit messages per conversation
                    })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    def _is_financial_query(self, message: str) -> bool:
        """Check if query is about financial reports"""
        financial_keywords = [
            'revenue', 'profit', 'sales', 'earnings', 'financial', 'income',
            'quarterly', 'annual', 'report', 'performance', 'margin',
            'cash flow', 'balance sheet', 'r&d', 'operating', 'net income',
            'market share', 'delivery', 'production', 'units sold'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in financial_keywords)
    
    def _handle_financial_query(self, message: str, session: Dict) -> str:
        """Handle financial report queries with visual results"""
        try:
            if not self.financial_rag:
                return """
                <div style='padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 8px; margin: 10px 0;'>
                    <strong>📊 Financial Reports</strong>
                    <p>Financial analysis module is not available at the moment. Please contact support for detailed financial information.</p>
                </div>
                """
            
            logger.info(f"📊 Processing financial query: {message}")
            
            # Query financial RAG
            result = self.financial_rag.answer_query(
                query=message,
                k_dense=5,
                k_sparse=5,
                alpha=0.6,
                top_k_final=5,
                temperature=0.3
            )
            
            answer = result.get('answer', 'No answer found')
            confidence = result.get('confidence', 0.0)
            method = result.get('method', 'unknown')
            retrieved = result.get('retrieved', [])
            
            # Format response with visual elements
            response = f"""
<div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 15px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15);'>
    <h3 style='margin: 0 0 10px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>📊</span>
        <span>Financial Analysis Results</span>
    </h3>
    <div style='background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin: 10px 0;'>
        <p style='margin: 0; font-size: 0.9em;'><strong>Search Method:</strong> {method.upper()}</p>
        <p style='margin: 5px 0 0 0; font-size: 0.9em;'><strong>Confidence:</strong> {confidence:.1%}</p>
    </div>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='color: #667eea; margin-top: 0;'>📈 Answer:</h4>
    <p style='color: #374151; line-height: 1.6; font-size: 1.05em;'>{answer}</p>
</div>
"""
            
            # Add source references if available
            if retrieved and len(retrieved) > 0:
                response += """
<div style='padding: 15px; background: #f9fafb; border-radius: 10px; 
            border-left: 4px solid #667eea; margin: 15px 0;'>
    <h4 style='color: #374151; margin-top: 0; font-size: 0.95em;'>📚 Sources:</h4>
    <div style='max-height: 200px; overflow-y: auto;'>
"""
                for i, item in enumerate(retrieved[:3], 1):
                    content = item.get('content', '')[:150]
                    section = item.get('section', 'Unknown')
                    score = item.get('score', 0)
                    
                    response += f"""
        <div style='padding: 10px; background: white; border-radius: 6px; 
                    margin: 8px 0; border: 1px solid #e5e7eb;'>
            <p style='margin: 0; font-size: 0.85em; color: #6b7280;'>
                <strong>Source {i}</strong> ({section}) - Relevance: {score:.0%}
            </p>
            <p style='margin: 5px 0 0 0; font-size: 0.9em; color: #374151;'>{content}...</p>
        </div>
"""
                
                response += """
    </div>
</div>
"""
            
            # Add follow-up suggestions
            response += """
<div style='padding: 15px; background: #ecfdf5; border-radius: 10px; margin: 15px 0;'>
    <p style='margin: 0; color: #065f46; font-weight: 600;'>💡 Try asking:</p>
    <ul style='margin: 10px 0 0 0; color: #047857;'>
        <li>Compare revenues of Toyota and Tesla</li>
        <li>What was the operating margin in 2023?</li>
        <li>Show me R&D spending trends</li>
        <li>Which company has the highest net income?</li>
    </ul>
</div>
"""
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Financial query error: {e}")
            return f"""
<div style='padding: 15px; background: #fee2e2; border-left: 4px solid #ef4444; 
            border-radius: 8px; margin: 10px 0;'>
    <strong>⚠️ Error</strong>
    <p>Unable to process financial query: {str(e)}</p>
</div>
"""
    
    def _generate_rich_response(self, agent_result: Dict, session: Dict, 
                                original_message: str) -> str:
        """Generate rich HTML response with images and interactive elements"""
        
        action_type = agent_result['reasoning']['action']
        data = agent_result['action_result'].get('data', {})
        base_response = agent_result.get('response', '')
        
        # 🚗 VEHICLE SEARCH - Show with images
        if action_type in ['vehicle_search', 'budget_search', 'feature_search']:
            vehicles = data.get('vehicles', [])
            
            if vehicles and len(vehicles) > 0:
                return self._format_vehicle_cards(vehicles, session, base_response)
            else:
                return self._format_no_results(original_message)
        
        # ⚖️ COMPARISON - Visual comparison
        elif action_type == 'compare_vehicles':
            vehicles = data.get('vehicles', [])
            if len(vehicles) >= 2:
                return self._format_comparison(vehicles[:2], base_response)
        
        # 😊 SENTIMENT - Empathetic response
        elif action_type == 'analyze_sentiment':
            sentiment_data = data
            return self._format_sentiment_response(sentiment_data, base_response)
        
        # 📅 APPOINTMENT - Show booking options
        elif action_type == 'manage_appointment':
            return self._format_appointment_options(base_response)
        
        # ℹ️ GENERAL INFO - Clean format
        elif action_type == 'provide_info':
            return self._format_info_response(base_response)
        
        # Default: Clean text response
        return self._format_default_response(base_response)
    
    # ════════════════════════════════════════════════════════════════════
    # FORMATTING METHODS - COMPLETE IMPLEMENTATIONS
    # ════════════════════════════════════════════════════════════════════
    
    def _format_vehicle_cards(self, vehicles: List[Dict], session: Dict, 
                             base_response: str) -> str:
        """Format vehicles as rich cards with horizontal scroll carousel - OPTIMIZED"""
        
        # ✅ CRITICAL: Limit to 5 vehicles to prevent 117KB response
        original_count = len(vehicles)
        if len(vehicles) > 5:
            vehicles = vehicles[:5]
        
        # Track viewed vehicles
        session['viewed_vehicles'].extend([v['id'] for v in vehicles])
        session['viewed_vehicles'] = list(set(session['viewed_vehicles']))
        
        total_vehicles = len(vehicles)
        
        # ✅ SIMPLIFIED: Smaller header
        response = f"""
<div style='padding: 12px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 10px; color: white; margin: 10px 0;'>
    <h3 style='margin: 0; font-size: 1.1em;'>🚗 Found {original_count} Vehicle(s)</h3>
    {f"<p style='margin: 3px 0 0 0; font-size: 0.85em; opacity: 0.9;'>Showing top {total_vehicles}</p>" if original_count > 5 else ""}
</div>

<!-- Carousel -->
<div style='position: relative; margin: 15px 0;'>
    <button onclick='document.getElementById("vc").scrollBy({{left:-320,behavior:"smooth"}})' 
            style='position: absolute; left: -12px; top: 45%; z-index: 10; 
                   background: #667eea; color: white; border: none; width: 35px; height: 35px; 
                   border-radius: 50%; cursor: pointer; font-size: 1.1em;'>◀</button>
    
    <div id='vc' style='display: flex; overflow-x: auto; gap: 12px; padding: 15px 5px; scroll-behavior: smooth;'>
"""
        
        # ✅ OPTIMIZED: Generate compact vehicle cards
        for i, v in enumerate(vehicles, 1):
            vid = v['id']
            make = v['make']
            model = v['model']
            year = v['year']
            price = v['price']
            features = v.get('features', [])
            image = v.get('image', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400')
            stock = v.get('stock', 0)
            
            # ✅ SIMPLIFIED: Stock badge
            if stock > 5:
                badge = '<span style="background:#10b981;color:white;padding:3px 8px;border-radius:8px;font-size:0.75em;">✅</span>'
            elif stock > 0:
                badge = f'<span style="background:#f59e0b;color:white;padding:3px 8px;border-radius:8px;font-size:0.75em;">⚠️{stock}</span>'
            else:
                badge = '<span style="background:#ef4444;color:white;padding:3px 8px;border-radius:8px;font-size:0.75em;">❌</span>'
            
            # ✅ COMPACT: Much smaller card HTML
            response += f"""
<div style='min-width:280px;max-width:280px;background:white;border-radius:10px;
            box-shadow:0 2px 8px rgba(0,0,0,0.1);border:1px solid #e5e7eb;'>
    <img src='{image}' style='width:100%;height:140px;object-fit:cover;border-radius:10px 10px 0 0;'
         onerror="this.src='https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'">
    <div style='padding:12px;'>
        <div style='display:flex;justify-content:space-between;align-items:start;margin-bottom:6px;'>
            <h4 style='margin:0;color:#1f2937;font-size:1em;'>{year} {make} {model}</h4>
            {badge}
        </div>
        <p style='font-size:1.4em;color:#667eea;font-weight:700;margin:6px 0;'>AED {price:,}</p>
        <p style='color:#9ca3af;font-size:0.8em;margin:4px 0;'>ID: {vid}</p>
"""
            
            # ✅ COMPACT: Only show 2 features
            if features:
                response += "<div style='display:flex;gap:4px;margin:6px 0;'>"
                for feature in features[:2]:
                    response += f"<span style='background:#dbeafe;color:#1e40af;padding:2px 6px;border-radius:6px;font-size:0.7em;'>{feature}</span>"
                response += "</div>"
            
            # ✅ SIMPLIFIED: Booking button with less JavaScript
            response += f"""
        <button onclick='
var i=document.querySelector("#chat_input textarea");
if(i){{i.value="🚗 BOOK_START:{vid}";i.dispatchEvent(new Event("input",{{bubbles:true}}));
setTimeout(()=>{{var b=document.querySelector("#send_btn");if(b)b.click();}},150);}}
else{{alert("Type: Book test drive for {vid}");}}
' style='width:100%;background:#667eea;color:white;border:none;padding:8px;
         border-radius:6px;cursor:pointer;font-weight:600;font-size:0.85em;margin-top:6px;'>
            📅 Book
        </button>
    </div>
</div>
"""
        
        # Close carousel
        response += f"""
    </div>
    <button onclick='document.getElementById("vc").scrollBy({{left:320,behavior:"smooth"}})' 
            style='position:absolute;right:-12px;top:45%;z-index:10;
                   background:#667eea;color:white;border:none;width:35px;height:35px;
                   border-radius:50%;cursor:pointer;font-size:1.1em;'>▶</button>
</div>

<div style='text-align:center;padding:8px;background:#f3f4f6;border-radius:8px;margin:8px 0;'>
    <p style='margin:0;color:#6b7280;font-size:0.85em;'>
        📊 Showing {total_vehicles} of {original_count} • {"Try specific search for more" if original_count > 5 else "Scroll to browse"}
    </p>
</div>
"""
        
        return response
    
    def _format_no_results(self, query: str) -> str:
        """Format no results message with suggestions"""
        return f"""
<div style='text-align: center; padding: 40px 20px; background: #f9fafb; 
            border-radius: 12px; margin: 15px 0; border: 2px dashed #d1d5db;'>
    <div style='font-size: 3em; margin-bottom: 15px;'>🔍</div>
    <h3 style='color: #4a5568; margin: 10px 0;'>No Vehicles Found</h3>
    <p style='color: #718096;'>No results for "{query}"</p>
    
    <div style='margin-top: 20px;'>
        <p style='font-size: 0.9em; color: #777;'><strong>Try:</strong></p>
        <div style='display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 10px;'>
            <span style='background: white; padding: 8px 16px; border-radius: 20px; border: 1px solid #e5e7eb;'>luxury SUV</span>
            <span style='background: white; padding: 8px 16px; border-radius: 20px; border: 1px solid #e5e7eb;'>cars under 200k</span>
            <span style='background: white; padding: 8px 16px; border-radius: 20px; border: 1px solid #e5e7eb;'>Toyota</span>
        </div>
    </div>
</div>
"""
    
    def _format_comparison(self, vehicles: List[Dict], base_response: str) -> str:
        """Format vehicle comparison"""
        v1, v2 = vehicles[0], vehicles[1]
        
        response = f"""
<div style='padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 10px 0;'>
    <h3 style='margin: 0;'>⚖️ Vehicle Comparison</h3>
</div>

<div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;'>
"""
        
        for vehicle in [v1, v2]:
            response += f"""
    <div style='background: white; border-radius: 12px; overflow: hidden; 
                border: 2px solid #e5e7eb; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'>
        <img src='{vehicle.get("image", "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400")}' 
             style='width: 100%; height: 150px; object-fit: cover;'
             onerror="this.src='https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'">
        <div style='padding: 15px;'>
            <h4 style='margin: 0 0 10px 0; color: #1f2937;'>{vehicle['year']} {vehicle['make']} {vehicle['model']}</h4>
            <p style='font-size: 1.5em; color: #667eea; font-weight: 700; margin: 8px 0;'>AED {vehicle['price']:,}</p>
            <p style='color: #6b7280; font-size: 0.9em;'>Stock: {vehicle.get('stock', 0)} units</p>
        </div>
    </div>
"""
        
        response += """
</div>
"""
        
        return response
    
    def _format_sentiment_response(self, sentiment_data: Dict, base_response: str) -> str:
        """Format sentiment response"""
        sentiment = sentiment_data.get('label', 'NEUTRAL').lower()
        emoji = sentiment_data.get('emoji', '😊')
        score = sentiment_data.get('score', 0.5)
        
        colors = {
            'positive': {'bg': '#ecfdf5', 'border': '#10b981', 'text': '#065f46'},
            'negative': {'bg': '#fef2f2', 'border': '#ef4444', 'text': '#991b1b'},
            'neutral': {'bg': '#f0f9ff', 'border': '#3b82f6', 'text': '#1e3a8a'}
        }
        
        color = colors.get(sentiment, colors['neutral'])
        
        return f"""
<div style='padding: 20px; background: {color['bg']}; border-left: 4px solid {color['border']}; 
            border-radius: 10px; margin: 15px 0;'>
    <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 12px;'>
        <span style='font-size: 2em;'>{emoji}</span>
        <div>
            <p style='margin: 0; color: {color['text']}; font-weight: 600; font-size: 1.1em;'>
                {sentiment.title()} Sentiment
            </p>
            <p style='margin: 4px 0 0 0; color: {color['text']}; font-size: 0.9em;'>
                Confidence: {score:.1%}
            </p>
        </div>
    </div>
    <p style='margin: 0; color: {color['text']}; line-height: 1.6;'>{base_response}</p>
</div>
"""
    
    def _format_appointment_options(self, base_response: str) -> str:
        """Format appointment options"""
        return f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #667eea; margin: 15px 0;'>
    <h3 style='color: #667eea; margin: 0 0 15px 0;'>📅 Book Your Test Drive</h3>
    <p style='color: #4b5563; margin: 0 0 15px 0;'>{base_response}</p>
    
    <div style='background: #f9fafb; padding: 15px; border-radius: 8px;'>
        <p style='margin: 0 0 10px 0; color: #1f2937; font-weight: 600;'>📋 What you'll need:</p>
        <ul style='margin: 0; color: #4b5563; line-height: 1.8;'>
            <li>Vehicle ID (from search results)</li>
            <li>Preferred date and time</li>
            <li>Your contact information</li>
        </ul>
    </div>
</div>
"""
    
    def _format_info_response(self, base_response: str) -> str:
        """Format info response"""
        return f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <p style='color: #374151; line-height: 1.8;'>{base_response.replace(chr(10)+chr(10), '</p><p style="margin: 12px 0;">').replace(chr(10), '<br>')}</p>
</div>
"""
    
    def _format_default_response(self, base_response: str) -> str:
        """Format default response"""
        return f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <p style='color: #374151; line-height: 1.6;'>{base_response}</p>
</div>
"""
    
    def _get_smart_recommendations(self, session: Dict) -> str:
        """Get smart recommendations based on browsing history"""
        viewed = session.get('viewed_vehicles', [])
        
        if not viewed:
            return ""
        
        try:
            # Get similar vehicles from Neo4j
            with self.app.neo4j.driver.session(database=self.app.neo4j.database) as neo_session:
                result = neo_session.run("""
                    MATCH (v:Vehicle)
                    WHERE NOT v.id IN $viewed_ids
                    RETURN v
                    ORDER BY v.price
                    LIMIT 3
                """, viewed_ids=viewed[-3:])
                
                recommendations = []
                for record in result:
                    v = record['v']
                    recommendations.append({
                        'id': v['id'],
                        'make': v['make'],
                        'model': v['model'],
                        'year': v['year'],
                        'price': v['price'],
                        'image': v.get('image', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400')
                    })
            
            if not recommendations:
                return ""
            
            response = """
<div style='padding: 15px; background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%); 
            border-radius: 12px; color: white; margin: 20px 0;'>
    <h3 style='margin: 0 0 10px 0;'>💡 You Might Also Like</h3>
    <p style='margin: 0; opacity: 0.95;'>Based on your browsing history</p>
</div>

<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 15px 0;'>
"""
            
            for rec in recommendations:
                response += f"""
    <div style='background: white; border-radius: 10px; overflow: hidden; 
                border: 2px solid #e5e7eb; cursor: pointer;'>
        <img src='{rec['image']}' 
             style='width: 100%; height: 120px; object-fit: cover;'
             onerror="this.src='https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400'">
        <div style='padding: 12px;'>
            <h4 style='margin: 0 0 6px 0; color: #1f2937; font-size: 0.95em;'>{rec['year']} {rec['make']}</h4>
            <p style='margin: 0; color: #667eea; font-weight: 700;'>AED {rec['price']:,}</p>
        </div>
    </div>
"""
            
            response += """
</div>
"""
            
            return response
            
        except Exception as e:
            logger.error(f"Recommendations error: {e}")
            return ""
    
    def _error_response(self, custom_message: str = None) -> str:
        """Format error response"""
        message = custom_message or "I apologize for the inconvenience."
        return f"""
<div style='padding: 20px; background: #fef2f2; border-left: 4px solid #ef4444; 
            border-radius: 10px; margin: 15px 0;'>
    <div style='display: flex; align-items: center; gap: 12px;'>
        <span style='font-size: 2em;'>⚠️</span>
        <div>
            <p style='margin: 0; color: #991b1b; font-weight: 600;'>Oops! Something went wrong</p>
            <p style='margin: 6px 0 0 0; color: #dc2626;'>{message}</p>
            <p style='margin: 6px 0 0 0; color: #dc2626;'>Please try:</p>
            <ul style='margin: 8px 0 0 0; color: #dc2626;'>
                <li>Rephrasing your question</li>
                <li>Asking about something else</li>
                <li>Contacting support if the issue persists</li>
            </ul>
        </div>
    </div>
</div>
"""

    def _handle_escalation(self, message: str, session: Dict) -> str:
        """Handle escalation requests"""
        try:
            escalation_type = message.replace("🆘 ESCALATE:", "").strip()
            user_name = session.get('user_name', 'Customer')
            user_email = session.get('user_email', 'anonymous')
        
        # Log to Neo4j
            try:
                with self.neo4j.driver.session(database=self.neo4j.database) as neo_session:
                    escalation_id = f"ESC{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                    neo_session.run("""
                        CREATE (e:Escalation {
                            id: $id,
                            type: $type,
                            customer_email: $email,
                            customer_name: $name,
                            status: 'pending',
                            priority: 'high',
                            created_at: datetime(),
                            session_id: $session_id
                        })
                    """, id=escalation_id, type=escalation_type, 
                        email=user_email, name=user_name,
                        session_id=session.get('session_id'))
                
                    logger.info(f"✅ Escalation logged: {escalation_id}")
            except Exception as e:
                logger.error(f"❌ Failed to log escalation: {e}")
        
        # Generate response based on escalation type
            if escalation_type == 'urgent_support':
                return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 12px 0;'>✅ Support Request Received</h3>
    <p style='margin: 0 0 15px 0; opacity: 0.95;'>
        Hi {user_name}, I've escalated your request to our support team.
    </p>
    
    <div style='background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px;'>
        <p style='margin: 0 0 8px 0;'><strong>Ticket ID:</strong> {escalation_id}</p>
        <p style='margin: 0 0 8px 0;'><strong>Priority:</strong> HIGH</p>
        <p style='margin: 0;'><strong>Expected Response:</strong> Within 5 minutes</p>
    </div>
</div>

<div style='padding: 15px; background: #ecfdf5; border-radius: 10px; margin: 15px 0;'>
    <p style='margin: 0; color: #065f46;'>
        📧 A support agent will contact you at <strong>{user_email}</strong> shortly.
    </p>
</div>
"""
        
            elif escalation_type == 'manager_request':
                return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 12px 0;'>👔 Manager Request Submitted</h3>
    <p style='margin: 0; opacity: 0.95;'>
        Your request to speak with a manager has been forwarded to our senior team.
    </p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='margin: 0 0 10px 0; color: #374151;'>Request Details</h4>
    <p style='margin: 0 0 8px 0;'><strong>Reference:</strong> {escalation_id}</p>
    <p style='margin: 0 0 8px 0;'><strong>Callback:</strong> {user_email}</p>
    <p style='margin: 0;'><strong>Status:</strong> Priority Queue</p>
</div>
"""
        
            elif escalation_type == 'file_complaint':
                return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 12px 0;'>📋 Formal Complaint Logged</h3>
    <p style='margin: 0; opacity: 0.95;'>
        Your complaint has been officially recorded and will be reviewed by our quality assurance team.
    </p>
</div>

<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin: 15px 0;'>
    <h4 style='margin: 0 0 10px 0; color: #374151;'>Complaint Reference</h4>
    <p style='margin: 0 0 8px 0;'><strong>Complaint ID:</strong> {escalation_id}</p>
    <p style='margin: 0 0 8px 0;'><strong>Filed By:</strong> {user_name}</p>
    <p style='margin: 0 0 8px 0;'><strong>Contact:</strong> {user_email}</p>
    <p style='margin: 0;'><strong>Review Timeline:</strong> 24-48 hours</p>
</div>

<div style='padding: 15px; background: #fef2f2; border-radius: 10px; margin: 15px 0;'>
    <p style='margin: 0; color: #991b1b; font-size: 0.9em;'>
        ⚠️ You will receive a detailed response via email within 48 hours.
    </p>
</div>
"""
        
            else:
                return "✅ Your request has been escalated to our team."
            
        except Exception as e:
            logger.error(f"❌ Escalation handler error: {e}")
            return "❌ Unable to process escalation. Please contact support directly."


# Testing function
def test_chatbot():
    """Test the enhanced chatbot"""
    print("\n" + "="*60)
    print("🧪 TESTING ENHANCED CUSTOMER CHATBOT")
    print("="*60)
    print("\n✅ Chatbot module loaded successfully!")
    print("\nFeatures:")
    print("  • Vehicle cards with images")
    print("  • Financial report integration")
    print("  • Smart recommendations")
    print("  • Interactive elements")
    print("  • Voice input/output")
    print("  • Neo4j persistence")
    print("  • Session management")
    print("  • Rich HTML formatting")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_chatbot()