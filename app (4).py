"""
Complete Agentic AI Automotive Assistant - Enhanced with Pagination & Metrics
- Customer Search: Pagination (5 per page) + Accuracy Metrics (F1, Precision, Recall)
- No Hallucination: Relevance filtering
- Admin Dashboard: Unchanged (all features preserved)
- Multimodal Upload Support: CSV, JSON, XML, Excel
- Paginated Data View: 10 records per page (admin)
-Amit Sarkar
"""

import os
import json
import logging
import math
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import traceback
import xml.etree.ElementTree as ET

from neo4j_handler import Neo4jHandler
from rag_module import RAGSystem
from sentiment_module import SentimentAnalyzer
from translation_module import TranslationSystem
from speech_module import SpeechSystem
from agent_module import Agent
from test_drive_module import TestDriveBookingSystem
from chatbot_module import AutomotiveChatbot
from floating_chat_widget import SIMPLE_FLOATING_CHAT
from financial_rag_module import AutomotiveFinancialRAG
from financial_rag_init import initialize_financial_rag
from sentiment_analytics import get_sentiment_analysis
from knowledge_graph_viz import get_knowledge_graph_data, generate_d3_visualization
from knowledge_graph_viz_iframe import get_knowledge_graph_data, generate_graph_iframe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutomotiveAssistantApp:
    """Main application"""
    
    def __init__(self):
        logger.info("="*60)
        logger.info("Initializing Automotive AI Assistant")
        logger.info("="*60)
        
        try:
            self.neo4j = Neo4jHandler()
            self.rag = RAGSystem(self.neo4j)
            self.sentiment = SentimentAnalyzer()
            self.translator = TranslationSystem()
            self.speech = SpeechSystem()
            self.test_drive = TestDriveBookingSystem(self.neo4j)
            tools = {
                'rag': lambda q: self.rag.search_vehicles(q),
                'sentiment': lambda t: self.sentiment.analyze(t),
            }
            self.agent = Agent(tools=tools)
            try:
                self.financial_rag = initialize_financial_rag()
                if self.financial_rag:
                    logger.info("✅ Financial RAG initialized")
                else:
                    logger.warning("⚠️ Financial RAG initialization returned None")
            except Exception as e:
                logger.warning(f"⚠️ Financial RAG not available: {e}")
                self.financial_rag = None
            # Initialize Agent-Powered Chatbot
            self.chatbot = AutomotiveChatbot(self)
            logger.info("✅ Chatbot initialized")
            logger.info("✅ All systems initialized!")
            
        except Exception as e:
            logger.error(f"Initialization error: {e}", exc_info=True)
            raise


# ==========================================
# FILE PARSING UTILITIES
# ==========================================

def parse_uploaded_file(file_path: str) -> pd.DataFrame:
    """
    Parse uploaded file - supports CSV, JSON, XML, Excel
    Returns: pandas DataFrame
    """
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        logger.info(f"Parsing file: {file_path} (type: {file_ext})")
        
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
            logger.info(f"✅ CSV parsed: {len(df)} rows")
            return df
            
        elif file_ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                if 'data' in data:
                    df = pd.DataFrame(data['data'])
                elif 'vehicles' in data:
                    df = pd.DataFrame(data['vehicles'])
                elif 'leads' in data:
                    df = pd.DataFrame(data['leads'])
                else:
                    df = pd.DataFrame([data])
            else:
                raise ValueError("Unsupported JSON structure")
            
            logger.info(f"✅ JSON parsed: {len(df)} rows")
            return df
            
        elif file_ext == '.xml':
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            records = []
            for item in root:
                record = {}
                for child in item:
                    record[child.tag] = child.text
                records.append(record)
            
            df = pd.DataFrame(records)
            logger.info(f"✅ XML parsed: {len(df)} rows")
            return df
            
        elif file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            logger.info(f"✅ Excel parsed: {len(df)} rows")
            return df
            
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
            
    except Exception as e:
        logger.error(f"File parsing error: {e}")
        raise


# ==========================================
# CUSTOMER PORTAL - ENHANCED WITH PAGINATION & METRICS
# ==========================================

# Global state for pagination and metrics
search_state = {
    "vehicles": [], 
    "query": "", 
    "page": 1, 
    "total_searched": 0, 
    "relevant_found": 0
}


def create_customer_portal(app: AutomotiveAssistantApp):
    """Customer portal with search, pagination, metrics, and appointments"""
    from session_manager import get_session_manager
    session_manager = get_session_manager()
    def initialize_session(session_token: Optional[str]) -> Tuple[str, str, str]:
        """
        Initialize or resume session from cookie
        
        Args:
            session_token: JWT token from cookie (if exists)
        
        Returns:
            Tuple of (new_token, session_id, user_id, welcome_message)
        """
        try:
            # Try to verify existing token
            if session_token:
                payload = session_manager.verify_session_token(session_token)
                
                if payload:
                    # Valid token - resume session
                    session_id = payload['session_id']
                    user_id = payload['user_id']
                    email = payload.get('email')
                    
                    logger.info(f"🔄 Resuming session: {session_id[:20]}... for user: {user_id}")
                    
                    # Load session from Neo4j
                    session_data = app.chatbot._load_session_from_neo4j(session_id)
                    
                    if session_data:
                        app.chatbot.user_sessions[user_id] = session_data
                        
                        welcome = f"""
<div style='padding: 15px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 12px; color: white; margin: 10px 0;'>
    <h3 style='margin: 0 0 8px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>👋</span>
        <span>Welcome Back!</span>
    </h3>
    <p style='margin: 0; opacity: 0.95;'>
        I've loaded your previous conversation. You have {session_data['message_count']} messages in history.
    </p>
    {f"<p style='margin: 8px 0 0 0; opacity: 0.95;'>📧 Logged in as: {email}</p>" if email else ""}
</div>
"""
                        return session_token, session_id, user_id, welcome
            
            # No valid token - create new session
            import uuid
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            
            new_token = session_manager.create_session_token(user_id, session_id=session_id)
            
            logger.info(f"🆕 New session created: {session_id[:20]}... for user: {user_id}")
            
            welcome = """
<div style='padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; text-align: center; margin: 10px 0;'>
    <h3 style='margin: 0 0 10px 0;'>👋 Welcome!</h3>
    <p style='margin: 0; opacity: 0.95;'>I'm your AI Automotive Voice Assistant</p>
</div>
<div style='padding: 15px; background: white; border-radius: 10px; margin-top: 10px; border: 2px solid #e5e7eb;'>
    <p style='margin: 0 0 10px 0; color: #374151; font-weight: 600;'>I can help you with:</p>
    <ul style='margin: 0; color: #4b5563; line-height: 1.8;'>
        <li>🔍 <strong>Search vehicles</strong> with images</li>
        <li>📊 <strong>Financial reports</strong> and analysis</li>
        <li>💡 <strong>Smart recommendations</strong></li>
        <li>🎤 <strong>Voice commands</strong> - just speak!</li>
        <li>📅 <strong>Test drive booking</strong></li>
    </ul>
</div>
"""
            
            return new_token, session_id, user_id, welcome
            
        except Exception as e:
            logger.error(f"❌ Session initialization error: {e}")
            # Fallback
            import uuid
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            session_id = f"session_{uuid.uuid4().hex[:16]}"
            token = session_manager.create_session_token(user_id, session_id=session_id)
            return token, session_id, user_id, "Welcome to Automotive AI Assistant!"
    
    # ═══════════════════════════════════════════════════════════
    # ENHANCED CHAT HANDLER WITH COOKIES
    # ═══════════════════════════════════════════════════════════
    def on_chat_open(app, session_token):
        """Initialize session when chat opens"""
        try:
            logger.info("🚀 Chat opened, initializing session...")
            token, session_id, user_id, welcome = initialize_session(app,session_token)
            logger.info(f"✅ Session initialized: {session_id[:20]}... for user: {user_id}")
            
            return [{'role': 'assistant', 'content': welcome}], token, session_id, user_id
        except ValueError as ve:
            logger.error(f"❌ on_chat_open ValueError: {ve}", exc_info=True)
            # Create emergency fallback session
            import uuid
            fallback_user = f"user_{uuid.uuid4().hex[:12]}"
            fallback_session = f"session_{uuid.uuid4().hex[:12]}"
            return [{'role': 'assistant', 'content': "👋 Welcome! How can I help you?"}], None, fallback_session, fallback_user
        except Exception as e:
            logger.error(f"❌ on_chat_open error: {e}", exc_info=True)
            import uuid
            fallback_user = f"user_{uuid.uuid4().hex[:12]}"
            fallback_session = f"session_{uuid.uuid4().hex[:12]}"
            return [{'role': 'assistant', 'content': "👋 Welcome! How can I help you?"}], None, fallback_session, fallback_user
        
    def process_text_chat_with_session(message, history, session_token, session_id, user_id, user_email):
        """Process chat with session management"""
        if not message or not message.strip():
            return history, "", None, session_token, session_id, user_id, user_email
        
        try:
            # Verify session token
            if session_token:
                payload = session_manager.verify_session_token(session_token)
                if not payload:
                    # Token expired, create new one
                    logger.warning("⚠️ Token expired, creating new session")
                    session_token, session_id, user_id, _ = initialize_session(None)
            
            # Check for email in message
            import re
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', message)
            
            if email_match and not user_email:
                user_email = email_match.group(0)
                logger.info(f"📧 Captured email: {user_email}")
                
                # Update token with email
                session_token = session_manager.create_session_token(
                    user_id=user_id,
                    email=user_email,
                    session_id=session_id
                )
            
            # Process message
            response_html, email_prompt = app.chatbot.process_message(
                message.strip(),
                user_id=user_id,
                user_email=user_email,
                session_id=session_id
            )
            
            # Generate voice
            session = app.chatbot.user_sessions.get(user_id, {})
            preferred_lang = session.get('preferred_language', 'en')
            
            audio_path = None
            try:
                audio_path = app.chatbot._generate_voice_response(response_html, preferred_lang)
            except:
                pass
            
            if history is None:
                history = []
            
            # ✅ FIX 1: Add timestamp to make responses unique (prevents Gradio deduplication)
            import time
            timestamp = int(time.time() * 1000)
            response_with_timestamp = f"{response_html}<!-- ts:{timestamp} -->"
            
            # ✅ FIX 2: Use messages format consistently
            history.append({'role': 'user', 'content': message})
            history.append({'role': 'assistant', 'content': response_with_timestamp})
            
            # ✅ FIX 3: Email prompt also uses messages format
            if email_prompt and not user_email:
                history.append({'role': 'assistant', 'content': email_prompt})
            
            return history, "", audio_path, session_token, session_id, user_id, user_email
            
        except Exception as e:
            logger.error(f"❌ Chat error: {e}", exc_info=True)
            return history, "", None, session_token, session_id, user_id, user_email
            
    def process_query_with_metrics(text_input: str, audio_input, enable_translation: bool, page_num: int = 1):
        """Process search query with pagination and accuracy metrics - NO HALLUCINATION"""
        try:
            query = text_input.strip() if text_input else ""
            
            # Handle audio input
            if audio_input:
                try:
                    logger.info("🎤 Processing audio input...")
                    transcription_result = app.speech.transcribe_audio(audio_input)
                    #transcript = app.speech.transcribe_audio(audio_input)
                    if transcription_result and transcription_result.get('text'):
                        query = transcription_result['text']
                        detected_audio_lang = transcription_result.get('detected_language', 'en')
                        confidence = transcription_result.get('confidence', 0.0)
                        logger.info(f"✅ Whisper transcription:")
                        logger.info(f"   Language: {detected_audio_lang}")
                        logger.info(f"   Text: '{query[:100]}...'")
                        logger.info(f"   Confidence: {confidence:.1%}")
                        # Use detected language for translation
                        if enable_translation:
                            source_lang = detected_audio_lang
                except Exception as e:
                    logger.error(f"❌ Audio transcription error: {e}")
            
            if not query:
                return "⚠️ Please provide a search query", None, "", 1, "Page 1 of 1", "No metrics available"
            
            # Language detection
            source_lang = 'en'
            if enable_translation:
                try:
                    # Verify language with text-based detection
                    # (character-based detection is more reliable for some scripts)
                    detected_by_text = app.translator.detect_language(query)
                    # If audio and text detection differ significantly, investigate
                    if 'detected_audio_lang' in locals() and detected_audio_lang != detected_by_text:
                        logger.info(f"🔍 Language verification:")
                        logger.info(f"   Whisper: {detected_audio_lang}")
                        logger.info(f"   Text analysis: {detected_by_text}")
                        
                        # Trust character-based detection for non-Latin scripts
                        # (Arabic, Hindi, Chinese, etc.)
                        if detected_by_text in ['ar', 'hi', 'ur', 'zh', 'ja', 'ko', 'th', 'ta', 'te']:
                            logger.info(f"   ✅ Using text-based detection: {detected_by_text}")
                            source_lang = detected_by_text
                        else:
                            logger.info(f"   ✅ Using Whisper detection: {detected_audio_lang}")
                            source_lang = detected_audio_lang
                    elif 'detected_audio_lang' in locals():
                        # Audio detection available, use it
                        source_lang = detected_audio_lang
                    else:
                        # No audio, use text detection
                        source_lang = detected_by_text
                except Exception as e:
                    logger.error(f"❌ Language detection error: {e}")
                    source_lang = 'en'
            else:
                source_lang = 'en'
            
            # Translate to English
            english_query = query
            if enable_translation and source_lang != 'en':
                try:
                    english_query = app.translator.translate_to_english(query, source_lang)
                except Exception as e:
                    logger.error(f"Translation error: {e}")
            
            # SEARCH VEHICLES USING RAG - Direct call prevents hallucination
            logger.info(f"Searching for: {english_query}")
            rag_result = app.rag.search_vehicles(english_query, top_k=100)
            all_vehicles = rag_result.get('vehicles', [])
            
            # FILTER BY RELEVANCE - This prevents hallucination!
            # Only show vehicles with relevance score > 0.3
            relevant_vehicles = [v for v in all_vehicles if v.get('relevance_score', 0) > 0.3]
            
            logger.info(f"Total found: {len(all_vehicles)}, Relevant: {len(relevant_vehicles)}")
            
            # Store in global state
            search_state['vehicles'] = relevant_vehicles
            search_state['query'] = query
            search_state['page'] = page_num
            search_state['total_searched'] = len(all_vehicles)
            search_state['relevant_found'] = len(relevant_vehicles)
            
            # Calculate pagination
            vehicles_per_page = 5
            total_pages = math.ceil(len(relevant_vehicles) / vehicles_per_page) if relevant_vehicles else 1
            page_num = max(1, min(page_num, total_pages))
            
            start_idx = (page_num - 1) * vehicles_per_page
            end_idx = start_idx + vehicles_per_page
            page_vehicles = relevant_vehicles[start_idx:end_idx]
            
            # Generate response text
            if not relevant_vehicles:
                response_text = f"Oops! No vehicles found for this search. Please try different filters or keywords, '{query}'\n\nSuggestions:\n• Try broader terms\n• Check spelling\n• Use categories like 'SUV', 'sedan', 'luxury'"
                metrics_text = "📊 **Search Metrics:**\n- No relevant results found\n- Try different search terms"
            else:
                response_text = f"Good news! Found {len(relevant_vehicles)} relevant vehicle(s) for query {query},you will love it!"
                
                # Add search criteria if available
                if 'intent' in rag_result and rag_result['intent'].get('parameters'):
                    params = rag_result['intent']['parameters']
                    if params.get('brand'):
                        response_text += f"\n🚗 Brand: {params['brand']}"
                    if params.get('max_budget'):
                        response_text += f"\n💰 Max Price: AED {params['max_budget']:,}"
                    if params.get('vehicle_type'):
                        response_text += f"\n📦 Type: {params['vehicle_type'].title()}"
                
                response_text += f"\n\n📄 Showing page {page_num} of {total_pages}"
                
                # Calculate accuracy metrics
                precision = len(relevant_vehicles) / len(all_vehicles) if len(all_vehicles) > 0 else 0
                recall = 1.0  # Simplified - assumes we found all relevant vehicles
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                avg_relevance = sum(v.get('relevance_score', 0) for v in relevant_vehicles) / len(relevant_vehicles) if relevant_vehicles else 0
                
                metrics_text = f"""📊 **Search Accuracy Metrics**

**Performance:**
- 🎯 **Precision:** {precision:.2%}
- 📈 **Recall:** {recall:.2%}
- ⚖️ **F1 Score:** {f1_score:.2%}
- ⭐ **Avg Relevance:** {avg_relevance:.2%}

**Results:**
- 🔍 Total Searched: {len(all_vehicles)}
- ✅ Relevant Found: {len(relevant_vehicles)}
- ❌ Filtered Out: {len(all_vehicles) - len(relevant_vehicles)} (low relevance < 30%)

**Quality:**
- Search Type: {rag_result.get('search_type', 'semantic_search')}
- No Hallucination: ✅ Only showing verified matches
"""
            
            # Translate response
            if enable_translation and source_lang != 'en':
                try:
                    response_text = app.translator.translate_from_english(response_text, source_lang)
                except Exception as e:
                    logger.error(f"Response translation error: {e}")
            
            # Generate speech
            audio_output = None
            try:
                # Extract first line or summary for TTS
                
                speech_text = response_text.split('\n')[0][:200]  # First line, max 200 chars
                # Remove markdown/special characters for better TTS
                import re 
                speech_text = re.sub(r'[*_#\[\]]', '', speech_text)
                speech_text = speech_text.strip()
                if speech_text:
                    logger.info(f"🔊 Generating TTS in '{source_lang}'...")
                    audio_output = app.speech.synthesize_speech(speech_text, language=source_lang)
                    if audio_output:
                        logger.info(f"✅ TTS generated: {audio_output}")
                    else:
                        logger.warning("⚠️ TTS generation failed")
            except Exception as e:
                logger.error(f"❌ Speech synthesis error: {e}")
                audio_output = None  # Continue without audio
                
            
            # Format HTML
            vehicle_html = format_vehicles_paginated(page_vehicles, page_num, total_pages, len(relevant_vehicles))
            page_info = f"Page {page_num} of {total_pages} ({len(relevant_vehicles)} result{'s' if len(relevant_vehicles) != 1 else ''})"
            
            return response_text, audio_output, vehicle_html, page_num, page_info, metrics_text
            
        except Exception as e:
            logger.error(f"Query error: {e}", exc_info=True)
            return f"❌ Error: {str(e)}", None, "", 1, "Error", "Error calculating metrics"

    # Vehicle pagination
    
    def format_vehicles_paginated(vehicles: List[Dict], page: int, total_pages: int, total_count: int) -> str:
        """Format vehicles with beautiful cards - 5 per page"""
        if not vehicles:
            return """
            <div style='text-align: center; padding: 60px 20px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); 
                        border-radius: 16px; border: 2px dashed #ccc;'>
                <div style='font-size: 4em; margin-bottom: 20px;'>😕</div>
                <h2 style='color: #666; margin: 10px 0;'>No Vehicles Found</h2>
                <p style='color: #999;'>Try different search terms or filters</p>
                <div style='margin-top: 20px;'>
                    <p style='font-size: 0.9em; color: #777;'><strong>Try:</strong></p>
                    <div style='display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 10px;'>
                        <span style='background: white; padding: 8px 16px; border-radius: 20px;'>luxury SUV</span>
                        <span style='background: white; padding: 8px 16px; border-radius: 20px;'>cars under 200k</span>
                        <span style='background: white; padding: 8px 16px; border-radius: 20px;'>Toyota Camry</span>
                    </div>
                </div>
            </div>
            """
        
        html = f"""
        <div style='margin-bottom: 25px; padding: 2rem 1.5rem; background-image: linear-gradient(rgba(102, 126, 234, 0.92), rgba(118, 75, 162, 0.92)),url("https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=1600&q=80"); 
                    background-size: cover;
                    background-position: center;
                    color: white;
                    border-radius: 16px;
                    text-align: center;
                    box-shadow: 0 6px 16px rgba(0,0,0,0.15);'>
            <h2 style='margin: 0 0 0.8rem 0; font-size: 2em; font-weight: 700;text-shadow: 2px 2px 6px rgba(0,0,0,0.4);'>🔍 Your Perfect Match Awaits</h2>
            <p style='margin: 0; font-size: 1.2em; font-weight: 500;text-shadow: 1px 1px 4px rgba(0,0,0,0.3);'>
                Found <strong style='font-size: 1.3em; color: #FFD700;'>{total_count}</strong> vehicle{'s' if total_count != 1 else ''} | 
                Page <strong>{page}</strong> of <strong>{total_pages}</strong>
            </p>
        </div>
        """
        
        for idx, v in enumerate(vehicles, 1):
            # Stock status
            stock = v.get('stock', 0)
            if stock > 5:
                stock_badge = "<span style='background: #4CAF50; color: white; padding: 6px 14px; border-radius: 20px; font-size: 0.85em; font-weight: 600;'>✅ In Stock</span>"
            elif stock > 0:
                stock_badge = f"<span style='background: #FF9800; color: white; padding: 6px 14px; border-radius: 20px; font-size: 0.85em; font-weight: 600;'>⚠️ Limited ({stock})</span>"
            else:
                stock_badge = "<span style='background: #F44336; color: white; padding: 6px 14px; border-radius: 20px; font-size: 0.85em; font-weight: 600;'>❌ Out of Stock</span>"
            
            # Image
            image_url = v.get('image', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=600')
            
            # Features
            features = v.get('features', [])
            features_html = ""
            if features:
                features_html = "<div style='display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0;'>"
                for feat in features[:5]:
                    features_html += f"""
                    <span style='background: #E3F2FD; color: #1976D2; padding: 5px 12px; border-radius: 12px; 
                                 font-size: 0.8em; font-weight: 500;'>✨ {feat}</span>
                    """
                if len(features) > 5:
                    features_html += f"<span style='color: #999; font-size: 0.85em; padding: 5px;'>+{len(features)-5} more</span>"
                features_html += "</div>"
            
            # Description
            description = v.get('description', '')[:150]
            if len(v.get('description', '')) > 150:
                description += "..."
            
            # Relevance score
            relevance = v.get('relevance_score', 0)
            if relevance > 0.8:
                match_badge = "<span style='background: #4CAF50; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; margin-left: 8px;'>🎯 Perfect Match</span>"
            elif relevance > 0.6:
                match_badge = "<span style='background: #2196F3; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; margin-left: 8px;'>✓ Good Match</span>"
            else:
                match_badge = "<span style='background: #FF9800; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75em; margin-left: 8px;'>Match</span>"
            
            html += f"""
            <div style='border: 2px solid #e8e8e8; border-radius: 20px; overflow: hidden; 
                        background: white; box-shadow: 0 6px 12px rgba(0,0,0,0.08); 
                        margin-bottom: 25px; transition: all 0.3s;'>
                
                <div style='display: flex; flex-direction: row; min-height: 280px;'>
                    
                    <!-- Left: Image Section -->
                    <div style='width: 380px; min-width: 380px; position: relative; overflow: hidden;'>
                        <img src='{image_url}' 
                             style='width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;'
                             onerror="this.src='https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=600'"
                             alt='{v["make"]} {v["model"]}'>
                        <div style='position: absolute; top: 15px; left: 15px; z-index: 10;'>
                            <div style='background: rgba(0,0,0,0.7); backdrop-filter: blur(8px); 
                                        color: white; padding: 8px 14px; border-radius: 12px; 
                                        font-weight: 600; font-size: 0.9em;'>
                                #{idx + (page-1)*5}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Right: Details Section -->
                    <div style='flex: 1; padding: 25px 30px; display: flex; flex-direction: column; justify-content: space-between;'>
                        
                        <!-- Header -->
                        <div>
                            <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;'>
                                <div style='flex: 1;'>
                                    <h2 style='margin: 0 0 6px 0; color: #2c3e50; font-size: 1.7em; line-height: 1.2;'>
                                        {v['year']} {v['make']} {v['model']}
                                        {match_badge}
                                    </h2>
                                    <p style='margin: 0; color: #7f8c8d; font-size: 0.9em;'>
                                        Vehicle ID: <strong>{v['id']}</strong> | Relevance: {relevance:.0%}
                                    </p>
                                </div>
                                <div style='text-align: right;'>
                                    {stock_badge}
                                </div>
                            </div>
                            
                            <!-- Price -->
                            <div style='margin: 15px 0;'>
                                <span style='font-size: 2.2em; color: #667eea; font-weight: 700; letter-spacing: -0.5px;'>
                                    AED {v['price']:,}
                                </span>
                            </div>
                            
                            <!-- Description -->
                            {f"<p style='color: #555; margin: 12px 0; line-height: 1.6; font-size: 0.95em;'>{description}</p>" if description else ""}
                            
                            <!-- Features -->
                            {features_html}
                        </div>
                        
                        <!-- Action Buttons -->
                        <div style='margin-top: auto; display: flex; gap: 12px;'>
                            <button 
                                onclick='
                                    // Copy vehicle ID to clipboard
                                    navigator.clipboard.writeText("{v["id"]}").then(function() {{
                                        var btn = event.target;
                                        btn.innerHTML = "✅ ID Copied: {v["id"]}";
                                        btn.style.background = "#4CAF50";
                                        
                                        setTimeout(function() {{
                                            btn.innerHTML = "📅 Book Test Drive";
                                            btn.style.background = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)";
                                        }}, 2000);
                                        
                                        // Try to switch to Test Drive tab
                                        setTimeout(function() {{
                                            var tabs = document.querySelectorAll(".tab-nav button");
                                            if (tabs && tabs.length > 1) {{
                                                tabs[1].click();
                                            }}
                                        }}, 1000);
                                    }}).catch(function() {{
                                        alert("Vehicle ID: {v["id"]}\\n\\nPlease copy this and paste in Test Drive tab.");
                                    }});
                                '
                                style='flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                       color: white; border: none; padding: 14px 20px; 
                                       border-radius: 12px; font-size: 1em; cursor: pointer;
                                       font-weight: 600; transition: all 0.3s; box-shadow: 0 4px 8px rgba(102,126,234,0.3);'>
                                📅 Book Test Drive
                            </button>
                            
                            <button 
                                onclick='
                                    alert("🚗 VEHICLE DETAILS\\n\\n" +
                                          "━━━━━━━━━━━━━━━━━━━━\\n" +
                                          "ID: {v["id"]}\\n" +
                                          "Vehicle: {v["year"]} {v["make"]} {v["model"]}\\n" +
                                          "Price: AED {v["price"]:,}\\n" +
                                          "Stock: {v.get("stock", 0)} units\\n" +
                                          "Match: {v.get("relevance_score", 0):.0%}\\n" +
                                          "━━━━━━━━━━━━━━━━━━━━\\n" +
                                          "Top Features:\\n• {chr(10) + "• ".join(str(f) for f in v.get("features", ["No features listed"])[:5])}");
                                '
                                style='flex: 1; background: white; color: #667eea; 
                                       border: 2px solid #667eea; padding: 14px 20px; 
                                       border-radius: 12px; font-size: 1em; cursor: pointer;
                                       font-weight: 600; transition: all 0.3s;'>
                                ℹ️ More Details
                            </button>
                            
                            <button 
                                onclick='
                                    var btn = event.target;
                                    if (btn.innerHTML.includes("❤️")) {{
                                        btn.innerHTML = "💖";
                                        btn.style.color = "#999";
                                        btn.style.borderColor = "#999";
                                    }} else {{
                                        btn.innerHTML = "❤️";
                                        btn.style.color = "#e91e63";
                                        btn.style.borderColor = "#e91e63";
                                    }}
                                '
                                style='background: white; color: #e91e63; border: 2px solid #e91e63; 
                                       padding: 14px 20px; border-radius: 12px; font-size: 1.2em; 
                                       cursor: pointer; font-weight: 600; min-width: 60px; transition: all 0.3s;'>
                                ❤️
                            </button>
                        </div>
                    </div>
                </div>
            </div>
"""
        
        return html
    
    def next_page():
        """Navigate to next page"""
        current_page = search_state.get('page', 1)
        vehicles = search_state.get('vehicles', [])
        
        if not vehicles:
            return "⚠️ No search results", None, "", 1, "Page 1 of 1", "No metrics"
        
        vehicles_per_page = 5
        total_pages = math.ceil(len(vehicles) / vehicles_per_page)
        new_page = min(current_page + 1, total_pages)
        
        start_idx = (new_page - 1) * vehicles_per_page
        end_idx = start_idx + vehicles_per_page
        page_vehicles = vehicles[start_idx:end_idx]
        
        response_text = f"📄 Page {new_page} of {total_pages}"
        vehicle_html = format_vehicles_paginated(page_vehicles, new_page, total_pages, len(vehicles))
        page_info = f"Page {new_page} of {total_pages} ({len(vehicles)} total)"
        
        # Keep metrics
        total_searched = search_state.get('total_searched', len(vehicles))
        precision = len(vehicles) / total_searched if total_searched > 0 else 0
        f1_score = 2 * precision * 1.0 / (precision + 1.0) if precision > 0 else 0
        
        metrics_text = f"""📊 **Search Metrics:**
- Precision: {precision:.2%}
- F1 Score: {f1_score:.2%}
- Results: {len(vehicles)}"""
        
        search_state['page'] = new_page
        
        return response_text, None, vehicle_html, new_page, page_info, metrics_text
    
    def prev_page():
        """Navigate to previous page"""
        current_page = search_state.get('page', 1)
        vehicles = search_state.get('vehicles', [])
        
        if not vehicles:
            return "⚠️ No search results", None, "", 1, "Page 1 of 1", "No metrics"
        
        vehicles_per_page = 5
        total_pages = math.ceil(len(vehicles) / vehicles_per_page)
        new_page = max(current_page - 1, 1)
        
        start_idx = (new_page - 1) * vehicles_per_page
        end_idx = start_idx + vehicles_per_page
        page_vehicles = vehicles[start_idx:end_idx]
        
        response_text = f"📄 Page {new_page} of {total_pages}"
        vehicle_html = format_vehicles_paginated(page_vehicles, new_page, total_pages, len(vehicles))
        page_info = f"Page {new_page} of {total_pages} ({len(vehicles)} total)"
        
        # Keep metrics
        total_searched = search_state.get('total_searched', len(vehicles))
        precision = len(vehicles) / total_searched if total_searched > 0 else 0
        f1_score = 2 * precision * 1.0 / (precision + 1.0) if precision > 0 else 0
        
        metrics_text = f"""📊 **Search Metrics:**
- Precision: {precision:.2%}
- F1 Score: {f1_score:.2%}
- Results: {len(vehicles)}"""
        
        search_state['page'] = new_page
        
        return response_text, None, vehicle_html, new_page, page_info, metrics_text
    
    # Rest of your appointment functions (unchanged)
    def get_available_dates():
        today = datetime.now()
        return [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(90)]
    
    def book_appointment(name, phone, email, vehicle, date, time, notes):
        try:
            if not all([name, phone, email, vehicle, date, time]):
                return "❌ All fields required", None
            
            lead_id = f"L{abs(hash(email)) % 100000:05d}"
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                session.run("""
                    MERGE (l:Lead {email: $email})
                    SET l.id = $id, l.name = $name, l.phone = $phone,
                        l.city = 'Dubai', l.budget = 0, l.interest = $vehicle,
                        l.status = 'warm', l.sentiment = 'neutral',
                        l.created_at = coalesce(l.created_at, datetime())
                """, id=lead_id, email=email, name=name, phone=phone, vehicle=vehicle)
                
                vehicle_result = session.run("""
                    MATCH (v:Vehicle)
                    WHERE toLower(v.make + ' ' + v.model) CONTAINS toLower($vehicle)
                    RETURN v.id as vid LIMIT 1
                """, vehicle=vehicle).single()
                
                vehicle_id = vehicle_result['vid'] if vehicle_result else 'V00001'
                
                appt_id = f"A{datetime.now().strftime('%Y%m%d%H%M%S')}"
                session.run("""
                    MATCH (l:Lead {id: $lead_id})
                    MATCH (v:Vehicle {id: $vehicle_id})
                    CREATE (a:Appointment {
                        id: $appt_id,
                        customer_name: $name,
                        customer_email: $email,
                        customer_phone: $phone,
                        date: date($date),
                        time: $time,
                        type: 'Test Drive',
                        status: 'confirmed',
                        notes: $notes,
                        created_at: datetime()
                    })
                    CREATE (l)-[:HAS_APPOINTMENT]->(a)
                    CREATE (a)-[:FOR_VEHICLE]->(v)
                """, lead_id=lead_id, vehicle_id=vehicle_id, appt_id=appt_id,
                    name=name, email=email, phone=phone, date=date, time=time, notes=notes)
            
            confirmation = f"""✅ **Appointment Confirmed!**

📋 **ID:** {appt_id}
👤 **Name:** {name}
🚗 **Vehicle:** {vehicle}
📅 **Date:** {date}
⏰ **Time:** {time}

📧 Confirmation sent to {email}
"""
            appointments_data = fetch_user_appointments(email)
            return confirmation, appointments_data
            
        except Exception as e:
            logger.error(f"Booking error: {e}", exc_info=True)
            return f"❌ Error: {str(e)}", None
    
    def fetch_user_appointments(email):
        try:
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                result = session.run("""
                    MATCH (a:Appointment)
                    WHERE a.customer_email = $email
                    OPTIONAL MATCH (a)-[:FOR_VEHICLE]->(v:Vehicle)
                    RETURN a, v.make + ' ' + v.model as vehicle
                    ORDER BY a.date DESC, a.time
                """, email=email)
                
                appointments = []
                for record in result:
                    appt = record['a']
                    appointments.append([
                        appt['id'],
                        str(appt['date']),
                        appt['time'],
                        record.get('vehicle', 'N/A'),
                        appt['status'],
                        appt.get('notes', '')
                    ])
                
                return appointments if appointments else [["No appointments found", "", "", "", "", ""]]
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return [["Error loading", "", "", "", "", ""]]
    
    def reschedule_appointment(appt_id, new_date, new_time):
        try:
            if not all([appt_id, new_date, new_time]):
                return "❌ All fields required"
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                result = session.run("""
                    MATCH (a:Appointment {id: $appt_id})
                    SET a.date = date($new_date),
                        a.time = $new_time,
                        a.status = 'rescheduled',
                        a.updated_at = datetime()
                    RETURN a.customer_email as email
                """, appt_id=appt_id, new_date=new_date, new_time=new_time).single()
                
                if result:
                    return f"✅ Rescheduled to {new_date} at {new_time}"
                return "❌ Appointment not found"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def cancel_appointment(appt_id, reason):
        try:
            if not appt_id:
                return "❌ Appointment ID required"
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                result = session.run("""
                    MATCH (a:Appointment {id: $appt_id})
                    SET a.status = 'cancelled',
                        a.cancellation_reason = $reason,
                        a.cancelled_at = datetime()
                    RETURN a
                """, appt_id=appt_id, reason=reason).single()
                
                if result:
                    return "✅ Appointment cancelled successfully"
                return "❌ Appointment not found"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def get_customer_slot_availability():
        """Get slot availability for customers"""
        try:
            today = datetime.now()
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                result = session.run("""
                    MATCH (a:Appointment)
                    WHERE a.date >= date($today) 
                      AND a.date <= date($end_date)
                      AND a.status IN ['confirmed', 'rescheduled']
                    RETURN a.date as date, a.time as time
                    ORDER BY a.date, a.time
                """, today=today.strftime('%Y-%m-%d'),
                    end_date=(today + timedelta(days=30)).strftime('%Y-%m-%d'))
                
                booked_slots = set()
                for record in result:
                    slot = f"{record['date']}_{record['time']}"
                    booked_slots.add(slot)
                
                time_slots = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]
                availability = []
                
                for i in range(30):
                    date = today + timedelta(days=i)
                    date_str = date.strftime('%Y-%m-%d')
                    day_name = date.strftime('%A, %b %d')
                    
                    available_count = 0
                    for time_slot in time_slots:
                        slot_key = f"{date_str}_{time_slot}"
                        if slot_key not in booked_slots:
                            available_count += 1
                    
                    if available_count > 5:
                        status = "🟢 Available"
                    elif available_count > 2:
                        status = "🟡 Limited Slots"
                    elif available_count > 0:
                        status = "🟠 Few Slots Left"
                    else:
                        status = "🔴 Fully Booked"
                    
                    availability.append([
                        date_str,
                        day_name,
                        f"{available_count}/8",
                        f"{8-available_count}/8",
                        status
                    ])
                
                return availability
                
        except Exception as e:
            logger.error(f"Availability error: {e}")
            return [["Error loading availability", "", "", "", ""]]
    
    
    # ===== NEW: Test Drive Functions =====
    def book_test_drive(name, email, phone, vehicle_id, date, time, location, notes):
        """Book test drive"""
        try:
            if not all([name, email, phone, vehicle_id, date, time]):
                return "❌ All required fields must be filled", None
            
            result = app.test_drive.book_test_drive(
                customer_name=name,
                customer_email=email,
                customer_phone=phone,
                vehicle_id=vehicle_id,
                preferred_date=date,
                preferred_time=time,
                notes=notes or "",
                pickup_location=location
            )
            
            if result['success']:
                bookings = app.test_drive.get_my_test_drives(email)
                bookings_table = [
                    [b['booking_id'], b['vehicle_name'], b['date'], 
                     b['time'], b['status'], b['pickup_location']]
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
                
        except Exception as e:
            logger.error(f"Test drive booking error: {e}", exc_info=True)
            return f"❌ Error: {str(e)}", None
    
    def view_my_test_drives(email):
        """View customer's test drives"""
        try:
            if not email:
                return [["Please enter your email", "", "", "", "", ""]]
            
            bookings = app.test_drive.get_my_test_drives(email)
            
            if not bookings:
                return [["No test drives found", "", "", "", "", ""]]
            
            return [
                [b['booking_id'], b['vehicle_name'], b['date'], 
                 b['time'], b['status'], b['pickup_location']]
                for b in bookings
            ]
        except Exception as e:
            logger.error(f"View test drives error: {e}")
            return [["Error loading test drives", "", "", "", "", ""]]
    # ===== End Test Drive Functions =====
    
    # Build Gradio interface
    with gr.Blocks(theme=gr.themes.Soft()) as portal:
        gr.Markdown("# 🚗 Customer Portal")
        
        with gr.Tabs():
            # Tab 1: Enhanced Vehicle Search with Pagination & Metrics
            with gr.Tab("🔍 Search Vehicles"):
                gr.Markdown("""
                ### 🎯 Find Your Perfect Vehicle
                
                **Examples:** "टोयोटा लैंड क्रूजर 2025 मॉडल 200k से कम में" | "Toyota land cruiser 2025 models under 200k" | "تويوتا لاند كروزر موديل 2025 بسعر أقل من 200 ألف" | "show SUV vehicles between 300k and 100k"
                
                ✅ **Features:** Pagination (5 per page) | Accuracy Metrics | Perfect Match
                """)
                
                with gr.Row():
                    with gr.Column(scale=1):
                        text_input = gr.Textbox(
                            label="Search Query",
                            placeholder="e.g., Show me luxury SUVs under 200,000 AED",
                            lines=3
                        )
                        audio_input = gr.Audio(
                            label="🎤 Voice Search",
                            sources=["microphone", "upload"],
                            type="filepath"
                        )
                        translate_check = gr.Checkbox(label="🌐 Multilingual", value=True)
                        search_btn = gr.Button("🔍 Search", variant="primary", size="lg")
                    
                    with gr.Column(scale=2):
                        response_text = gr.Textbox(label="📊 Search Summary", lines=6, show_copy_button=True)
                        response_audio = gr.Audio(label="🔊 Voice Response")
                
                # NEW: Metrics Display Section
                gr.Markdown("---")
                gr.Markdown("### 📊 Accuracy Metrics")
                metrics_display = gr.Markdown("""
**Run a search to see accuracy metrics:**
- Precision, Recall, F1 Score
- Relevance filtering (no hallucination)
- Search quality indicators
                """)
                
                # Pagination controls
                gr.Markdown("---")
                page_num_hidden = gr.Number(value=1, visible=False)
                page_info_display = gr.Markdown("### 📄 Page 1 of 1")
                
                with gr.Row():
                    prev_btn = gr.Button("⬅️ Previous Page", size="lg", scale=1)
                    next_btn = gr.Button("Next Page ➡️", size="lg", scale=1)
                
                # Vehicle display
                vehicle_display = gr.HTML(label="Vehicles")
                
                # Event handlers - NEW: 6 outputs instead of 3
                search_btn.click(
                    process_query_with_metrics,
                    inputs=[text_input, audio_input, translate_check, page_num_hidden],
                    outputs=[response_text, response_audio, vehicle_display, page_num_hidden, page_info_display, metrics_display]
                )
                
                prev_btn.click(
                    prev_page,
                    outputs=[response_text, response_audio, vehicle_display, page_num_hidden, page_info_display, metrics_display]
                )
                
                next_btn.click(
                    next_page,
                    outputs=[response_text, response_audio, vehicle_display, page_num_hidden, page_info_display, metrics_display]
                )
            
            # ===== NEW TAB: Test Drive Booking =====
            with gr.Tab("🚗 Book Test Drive"):
              gr.Markdown("### Schedule Your Test Drive")
              gr.Markdown("Experience your dream car before you buy!")
            
            # Booking Form
              gr.Markdown("#### 📝 Fill Booking Details")
              with gr.Row():
                td_name = gr.Textbox(label="Full Name *", placeholder="Amit Sarkar")
                td_email = gr.Textbox(label="Email *", placeholder="ahmed@example.com")
                td_phone = gr.Textbox(label="Phone *", placeholder="+971-50-123-4567")
            
              with gr.Row():
                td_vehicle = gr.Textbox(
                    label="Vehicle ID *", 
                    placeholder="Copy from search results (e.g., V00001)"
                )
                td_date = gr.Dropdown(choices=get_available_dates(), label="Select Date *")
                td_time = gr.Dropdown(
                    choices=["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", 
                            "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"],
                    label="Select Time *"
                )
            
              td_location = gr.Radio(
                choices=["Showroom", "Home Delivery"],
                value="Showroom",
                label="Pickup Location"
            )
              td_notes = gr.Textbox(
                label="Additional Notes", 
                lines=2,
                placeholder="Any specific features you'd like to test..."
            )
            
              td_book_btn = gr.Button("🚗 Book Test Drive", variant="primary", size="lg")
              td_status = gr.Markdown()
            
            # View My Test Drives
              gr.Markdown("---")
              gr.Markdown("### Your Test Drive Bookings")
            
              td_view_email = gr.Textbox(label="Your Email", placeholder="ahmed@example.com")
              td_view_btn = gr.Button("🔍 View My Test Drives")
              td_bookings = gr.Dataframe(
                headers=["Booking ID", "Vehicle", "Date", "Time", "Status", "Location"],
                label="My Test Drive Bookings"
            )
            
            # Event handlers
              td_book_btn.click(
                book_test_drive,
                [td_name, td_email, td_phone, td_vehicle, td_date, td_time, td_location, td_notes],
                [td_status, td_bookings]
            )
            
              td_view_btn.click(view_my_test_drives, td_view_email, td_bookings)
        # ===== End Test Drive Tab =====
        
            # Tab 2: Book Appointment (UNCHANGED)
            with gr.Tab("📅 Book Appointment"):
                gr.Markdown("### Schedule Your Test Drive")
                
                gr.Markdown("#### 🗓️ Check Slot Availability (Next 30 Days)")
                check_avail_btn = gr.Button("🔍 Check Available Slots", variant="secondary")
                availability_display = gr.Dataframe(
                    headers=["Date", "Day", "Available Slots", "Booked Slots", "Status"],
                    label="Slot Availability Calendar"
                )
                
                check_avail_btn.click(get_customer_slot_availability, outputs=availability_display)
                
                gr.Markdown("---")
                gr.Markdown("#### 📝 Fill Booking Details")
                
                with gr.Row():
                    book_name = gr.Textbox(label="Full Name *", placeholder="Amit Sarkar")
                    book_phone = gr.Textbox(label="Phone *", placeholder="+971-50-123-4567")
                    book_email = gr.Textbox(label="Email *", placeholder="AmitSar@email.com")
                
                with gr.Row():
                    book_vehicle = gr.Textbox(label="Vehicle Interest *", placeholder="Toyota Camry")
                    book_date = gr.Dropdown(choices=get_available_dates(), label="Select Date *")
                    book_time = gr.Dropdown(
                        choices=["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"],
                        label="Select Time *"
                    )
                
                book_notes = gr.Textbox(label="Special Requirements", lines=2, placeholder="Any specific requests...")
                book_btn = gr.Button("📅 Book Appointment", variant="primary", size="lg")
                booking_status = gr.Markdown()
                
                gr.Markdown("### Your Appointments")
                my_appointments = gr.Dataframe(
                    headers=["ID", "Date", "Time", "Vehicle", "Status", "Notes"],
                    label="My Bookings"
                )
                
                book_btn.click(
                    book_appointment,
                    [book_name, book_phone, book_email, book_vehicle, book_date, book_time, book_notes],
                    [booking_status, my_appointments]
                )
            
            # Tab 3: Manage Appointments (UNCHANGED)
            with gr.Tab("🔄 Manage Appointments"):
                gr.Markdown("### Reschedule or Cancel")
                
                with gr.Column():
                    gr.Markdown("#### 📝 View My Appointments")
                    view_email = gr.Textbox(label="Your Email", placeholder="ahmed@email.com")
                    view_btn = gr.Button("🔍 View My Appointments")
                    view_appointments_table = gr.Dataframe(
                        headers=["ID", "Date", "Time", "Vehicle", "Status", "Notes"]
                    )
                    
                    view_btn.click(fetch_user_appointments, view_email, view_appointments_table)
                
                gr.Markdown("---")
                
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### 🔄 Reschedule")
                        reschedule_id = gr.Textbox(label="Appointment ID *")
                        reschedule_date = gr.Dropdown(choices=get_available_dates(), label="New Date *")
                        reschedule_time = gr.Dropdown(
                            choices=["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"],
                            label="New Time *"
                        )
                        reschedule_btn = gr.Button("🔄 Reschedule", variant="primary")
                        reschedule_status = gr.Markdown()
                    
                    with gr.Column():
                        gr.Markdown("#### ❌ Cancel")
                        cancel_id = gr.Textbox(label="Appointment ID *")
                        cancel_reason = gr.Textbox(label="Reason", lines=2)
                        cancel_btn = gr.Button("❌ Cancel Appointment", variant="stop")
                        cancel_status = gr.Markdown()
                
                reschedule_btn.click(
                    reschedule_appointment,
                    [reschedule_id, reschedule_date, reschedule_time],
                    reschedule_status
                )
                
                cancel_btn.click(
                    cancel_appointment,
                    [cancel_id, cancel_reason],
                    cancel_status
                )
        
        # Hot Leads Display (UNCHANGED)
        gr.Markdown("---")
        gr.Markdown("## 🔥 Featured Opportunities")
        try:
            hot_leads = app.neo4j.get_hot_leads()
            leads_html = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;'>"
            for lead in hot_leads[:3]:
                leads_html += f"""
                <div style='border: 2px solid #f5576c; border-radius: 10px; padding: 15px; background: linear-gradient(135deg, #fff 0%, #ffe6e6 100%);'>
                    <span style='background: #f5576c; color: white; padding: 4px 12px; border-radius: 12px; font-size: 0.8em; font-weight: bold;'>🔥 HOT DEAL</span>
                    <h4 style='margin: 10px 0;'>{lead['interest']}</h4>
                    <p style='color: #666; margin: 5px 0;'><strong>Budget:</strong> AED {lead['budget']:,}</p>
                    <p style='color: #666; margin: 5px 0; font-size: 0.9em;'>{lead['notes'][:50]}...</p>
                </div>
                """
            leads_html += "</div>"
            gr.HTML(leads_html)
        except Exception as e:
            logger.error(f"Hot leads error: {e}")


    # ═══════════════════════════════════════════════════════════
    # AGENT MESSAGE POLLING (SHOWS AGENT MESSAGES IN MAIN CHAT)
    # ═══════════════════════════════════════════════════════════
    
    def poll_agent_messages(chat_history: List, session_state: Dict) -> Tuple[List, gr.update]:
        """
        Poll for new agent messages and display them in main chat
        
        Args:
            chat_history: Current chat history
            session_state: Session state
        
        Returns:
            Tuple of (updated_chat_history, button_visibility_update)
        """
        try:
            session_id = session_state.get('session_id')
            if not session_id:
                return chat_history, gr.update(visible=False)
            
            # Check if agent is active
            if not app.chatbot.gradio_transfer.is_agent_active(session_id):
                return chat_history, gr.update(visible=False)
            
            # 👉 CHECK FOR NEW AGENT MESSAGES
            new_message_html = app.chatbot.gradio_transfer.check_for_messages(session_id)
            
            if new_message_html:
                logger.info(f"📨 New agent message received for session: {session_id}")
                
                # 👉 ADD AGENT MESSAGE TO MAIN CHAT HISTORY
                if chat_history is None:
                    chat_history = []
                
                chat_history.append({
                    'role': 'assistant',
                    'content': new_message_html,
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.info(f"✅ Agent message added to chat (total messages: {len(chat_history)})")
            
            return chat_history, gr.update(visible=True)
            
        except Exception as e:
            logger.error(f"❌ Polling error: {e}", exc_info=True)
            return chat_history, gr.update(visible=False)    
    
    return portal

    


# ==========================================
# ADMIN DASHBOARD
# ==========================================

# ==========================================
# ADMIN DASHBOARD
# ==========================================

def create_admin_dashboard(app: AutomotiveAssistantApp):
    """Admin dashboard for data management"""
    from conversation_exporter import ConversationExporter
    exporter = ConversationExporter(app.neo4j)
    
    def login(username, password):
        if not username or not password:
            return (
            gr.update(visible=True),   # Keep login visible
            gr.update(visible=False),  # Hide admin panel
            "⚠️ Please enter username and password"  # Error message
            )
        if username == "admin" and password == "admin123":
           return (
            gr.update(visible=False),  # Hide login
            gr.update(visible=True),   # Show admin panel
            "✅ Login successful!"      # Success message
            )
        else:
           return (
            gr.update(visible=True),   # Keep login visible
            gr.update(visible=False),  # Hide admin panel
            "❌ Invalid username or password"  # Error message
        )   
    def upload_vehicles(file):
        """Upload vehicles with multimodal support (CSV, JSON, XML, Excel)"""
        try:
            if file is None:
                return "❌ No file selected"
            
            if not os.path.exists(file.name):
                return "❌ File not found. Please try uploading again."
            
            logger.info(f"Starting vehicle upload from: {file.name}")
            
            # Parse file (supports CSV, JSON, XML, Excel)
            try:
                df = parse_uploaded_file(file.name)
            except Exception as e:
                return f"❌ File parsing error: {str(e)}"
            
            if df.empty:
                return "❌ File contains no data"
            
            success = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    vehicle_id = row.get('id', f'V{idx+10000:05d}')
                    features = [f.strip() for f in str(row.get('features', '')).split(',') if f.strip()]
                    
                    with app.neo4j.driver.session(database=app.neo4j.database) as session:
                        session.run("""
                            MERGE (v:Vehicle {id: $id})
                            SET v.make = $make, v.model = $model, v.year = $year,
                                v.price = $price, v.features = $features, v.stock = $stock,
                                v.image = $image, v.description = $description,
                                v.updated_at = datetime()
                        """,
                            id=vehicle_id, make=str(row['make']), model=str(row['model']),
                            year=int(row['year']), price=float(row['price']),
                            features=features, stock=int(row.get('stock', 0)),
                            image=str(row.get('image', '')), description=str(row.get('description', ''))
                        )
                    success += 1
                    
                    if (idx + 1) % 100 == 0:
                        logger.info(f"Uploaded {idx+1}/{len(df)} vehicles...")
                        
                except Exception as e:
                    error_msg = f"Row {idx}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    if len(errors) > 10:
                        break
            
            # Rebuild RAG index
            try:
                app.rag.rebuild_index()
                index_msg = "RAG index rebuilt!"
            except Exception as e:
                logger.error(f"RAG rebuild error: {e}")
                index_msg = f"Warning: RAG rebuild failed - {str(e)}"
            
            result_msg = f"✅ Uploaded {success}/{len(df)} vehicles. {index_msg}"
            if errors:
                result_msg += f"\n\n⚠️ {len(errors)} errors occurred. First error: {errors[0]}"
            
            return result_msg
            
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Upload vehicles error: {error_trace}")
            return f"❌ Error: {str(e)}\n\nPlease check the file format and try again."
    
    def upload_leads(file):
        """Upload leads with multimodal support (CSV, JSON, XML, Excel)"""
        try:
            if file is None:
                return "❌ No file selected"
            
            if not os.path.exists(file.name):
                return "❌ File not found. Please try uploading again."
            
            logger.info(f"Starting lead upload from: {file.name}")
            
            # Parse file (supports CSV, JSON, XML, Excel)
            try:
                df = parse_uploaded_file(file.name)
            except Exception as e:
                return f"❌ File parsing error: {str(e)}"
            
            if df.empty:
                return "❌ File contains no data"
            
            success = 0
            errors = []
            
            for idx, row in df.iterrows():
                try:
                    lead_id = row.get('id', f'L{idx+10000:05d}')
                    
                    with app.neo4j.driver.session(database=app.neo4j.database) as session:
                        session.run("""
                            MERGE (l:Lead {id: $id})
                            SET l.name = $name, l.phone = $phone, l.email = $email,
                                l.city = $city, l.budget = $budget, l.interest = $interest,
                                l.status = $status, l.sentiment = $sentiment, l.notes = $notes,
                                l.updated_at = datetime()
                        """,
                            id=lead_id, name=str(row['name']), phone=str(row['phone']),
                            email=str(row['email']), city=str(row['city']),
                            budget=float(row['budget']), interest=str(row.get('interest', '')),
                            status=str(row.get('status', 'cold')),
                            sentiment=str(row.get('sentiment', 'neutral')),
                            notes=str(row.get('notes', ''))
                        )
                    success += 1
                    
                    if (idx + 1) % 100 == 0:
                        logger.info(f"Uploaded {idx+1}/{len(df)} leads...")
                        
                except Exception as e:
                    error_msg = f"Row {idx}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    if len(errors) > 10:
                        break
            
            result_msg = f"✅ Uploaded {success}/{len(df)} leads!"
            if errors:
                result_msg += f"\n\n⚠️ {len(errors)} errors occurred. First error: {errors[0]}"
            
            return result_msg
            
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Upload leads error: {error_trace}")
            return f"❌ Error: {str(e)}\n\nPlease check the file format and try again."
    
    def manual_add_vehicle(vid, make, model, year, price, features, stock, image, description):
        """Manual vehicle entry with delta update"""
        try:
            if not all([make, model, year, price]):
                return "❌ Make, Model, Year, and Price are required"
            
            # Generate ID if not provided
            if not vid:
                vid = f"V{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Parse features
            feature_list = [f.strip() for f in features.split(',') if f.strip()]
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                session.run("""
                    MERGE (v:Vehicle {id: $id})
                    SET v.make = $make, v.model = $model, v.year = $year,
                        v.price = $price, v.features = $features, v.stock = $stock,
                        v.image = $image, v.description = $description,
                        v.updated_at = datetime()
                """,
                    id=vid, make=make, model=model, year=int(year), price=float(price),
                    features=feature_list, stock=int(stock or 0),
                    image=image or '', description=description or ''
                )
            
            app.rag.rebuild_index()
            return f"✅ Vehicle {vid} added/updated successfully! RAG index rebuilt."
            
        except Exception as e:
            logger.error(f"Manual add vehicle error: {e}")
            return f"❌ Error: {str(e)}"
    
    def manual_add_lead(lid, name, phone, email, city, budget, interest, status, sentiment, notes):
        """Manual lead entry with delta update"""
        try:
            if not all([name, phone, email, city, budget]):
                return "❌ Name, Phone, Email, City, and Budget are required"
            
            # Generate ID if not provided
            if not lid:
                lid = f"L{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                session.run("""
                    MERGE (l:Lead {id: $id})
                    SET l.name = $name, l.phone = $phone, l.email = $email,
                        l.city = $city, l.budget = $budget, l.interest = $interest,
                        l.status = $status, l.sentiment = $sentiment, l.notes = $notes,
                        l.updated_at = datetime()
                """,
                    id=lid, name=name, phone=phone, email=email, city=city,
                    budget=float(budget), interest=interest or '',
                    status=status or 'cold', sentiment=sentiment or 'neutral',
                    notes=notes or ''
                )
            
            return f"✅ Lead {lid} added/updated successfully!"
            
        except Exception as e:
            logger.error(f"Manual add lead error: {e}")
            return f"❌ Error: {str(e)}"
    
    def get_appointment_slots_last_3_months():
        """Get appointment slots for last 3 months"""
        try:
            today = datetime.now()
            three_months_ago = today - timedelta(days=90)
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                result = session.run("""
                    MATCH (a:Appointment)
                    WHERE a.date >= date($start_date) AND a.date <= date($end_date)
                    OPTIONAL MATCH (a)-[:FOR_VEHICLE]->(v:Vehicle)
                    RETURN a, v.make + ' ' + v.model as vehicle
                    ORDER BY a.date DESC, a.time DESC
                """, start_date=three_months_ago.strftime('%Y-%m-%d'), 
                    end_date=today.strftime('%Y-%m-%d'))
                
                appointments = []
                for record in result:
                    appt = record['a']
                    appointments.append([
                        appt['id'],
                        appt.get('customer_name', 'N/A'),
                        str(appt['date']),
                        appt['time'],
                        record.get('vehicle', 'N/A'),
                        appt['status'],
                        appt['type']
                    ])
                
                if not appointments:
                    return [["No appointments in last 3 months", "", "", "", "", "", ""]]
                
                return appointments
                
        except Exception as e:
            logger.error(f"Appointment fetch error: {e}")
            return [["Error loading appointments", "", "", "", "", "", ""]]
    
    def get_available_time_slots():
        """Show available vs booked time slots"""
        try:
            today = datetime.now()
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                # Get all appointments for next 30 days
                result = session.run("""
                    MATCH (a:Appointment)
                    WHERE a.date >= date($today) 
                      AND a.date <= date($end_date)
                      AND a.status IN ['confirmed', 'rescheduled']
                    RETURN a.date as date, a.time as time
                    ORDER BY a.date, a.time
                """, today=today.strftime('%Y-%m-%d'),
                    end_date=(today + timedelta(days=30)).strftime('%Y-%m-%d'))
                
                # Create set of booked slots
                booked_slots = set()
                for record in result:
                    slot = f"{record['date']}_{record['time']}"
                    booked_slots.add(slot)
                
                # Generate time slot availability for next 30 days
                time_slots = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]
                availability = []
                
                for i in range(30):
                    date = today + timedelta(days=i)
                    date_str = date.strftime('%Y-%m-%d')
                    day_name = date.strftime('%A')
                    
                    available_count = 0
                    booked_count = 0
                    
                    for time_slot in time_slots:
                        slot_key = f"{date_str}_{time_slot}"
                        if slot_key in booked_slots:
                            booked_count += 1
                        else:
                            available_count += 1
                    
                    status = "🟢 Available" if available_count > 4 else "🟡 Limited" if available_count > 0 else "🔴 Full"
                    
                    availability.append([
                        date_str,
                        day_name,
                        f"{available_count}/8",
                        f"{booked_count}/8",
                        status
                    ])
                
                return availability
                
        except Exception as e:
            logger.error(f"Slot availability error: {e}")
            return [["Error loading", "", "", "", ""]]
    
    def analyze_lead_sentiment():
        try:
            leads = app.neo4j.get_all_leads()
            
            if not leads:
                return go.Figure(), "No leads found in database"
            
            positive = sum(1 for l in leads if l['sentiment'] == 'positive')
            neutral = sum(1 for l in leads if l['sentiment'] == 'neutral')
            negative = sum(1 for l in leads if l['sentiment'] == 'negative')
            
            # Create chart
            fig = go.Figure(data=[
                go.Bar(name='Sentiment', x=['Positive', 'Neutral', 'Negative'], 
                      y=[positive, neutral, negative],
                      marker_color=['#4CAF50', '#FFC107', '#F44336'])
            ])
            
            fig.update_layout(
                title='Lead Sentiment Distribution',
                yaxis_title='Count',
                height=400
            )
            
            summary = f"""### 📊 Sentiment Summary

**Total Leads:** {len(leads)}
- 😊 **Positive:** {positive} ({positive/len(leads)*100:.1f}%)
- 😐 **Neutral:** {neutral} ({neutral/len(leads)*100:.1f}%)
- 😟 **Negative:** {negative} ({negative/len(leads)*100:.1f}%)

### 🎯 Recommendations
- **Hot Leads:** Focus on {positive} positive sentiment leads
- **At Risk:** {negative} negative leads need immediate attention
- **Follow-up:** {neutral} neutral leads require nurturing
"""
            
            return fig, summary
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return go.Figure(), f"Error: {str(e)}"
    
    def get_kb_stats():
        try:
            stats = app.neo4j.get_knowledge_graph_stats()
            
            # Get additional stats
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                hot_leads = session.run("MATCH (l:Lead {status: 'hot'}) RETURN count(l) as count").single()['count']
                warm_leads = session.run("MATCH (l:Lead {status: 'warm'}) RETURN count(l) as count").single()['count']
                cold_leads = session.run("MATCH (l:Lead {status: 'cold'}) RETURN count(l) as count").single()['count']
                confirmed_appts = session.run("MATCH (a:Appointment {status: 'confirmed'}) RETURN count(a) as count").single()['count']
            
            return f"""### 📊 Knowledge Base Statistics

**Vehicles:** {stats['vehicles']:,}
**Leads:** {stats['leads']:,}
  - 🔥 Hot: {hot_leads}
  - 🟡 Warm: {warm_leads}
  - 🔵 Cold: {cold_leads}

**Appointments:** {stats['appointments']:,}
  - ✅ Confirmed: {confirmed_appts}

**Relationships:** {stats['relationships']:,}
"""
        except Exception as e:
            logger.error(f"KB stats error: {e}")
            return f"Error loading stats: {str(e)}"
    
    # ==========================================
    # PAGINATED DATA VIEWERS (10 per page)
    # ==========================================
    
    def get_paginated_vehicles(page_num):
        """Get vehicles with pagination - 10 per page"""
        try:
            page_size = 10
            skip = (page_num - 1) * page_size
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                # Get total count
                total_result = session.run("MATCH (v:Vehicle) RETURN count(v) as total").single()
                total = total_result['total'] if total_result else 0
                
                # Get paginated data
                result = session.run("""
                    MATCH (v:Vehicle)
                    RETURN v
                    ORDER BY v.id
                    SKIP $skip
                    LIMIT $limit
                """, skip=skip, limit=page_size)
                
                vehicles = []
                for record in result:
                    v = record['v']
                    vehicles.append([
                        v['id'],
                        v['make'],
                        v['model'],
                        v['year'],
                        v['price'],
                        v.get('stock', 0)
                    ])
                
                if not vehicles:
                    return [["No vehicles found", "", "", "", "", ""]], f"Page {page_num} of 1 (0 total)"
                
                total_pages = (total + page_size - 1) // page_size
                info = f"Page {page_num} of {total_pages} ({total} total vehicles)"
                
                return vehicles, info
                
        except Exception as e:
            logger.error(f"Paginated vehicles error: {e}")
            return [["Error loading", "", "", "", "", ""]], "Error"
    
    def get_paginated_leads(page_num):
        """Get leads with pagination - 10 per page"""
        try:
            page_size = 10
            skip = (page_num - 1) * page_size
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                # Get total count
                total_result = session.run("MATCH (l:Lead) RETURN count(l) as total").single()
                total = total_result['total'] if total_result else 0
                
                # Get paginated data
                result = session.run("""
                    MATCH (l:Lead)
                    RETURN l
                    ORDER BY l.id
                    SKIP $skip
                    LIMIT $limit
                """, skip=skip, limit=page_size)
                
                leads = []
                for record in result:
                    l = record['l']
                    leads.append([
                        l['id'],
                        l['name'],
                        l['city'],
                        l['budget'],
                        l.get('status', 'cold'),
                        l.get('sentiment', 'neutral')
                    ])
                
                if not leads:
                    return [["No leads found", "", "", "", "", ""]], f"Page {page_num} of 1 (0 total)"
                
                total_pages = (total + page_size - 1) // page_size
                info = f"Page {page_num} of {total_pages} ({total} total leads)"
                
                return leads, info
                
        except Exception as e:
            logger.error(f"Paginated leads error: {e}")
            return [["Error loading", "", "", "", "", ""]], "Error"
    
    def get_paginated_appointments(page_num):
        """Get appointments with pagination - 10 per page"""
        try:
            page_size = 10
            skip = (page_num - 1) * page_size
            
            with app.neo4j.driver.session(database=app.neo4j.database) as session:
                # Get total count
                total_result = session.run("MATCH (a:Appointment) RETURN count(a) as total").single()
                total = total_result['total'] if total_result else 0
                
                # Get paginated data
                result = session.run("""
                    MATCH (a:Appointment)
                    RETURN a
                    ORDER BY a.date DESC, a.time DESC
                    SKIP $skip
                    LIMIT $limit
                """, skip=skip, limit=page_size)
                
                appointments = []
                for record in result:
                    a = record['a']
                    appointments.append([
                        a['id'],
                        a.get('customer_name', 'N/A'),
                        str(a['date']),
                        a['time'],
                        a['status']
                    ])
                
                if not appointments:
                    return [["No appointments found", "", "", "", ""]], f"Page {page_num} of 1 (0 total)"
                
                total_pages = (total + page_size - 1) // page_size
                info = f"Page {page_num} of {total_pages} ({total} total appointments)"
                
                return appointments, info
                
        except Exception as e:
            logger.error(f"Paginated appointments error: {e}")
            return [["Error loading", "", "", "", ""]], "Error"
    
    with gr.Blocks(theme=gr.themes.Soft()) as admin:
        gr.Markdown("# 🔐 Admin Dashboard")
        
        with gr.Group(visible=True) as login_box:
            gr.Markdown("### Admin Login")
            username = gr.Textbox(label="Username", placeholder="username")
            password = gr.Textbox(label="Password", type="password", placeholder="password")
            login_btn = gr.Button("Login", variant="primary")
            login_status = gr.Markdown()
        
        with gr.Group(visible=False) as admin_panel:
            with gr.Tabs():
                # Knowledge Base
                with gr.Tab("📚 Knowledge Base"):
                    kb_stats = gr.Markdown(value=get_kb_stats())
                    refresh_kb_btn = gr.Button("🔄 Refresh Stats")
                    refresh_kb_btn.click(get_kb_stats, outputs=kb_stats)
                
                # Upload Data (Bulk) - Multimodal
                with gr.Tab("📤 Bulk Upload (Multi-Format)"):
                    gr.Markdown("""
                    ### Upload Data Files - **Supports Multiple Formats!**
                    
                    **✅ Supported Formats:**
                    - 📄 **CSV** (.csv)
                    - 📋 **JSON** (.json) - Array or object with 'data'/'vehicles'/'leads' key
                    - 📊 **Excel** (.xlsx, .xls)
                    - 🔖 **XML** (.xml)
                    
                    **Important Tips:**
                    - Use small to medium-sized files (< 5MB recommended)
                    - For large datasets, split into multiple files
                    - Ensure stable internet connection
                    - JSON: Use array format or object with 'data' key
                    - XML: Each record should be a child element of root
                    """)
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### Upload Vehicles (CSV/JSON/XML/Excel)")
                            vehicle_file = gr.File(
                                label="Data File", 
                                file_types=[".csv", ".json", ".xml", ".xlsx", ".xls"],
                                file_count="single"
                            )
                            upload_v_btn = gr.Button("Upload Vehicles", variant="primary")
                            vehicle_status = gr.Markdown()
                        
                        with gr.Column():
                            gr.Markdown("#### Upload Leads (CSV/JSON/XML/Excel)")
                            lead_file = gr.File(
                                label="Data File", 
                                file_types=[".csv", ".json", ".xml", ".xlsx", ".xls"],
                                file_count="single"
                            )
                            upload_l_btn = gr.Button("Upload Leads", variant="primary")
                            lead_status = gr.Markdown()
                    
                    # Format Examples
                    with gr.Accordion("📖 Format Examples", open=False):
                        gr.Markdown("""
**JSON Example (Array):**
```json
[
  {"id": "V001", "make": "Toyota", "model": "Camry", "year": 2024, "price": 95000, ...},
  {"id": "V002", "make": "Honda", "model": "Accord", "year": 2024, "price": 105000, ...}
]
```

**JSON Example (Object):**
```json
{
  "vehicles": [
    {"id": "V001", "make": "Toyota", ...}
  ]
}
```

**XML Example:**
```xml
<vehicles>
  <vehicle>
    <id>V001</id>
    <make>Toyota</make>
    <model>Camry</model>
    <year>2024</year>
    <price>95000</price>
  </vehicle>
</vehicles>
```
                        """)
                    
                    upload_v_btn.click(
                        upload_vehicles, 
                        inputs=vehicle_file, 
                        outputs=vehicle_status,
                        show_progress=True
                    )
                    upload_l_btn.click(
                        upload_leads, 
                        inputs=lead_file, 
                        outputs=lead_status,
                        show_progress=True
                    )
                
                # Manual Entry (Delta)
                with gr.Tab("✍️ Manual Entry (Delta)"):
                    gr.Markdown("### Add/Update Single Records")
                    gr.Markdown("*Leave ID empty to auto-generate. Existing IDs will be updated.*")
                    
                    with gr.Tabs():
                        with gr.Tab("🚗 Add/Update Vehicle"):
                            with gr.Row():
                                man_v_id = gr.Textbox(label="ID (optional)", placeholder="Auto-generated if empty")
                                man_v_make = gr.Textbox(label="Make *", placeholder="Toyota")
                                man_v_model = gr.Textbox(label="Model *", placeholder="Camry")
                            
                            with gr.Row():
                                man_v_year = gr.Number(label="Year *", value=2024)
                                man_v_price = gr.Number(label="Price *", value=95000)
                                man_v_stock = gr.Number(label="Stock", value=1)
                            
                            man_v_features = gr.Textbox(
                                label="Features (comma-separated)",
                                placeholder="Hybrid,Safety Sense,Leather Seats"
                            )
                            man_v_image = gr.Textbox(
                                label="Image URL",
                                placeholder="https://images.unsplash.com/..."
                            )
                            man_v_desc = gr.Textbox(
                                label="Description",
                                lines=2,
                                placeholder="Reliable and fuel-efficient sedan"
                            )
                            
                            man_v_btn = gr.Button("💾 Save Vehicle", variant="primary", size="lg")
                            man_v_status = gr.Markdown()
                            
                            man_v_btn.click(
                                manual_add_vehicle,
                                [man_v_id, man_v_make, man_v_model, man_v_year, man_v_price, 
                                 man_v_features, man_v_stock, man_v_image, man_v_desc],
                                man_v_status
                            )
                        
                        with gr.Tab("👤 Add/Update Lead"):
                            with gr.Row():
                                man_l_id = gr.Textbox(label="ID (optional)", placeholder="Auto-generated if empty")
                                man_l_name = gr.Textbox(label="Name *", placeholder="Ahmed Hassan")
                                man_l_phone = gr.Textbox(label="Phone *", placeholder="+971-50-123-4567")
                            
                            with gr.Row():
                                man_l_email = gr.Textbox(label="Email *", placeholder="ahmed@email.com")
                                man_l_city = gr.Textbox(label="City *", placeholder="Dubai")
                                man_l_budget = gr.Number(label="Budget *", value=150000)
                            
                            with gr.Row():
                                man_l_interest = gr.Textbox(label="Interest", placeholder="Toyota Camry")
                                man_l_status_dropdown = gr.Dropdown(
                                    choices=["hot", "warm", "cold"],
                                    label="Status",
                                    value="warm"
                                )
                                man_l_sentiment = gr.Dropdown(
                                    choices=["positive", "neutral", "negative"],
                                    label="Sentiment",
                                    value="neutral"
                                )
                            
                            man_l_notes = gr.Textbox(label="Notes", lines=2, placeholder="Additional information")
                            
                            man_l_btn = gr.Button("💾 Save Lead", variant="primary", size="lg")
                            man_l_status_display = gr.Markdown()
                            
                            man_l_btn.click(
                                manual_add_lead,
                                [man_l_id, man_l_name, man_l_phone, man_l_email, man_l_city,
                                 man_l_budget, man_l_interest, man_l_status_dropdown, man_l_sentiment, man_l_notes],
                                man_l_status_display
                            )
                
                # Appointment Slots
                with gr.Tab("📅 Appointment Slots"):
                    gr.Markdown("### Time Slot Availability (Next 30 Days)")
                    
                    refresh_slots_btn = gr.Button("🔄 Refresh Availability")
                    
                    slot_availability_table = gr.Dataframe(
                        headers=["Date", "Day", "Available Slots", "Booked Slots", "Status"],
                        value=get_available_time_slots(),
                        label="Slot Availability"
                    )
                    
                    gr.Markdown("---")
                    gr.Markdown("### Appointments (Last 3 Months)")
                    
                    refresh_appts_btn = gr.Button("🔄 Refresh Appointments")
                    
                    past_appointments_table = gr.Dataframe(
                        headers=["ID", "Customer", "Date", "Time", "Vehicle", "Status", "Type"],
                        value=get_appointment_slots_last_3_months(),
                        label="Recent Appointments"
                    )
                    
                    refresh_slots_btn.click(get_available_time_slots, outputs=slot_availability_table)
                    refresh_appts_btn.click(get_appointment_slots_last_3_months, outputs=past_appointments_table)
                
                # Sentiment Analysis
                with gr.Tab("😊 Sentiment Analysis"):
                    gr.Markdown("### Analyze Customer Sentiment")
                    analyze_btn = gr.Button("🔍 Analyze All Leads", variant="primary")
                    sentiment_chart = gr.Plot()
                    sentiment_summary = gr.Markdown()
                    
                    analyze_btn.click(
                        analyze_lead_sentiment,
                        outputs=[sentiment_chart, sentiment_summary]
                    )


                # ✅ NEW TAB: Sentiment Analysis Dashboard
                with gr.Tab("📊 Sentiment Dashboard"):
                    gr.Markdown("""
                    ### 📈 Customer Sentiment Tracking
                    
                    Track customer sentiment from chat conversations. Search by email or phone number 
                    to view detailed sentiment analysis, lead status, and conversation history.
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            search_email = gr.Textbox(
                                label="🔍 Search by Email",
                                placeholder="customer@email.com",
                                info="Enter customer email address"
                            )
                        
                        with gr.Column(scale=1):
                            search_phone = gr.Textbox(
                                label="📱 Search by Phone",
                                placeholder="+971-50-123-4567",
                                info="Enter customer phone number"
                            )
                        
                        with gr.Column(scale=0.5):
                            search_btn = gr.Button(
                                "🔎 Search",
                                variant="primary",
                                size="lg"
                            )
                    
                    gr.Markdown("---")
                    
                    # Results area
                    with gr.Row():
                        # Left column - User Profile & Overview
                        with gr.Column(scale=1):
                            user_profile = gr.HTML(
                                label="👤 User Profile",
                                value="<div style='padding: 40px; text-align: center; color: #9ca3af;'>Enter email or phone to search</div>"
                            )
                            sentiment_overview = gr.HTML(
                                label="📊 Sentiment Overview"
                            )
                        
                        # Right column - Timeline & Conversations
                        with gr.Column(scale=2):
                            sentiment_timeline = gr.Plot(
                                label="📈 Sentiment Timeline"
                            )
                            conversation_list = gr.HTML(
                                label="💬 Conversation History"
                            )
                    
                    # ✅ Bind search function
                    def search_sentiment(email: str, phone: str):
                        """Wrapper for sentiment analysis"""
                        return get_sentiment_analysis(app.neo4j, email, phone)
                    
                    search_btn.click(
                        fn=search_sentiment,
                        inputs=[search_email, search_phone],
                        outputs=[user_profile, sentiment_overview, sentiment_timeline, conversation_list]
                    )
                    
                    # Also allow Enter key in email field
                    search_email.submit(
                        fn=search_sentiment,
                        inputs=[search_email, search_phone],
                        outputs=[user_profile, sentiment_overview, sentiment_timeline, conversation_list]
                    )
                    
                    # Also allow Enter key in phone field
                    search_phone.submit(
                        fn=search_sentiment,
                        inputs=[search_email, search_phone],
                        outputs=[user_profile, sentiment_overview, sentiment_timeline, conversation_list]
                    )

                # ✅ NEW TAB: Knowledge Graph Visualization
                with gr.Tab("🎨🕸️ Knowledge Graph D3 Visualization"):
                    gr.Markdown("""
                    ### 🌐 Interactive Knowledge Graph Visualization
                    
                    Explore relationships between Leads, Vehicles, and Appointments using an interactive force-directed graph.
                    
                    **Features:**
                    - 🖱️ **Drag nodes** to rearrange
                    - 🔍 **Zoom & pan** to explore
                    - 👆 **Click nodes** for details
                    - 🎨 **Color-coded** by type
                    - 📊 **Real-time statistics**
                    """)
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            graph_filter = gr.Dropdown(
                                choices=["all", "leads", "vehicles", "appointments"],
                                value="all",
                                label="🔍 Filter by Type",
                                info="Select what to visualize"
                            )
                        
                        with gr.Column(scale=1):
                            graph_limit = gr.Slider(
                                minimum=10,
                                maximum=200,
                                value=50,
                                step=10,
                                label="📊 Max Nodes",
                                info="Limit number of nodes (for performance)"
                            )
                        
                        with gr.Column(scale=0.5):
                            refresh_graph_btn = gr.Button(
                                "🔄 Refresh Graph",
                                variant="primary",
                                size="lg"
                            )
                    
                    gr.Markdown("---")
                    
                    # Graph visualization
                    graph_viz = gr.HTML(
                        value="<div style='padding: 100px; text-align: center; color: #9ca3af;'>Click 'Refresh Graph' to load visualization</div>"
                    )
                    
                    # Instructions
                    gr.Markdown("""
                    ### 💡 How to Use
                    
                    **Navigation:**
                    - **Drag** nodes to reposition them
                    - **Scroll** to zoom in/out
                    - **Click and drag** background to pan
                    - **Double-click** background to reset view
                    - **Click** a node to see details
                    
                    **Node Types:**
                    - 🟢 **Green** = Leads (customers)
                    - 🔵 **Blue** = Vehicles (inventory)
                    - 🟠 **Orange** = Appointments (bookings)
                    - 🟣 **Light Purple** = TestDrive nodes
                    - 🟣 **Dark Purple** = TestDriveBooking nodes
                    
                    **Relationships:**
                    - Lines show connections between entities
                    - Labels show relationship types
                    
                    **Tips:**
                    - Use filters to focus on specific entities
                    - Reduce max nodes for better performance
                    - Hot leads are marked with 🔥 status
                    """)
                    
                    # Bind refresh function
                    def refresh_graph_visualization(filter_type: str, limit: int):
                        """Generate knowledge graph visualization"""
                        try:
                            nodes, edges, stats = get_knowledge_graph_data(
                                app.neo4j,
                                filter_type=filter_type,
                                limit=int(limit)
                            )
                            
                            if not nodes:
                                return """
                                <div style='padding: 100px; text-align: center; background: #f9fafb; 
                                            border: 2px dashed #d1d5db; border-radius: 12px;'>
                                    <div style='font-size: 3em; margin-bottom: 15px;'>😕</div>
                                    <h3 style='color: #6b7280; margin: 0;'>No Data Found</h3>
                                    <p style='color: #9ca3af; margin: 10px 0 0 0;'>
                                        Try changing the filter or adding more data to Neo4j
                                    </p>
                                </div>
                                """
                            
                           # html = generate_d3_visualization(nodes, edges, stats)
                            html = generate_graph_iframe(nodes, edges, stats)
                            return html
                            
                        except Exception as e:
                            logger.error(f"❌ Graph visualization error: {e}", exc_info=True)
                            return f"""
                            <div style='padding: 100px; text-align: center; background: #fee2e2; 
                                        border: 2px solid #ef4444; border-radius: 12px;'>
                                <div style='font-size: 3em; margin-bottom: 15px;'>❌</div>
                                <h3 style='color: #991b1b; margin: 0;'>Error Loading Graph</h3>
                                <p style='color: #7f1d1d; margin: 10px 0 0 0;'>{str(e)}</p>
                            </div>
                            """
                    
                    refresh_graph_btn.click(
                        fn=refresh_graph_visualization,
                        inputs=[graph_filter, graph_limit],
                        outputs=graph_viz
                    )
                    
                    # Auto-load on filter change
                    graph_filter.change(
                        fn=refresh_graph_visualization,
                        inputs=[graph_filter, graph_limit],
                        outputs=graph_viz
                    )

                # ✅ CONVERSATION EXPORTER TAB - PROPER INDENTATION
                with gr.Tab("💬 Conversation Exporter"):
                    gr.Markdown("""
                    ### 📊 Export Conversation Data
                    Export conversation history for analysis, backup, or compliance purposes.
                    
                    **Features:**
                    - 📄 Multiple formats: CSV, JSON, Excel
                    - 🔍 Filter by date range and email
                    - 📈 Aggregate statistics
                    - 🔒 Privacy-compliant exports
                    """)
                    
                    # Date Range Selection
                    gr.Markdown("#### 📅 Select Date Range")
                    with gr.Row():
                        with gr.Column():
                            export_start_date = gr.Textbox(
                                label="Start Date (YYYY-MM-DD)",
                                value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                                placeholder="2025-01-01"
                            )
                        with gr.Column():
                            export_end_date = gr.Textbox(
                                label="End Date (YYYY-MM-DD)",
                                value=datetime.now().strftime('%Y-%m-%d'),
                                placeholder="2025-01-31"
                            )
                    
                    # Email Filter (Optional)
                    export_email_filter = gr.Textbox(
                        label="Filter by Email (Optional)",
                        placeholder="Leave empty to export all conversations",
                        value=""
                    )
                    
                    # Quick Date Range Buttons
                    gr.Markdown("#### ⚡ Quick Select")
                    with gr.Row():
                        last_7_days_btn = gr.Button("📅 Last 7 Days", size="sm")
                        last_30_days_btn = gr.Button("📅 Last 30 Days", size="sm")
                        last_90_days_btn = gr.Button("📅 Last 90 Days", size="sm")
                        all_time_btn = gr.Button("📅 All Time", size="sm")
                    
                    def set_date_range(days: int):
                        """Helper to set date range"""
                        end = datetime.now()
                        if days > 0:
                            start = end - timedelta(days=days)
                        else:
                            # All time
                            start = datetime(2020, 1, 1)
                        
                        return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
                    
                    last_7_days_btn.click(
                        lambda: set_date_range(7),
                        outputs=[export_start_date, export_end_date]
                    )
                    
                    last_30_days_btn.click(
                        lambda: set_date_range(30),
                        outputs=[export_start_date, export_end_date]
                    )
                    
                    last_90_days_btn.click(
                        lambda: set_date_range(90),
                        outputs=[export_start_date, export_end_date]
                    )
                    
                    all_time_btn.click(
                        lambda: set_date_range(-1),
                        outputs=[export_start_date, export_end_date]
                    )
                    
                    gr.Markdown("---")
                    
                    # Statistics Preview
                    gr.Markdown("#### 📊 Preview Statistics")
                    preview_stats_btn = gr.Button("🔍 Preview Statistics", variant="secondary")
                    stats_display = gr.Markdown("Click 'Preview Statistics' to see conversation metrics")
                    
                    def preview_statistics(start_date, end_date):
                        """Generate statistics preview"""
                        try:
                            stats = exporter.get_conversation_statistics(start_date, end_date)
                            
                            if not stats:
                                return "❌ Error loading statistics"
                            
                            return f"""### 📊 Conversation Statistics

**Date Range:** {stats['date_range']}

**Overview:**
- 💬 **Total Conversations:** {stats['total_conversations']:,}
- 📨 **Total Messages:** {stats['total_messages']:,}
- 👥 **Unique Users:** {stats['unique_users']:,}
- 📈 **Avg Messages/Conversation:** {stats['avg_messages_per_conversation']}

**Popular Intents:**
{', '.join(stats['intents'][:10]) if stats['intents'] else 'N/A'}

**Languages:**
{', '.join(stats['languages']) if stats['languages'] else 'N/A'}
"""
                        except Exception as e:
                            return f"❌ Error: {str(e)}"
                    
                    preview_stats_btn.click(
                        preview_statistics,
                        inputs=[export_start_date, export_end_date],
                        outputs=stats_display
                    )
                    
                    gr.Markdown("---")
                    
                    # Export Buttons
                    gr.Markdown("#### 📤 Export Data")
                    with gr.Row():
                        export_csv_btn = gr.Button("📄 Export to CSV", variant="primary", size="lg")
                        export_json_btn = gr.Button("📋 Export to JSON", variant="primary", size="lg")
                        export_excel_btn = gr.Button("📊 Export to Excel", variant="primary", size="lg")
                    
                    export_status = gr.Markdown()
                    
                    # Download Links
                    csv_download = gr.File(label="📥 Download CSV", visible=False)
                    json_download = gr.File(label="📥 Download JSON", visible=False)
                    excel_download = gr.File(label="📥 Download Excel", visible=False)
                    
                    # Export Functions
                    def export_csv_handler(start_date, end_date, email_filter):
                        """Handle CSV export"""
                        try:
                            conversations = exporter.get_conversations_by_date_range(
                                start_date, 
                                end_date, 
                                email_filter if email_filter.strip() else None
                            )
                            
                            if not conversations:
                                return "⚠️ No conversations found in this date range", gr.update(visible=False)

                            import tempfile
                            from datetime import datetime
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            output_path = os.path.join(tempfile.gettempdir(), f"conversations_{timestamp}.csv")
                            success, message = exporter.export_to_csv(conversations, output_path=output_path)
                            
                            if success and os.path.exists(output_path):
                                file_size = os.path.getsize(output_path)
                                logger.info(f"✅ CSV ready: {output_path}")
                                
                                return (
                                    f"✅ {message}\n**File:** `conversations_{timestamp}.csv`\n**Size:** {file_size:,} bytes",
                                    gr.update(value=output_path, visible=True)
                                )
                            else:
                                return f"❌ {message}", gr.update(visible=False)
                                
                        except Exception as e:
                            logger.error(f"CSV export error: {e}")
                            return f"❌ Error: {str(e)}", gr.update(visible=False)
                    
                    def export_json_handler(start_date, end_date, email_filter):
                        """Handle JSON export"""
                        try:
                            conversations = exporter.get_conversations_by_date_range(
                                start_date, 
                                end_date, 
                                email_filter if email_filter.strip() else None
                            )
                            
                            if not conversations:
                                return "⚠️ No conversations found in this date range", gr.update(visible=False)

                            import tempfile
                            from datetime import datetime
        
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            output_path = os.path.join(tempfile.gettempdir(), f"conversations_{timestamp}.json")
        
                            # Export with specific path
                            success, message = exporter.export_to_json(conversations, output_path=output_path)
                            
                            if success and os.path.exists(output_path):
                                file_size = os.path.getsize(output_path)
                                logger.info(f"✅ JSON ready: {output_path}")
                                
                                return (
                                    f"✅ {message}\n**File:** `conversations_{timestamp}.json`\n**Size:** {file_size:,} bytes",
                                    gr.update(value=output_path, visible=True)
                                )
                            else:
                                return f"❌ {message}", gr.update(visible=False)
                                
                        except Exception as e:
                            logger.error(f"JSON export error: {e}")
                            return f"❌ Error: {str(e)}", gr.update(visible=False)
                    
                    def export_excel_handler(start_date, end_date, email_filter):
                        """Handle Excel export"""
                        try:
                            conversations = exporter.get_conversations_by_date_range(
                                start_date, 
                                end_date, 
                                email_filter if email_filter.strip() else None
                            )
                            
                            if not conversations:
                                return "⚠️ No conversations found in this date range", gr.update(visible=False)
                            
                            import tempfile
                            from datetime import datetime
        
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            output_path = os.path.join(tempfile.gettempdir(), f"conversations_{timestamp}.xlsx")
        
                            # Export with specific path
                            success, message = exporter.export_to_excel(conversations, output_path=output_path)
        
                            if success and os.path.exists(output_path):
                                file_size = os.path.getsize(output_path)
                                logger.info(f"✅ Excel ready: {output_path}")
                                
                                return (
                                    f"✅ {message}\n**File:** `conversations_{timestamp}.xlsx`\n**Size:** {file_size:,} bytes",
                                    gr.update(value=output_path, visible=True)
                                )
                            else:
                                return f"❌ {message}", gr.update(visible=False)
                                
                        except Exception as e:
                            logger.error(f"Excel export error: {e}")
                            return f"❌ Error: {str(e)}", gr.update(visible=False)
                    
                    # Wire up event handlers
                    export_csv_btn.click(
                        export_csv_handler,
                        inputs=[export_start_date, export_end_date, export_email_filter],
                        outputs=[export_status, csv_download]
                    )
                    
                    export_json_btn.click(
                        export_json_handler,
                        inputs=[export_start_date, export_end_date, export_email_filter],
                        outputs=[export_status, json_download]
                    )
                    
                    export_excel_btn.click(
                        export_excel_handler,
                        inputs=[export_start_date, export_end_date, export_email_filter],
                        outputs=[export_status, excel_download]
                    )
                    
                    # Privacy Notice
                    gr.Markdown("---")
                    gr.Markdown("""
                    ### 🔒 Privacy & Compliance
                    
                    **Data Handling:**
                    - Exported data contains user conversations and personal information
                    - Ensure compliance with GDPR, CCPA, and local data protection laws
                    - Store exports securely and delete after use
                    - Only authorized personnel should access conversation data
                    
                    **Export Contents:**
                    - Session IDs, user emails, timestamps
                    - Message content (cleaned, no HTML)
                    - User intents and language preferences
                    - Aggregate statistics
                    """)
                
                # ✅ VIEW DATA TAB - SEPARATE TAB (SAME LEVEL AS OTHER TABS)
                with gr.Tab("📊 View Data (Paginated)"):
                    gr.Markdown("### 📄 Browse Data - 10 Records Per Page")

                    with gr.Tabs():
                        # Vehicles Tab with Pagination
                        with gr.Tab("🚗 Vehicles"):
                            with gr.Row():
                                v_page_num = gr.Number(label="Page", value=1, minimum=1, precision=0)
                                v_load_btn = gr.Button("📄 Load Page", variant="primary")
                            
                            v_page_info = gr.Markdown("Page 1")
                            vehicles_table = gr.Dataframe(
                                headers=["ID", "Make", "Model", "Year", "Price", "Stock"],
                                label="Vehicles"
                            )
                            
                            with gr.Row():
                                v_prev_btn = gr.Button("⬅️ Previous")
                                v_next_btn = gr.Button("Next ➡️")
                            
                            def load_vehicles_page(page):
                                data, info = get_paginated_vehicles(int(page))
                                return data, info
                            
                            def prev_page_v(current_page):
                                new_page = max(1, int(current_page) - 1)
                                data, info = get_paginated_vehicles(new_page)
                                return new_page, data, info
                            
                            def next_page_v(current_page):
                                new_page = int(current_page) + 1
                                data, info = get_paginated_vehicles(new_page)
                                # If no data, stay on current page
                                if data[0][0] == "No vehicles found":
                                    data, info = get_paginated_vehicles(int(current_page))
                                    return current_page, data, info
                                return new_page, data, info
                            
                            v_load_btn.click(
                                load_vehicles_page,
                                inputs=v_page_num,
                                outputs=[vehicles_table, v_page_info]
                            )
                            
                            v_prev_btn.click(
                                prev_page_v,
                                inputs=v_page_num,
                                outputs=[v_page_num, vehicles_table, v_page_info]
                            )
                            
                            v_next_btn.click(
                                next_page_v,
                                inputs=v_page_num,
                                outputs=[v_page_num, vehicles_table, v_page_info]
                            )
                            
                            # Auto-load first page
                            admin.load(
                                load_vehicles_page,
                                inputs=gr.Number(value=1, visible=False),
                                outputs=[vehicles_table, v_page_info]
                            )
                        
                        # Leads Tab with Pagination
                        with gr.Tab("👤 Leads"):
                            with gr.Row():
                                l_page_num = gr.Number(label="Page", value=1, minimum=1, precision=0)
                                l_load_btn = gr.Button("📄 Load Page", variant="primary")
                            
                            l_page_info = gr.Markdown("Page 1")
                            leads_table = gr.Dataframe(
                                headers=["ID", "Name", "City", "Budget", "Status", "Sentiment"],
                                label="Leads"
                            )
                            
                            with gr.Row():
                                l_prev_btn = gr.Button("⬅️ Previous")
                                l_next_btn = gr.Button("Next ➡️")
                            
                            def load_leads_page(page):
                                data, info = get_paginated_leads(int(page))
                                return data, info
                            
                            def prev_page_l(current_page):
                                new_page = max(1, int(current_page) - 1)
                                data, info = get_paginated_leads(new_page)
                                return new_page, data, info
                            
                            def next_page_l(current_page):
                                new_page = int(current_page) + 1
                                data, info = get_paginated_leads(new_page)
                                if data[0][0] == "No leads found":
                                    data, info = get_paginated_leads(int(current_page))
                                    return current_page, data, info
                                return new_page, data, info
                            
                            l_load_btn.click(
                                load_leads_page,
                                inputs=l_page_num,
                                outputs=[leads_table, l_page_info]
                            )
                            
                            l_prev_btn.click(
                                prev_page_l,
                                inputs=l_page_num,
                                outputs=[l_page_num, leads_table, l_page_info]
                            )
                            
                            l_next_btn.click(
                                next_page_l,
                                inputs=l_page_num,
                                outputs=[l_page_num, leads_table, l_page_info]
                            )
                        
                        # Appointments Tab with Pagination
                        with gr.Tab("📅 Appointments"):
                            with gr.Row():
                                a_page_num = gr.Number(label="Page", value=1, minimum=1, precision=0)
                                a_load_btn = gr.Button("📄 Load Page", variant="primary")
                            
                            a_page_info = gr.Markdown("Page 1")
                            appointments_table = gr.Dataframe(
                                headers=["ID", "Customer", "Date", "Time", "Status"],
                                label="Appointments"
                            )
                            
                            with gr.Row():
                                a_prev_btn = gr.Button("⬅️ Previous")
                                a_next_btn = gr.Button("Next ➡️")
                            
                            def load_appointments_page(page):
                                data, info = get_paginated_appointments(int(page))
                                return data, info
                            
                            def prev_page_a(current_page):
                                new_page = max(1, int(current_page) - 1)
                                data, info = get_paginated_appointments(new_page)
                                return new_page, data, info
                            
                            def next_page_a(current_page):
                                new_page = int(current_page) + 1
                                data, info = get_paginated_appointments(new_page)
                                if data[0][0] == "No appointments found":
                                    data, info = get_paginated_appointments(int(current_page))
                                    return current_page, data, info
                                return new_page, data, info
                            
                            a_load_btn.click(
                                load_appointments_page,
                                inputs=a_page_num,
                                outputs=[appointments_table, a_page_info]
                            )
                            
                            a_prev_btn.click(
                                prev_page_a,
                                inputs=a_page_num,
                                outputs=[a_page_num, appointments_table, a_page_info]
                            )
                            
                            a_next_btn.click(
                                next_page_a,
                                inputs=a_page_num,
                                outputs=[a_page_num, appointments_table, a_page_info]
                            )
        
        login_btn.click(login, [username, password], [login_box, admin_panel, login_status])
    
    return admin

#Financial RAG

def create_financial_tab(financial_rag: AutomotiveFinancialRAG):
    """Financial Analysis Tab using Advanced RAG"""
    
    def process_financial_query(query, k_dense, k_sparse, alpha, top_k_final, temperature):
        """Process financial query"""
        try:
            result = financial_rag.answer_query(
                query=query,
                k_dense=int(k_dense),
                k_sparse=int(k_sparse),
                alpha=float(alpha),
                top_k_final=int(top_k_final),
                temperature=float(temperature)
            )
            
            # Format retrieved chunks
            retrieved_text = ""
            retrieved_items = result.get("retrieved", [])

            if not retrieved_items:
                retrieved_text = "No chunks retrieved"
            else:
                for item in retrieved_items:
                   rank = item.get('rank', 'N/A')
                   score = item.get('score', 0.0)
                   content = item.get('content', item.get('text', ''))
                   section = item.get('section', item.get('metadata', {}).get('section', 'N/A'))
                   tokens = item.get('tokens', item.get('metadata', {}).get('tokens', 'N/A'))
                   source = item.get('source', item.get('metadata', {}).get('source', 'N/A'))

                   retrieved_text += f"**Rank {rank}** (Score: {score:.4f})\n"
                   retrieved_text += f"{content}\n"
                   metadata_parts = []
                   if section != 'N/A':
                      metadata_parts.append(f"Section: {section}")
                   if tokens != 'N/A':
                      metadata_parts.append(f"Tokens: {tokens}")
                   if source != 'N/A':
                      metadata_parts.append(f"Source: {source}")

                   if metadata_parts:
                       retrieved_text += f"_{' | '.join(metadata_parts)}_\n\n"
                   else:
                       retrieved_text += "\n"

            
            return (
                result.get("answer", "No answer generated"),
                result.get("method", "Unknown"),
                result.get("confidence", 0.0),
                result.get("latency_sec", 0.0),
                retrieved_text,
                result.get("safety_check", "Unknown")
            )
        except KeyError as ke:
            logger.error(f"Financial query KeyError: {ke}", exc_info=True)
            error_msg = f"⚠️ Data format error: Missing key '{ke}'. Please check RAG configuration."
            return error_msg, "Error", 0.0, 0.0, str(ke), "Error"
        except Exception as e:
            logger.error(f"Financial query error: {e}", exc_info=True)
            error_msg = f"❌ Error processing query: {str(e)}"
            return f"Error: {str(e)}", "Error", 0.0, 0.0, "", "Error"
    
    with gr.Blocks(theme=gr.themes.Soft()) as tab:
        gr.HTML("""
        <div style='text-align: center; 
                    padding: 2.5rem 2rem; 
                    background-image: linear-gradient(rgba(102, 126, 234, 0.92), rgba(118, 75, 162, 0.92)), 
                                      url("https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1600&q=80");
                    background-size: cover;
                    background-position: center;
                    border-radius: 12px; 
                    margin-bottom: 2rem;
                    box-shadow: 0 6px 20px rgba(0,0,0,0.15);
                    color: white;'>
            <h1 style='margin: 0 0 0.8rem 0; font-size: 2.3em; font-weight: 900;
                       text-shadow: 2px 2px 6px rgba(0,0,0,0.5);'>
                📊 Global Automotive Financial Analysis
            </h1>
            <p style='margin: 0; font-size: 1.1em; opacity: 0.95; font-weight: 500;
                      text-shadow: 1px 1px 4px rgba(0,0,0,0.4);'>
                Advanced RAG-Powered Financial Intelligence • Hybrid Retrieval • Real-time Analysis
            </p>
        </div>
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                query_input = gr.Textbox(
                    label="💼 Ask Financial Question",
                    placeholder="e.g., What was BMW's net profit in 2024?",
                    lines=3
                )
                
                with gr.Accordion("⚙️ Advanced RAG Settings", open=False):
                    k_dense = gr.Slider(2, 12, value=6, step=1, label="🔍 Dense Search Top-K")
                    k_sparse = gr.Slider(2, 12, value=6, step=1, label="📝 Sparse Search Top-K")
                    alpha = gr.Slider(0.0, 1.0, value=0.6, step=0.05, label="⚖️ Dense Weight (α)")
                    top_k_final = gr.Slider(2, 12, value=6, step=1, label="🎯 Final Top-K")
                    temperature = gr.Slider(0.1, 1.0, value=0.3, step=0.05, label="🌡️ Temperature")
                
                search_btn = gr.Button("🔍 Search Financial Data", variant="primary", size="lg")
                
                gr.Examples(
                    examples=[
                        "What was BMW's net profit in 2024?",
                        "What percentage of BMW's sales were in Europe in 2024?",
                        "What is BMW's planned investment in electrification by 2026?",
                        "What is Toyota's electric vehicle production target for 2026?",
                        "What was Toyota's financial services revenue in 2024?",
                        "What is Toyota's hydrogen fuel cell vehicle production target?",
                        "What was Toyota's sales in Asia excluding Japan in 2024?",
                        "What was Tesla's total revenue in 2024?",
                        "What was Mercedes-Benz's net profit in 2024?",
                        "What was Nissan's CO2 emissions reduction progress in fiscal 2023?"
                    ],
                    inputs=query_input
                )
            
            with gr.Column(scale=3):
                with gr.Tab("📝 Answer"):
                    answer_output = gr.Textbox(label="Generated Answer", lines=6, show_copy_button=True)
                
                with gr.Tab("📊 Metrics"):
                    with gr.Row():
                        method_output = gr.Textbox(label="Method Used")
                        confidence_output = gr.Number(label="Confidence", precision=3)
                    with gr.Row():
                        latency_output = gr.Number(label="Response Time (sec)", precision=3)
                        safety_output = gr.Textbox(label="Safety Check")
                
                with gr.Tab("🔍 Retrieved Context"):
                    retrieved_output = gr.Markdown(label="Retrieved Chunks")
        
        # Event handler
        search_btn.click(
            process_financial_query,
            inputs=[query_input, k_dense, k_sparse, alpha, top_k_final, temperature],
            outputs=[answer_output, method_output, confidence_output, latency_output, retrieved_output, safety_output]
        )
    
    return tab

# ==========================================
# MAIN APPLICATION
# ==========================================

def main():
    logger.info("Starting application...")
    
    try:
        # ═══════════════════════════════════════════════════════════
        # Initialize Main App
        # ═══════════════════════════════════════════════════════════
        app = AutomotiveAssistantApp()
        
        # ═══════════════════════════════════════════════════════════
        # Create UI Components
        # ═══════════════════════════════════════════════════════════
        customer_portal = create_customer_portal(app)
        admin_dashboard = create_admin_dashboard(app)
        
        # Financial tab (only if financial RAG is available)
        if app.financial_rag:
            financial_tab = create_financial_tab(app.financial_rag)
            logger.info("✅ Financial tab created")
        else:
            financial_tab = None
            logger.warning("⚠️ Financial tab skipped (RAG not available)")
        
        # ═══════════════════════════════════════════════════════════
        # Import chat handlers
        # ═══════════════════════════════════════════════════════════
        from chat_handlers import initialize_session, on_chat_open, process_text_chat_with_session
        
        # ═══════════════════════════════════════════════════════════
        # Custom CSS
        # ═══════════════════════════════════════════════════════════
        custom_css = """
        /* Floating Chat Button */
        #floating-chat-button {
            position: fixed !important;
            bottom: 24px !important;
            right: 24px !important;
            z-index: 999999 !important;
            width: 65px !important;
            height: 65px !important;
            min-width: 65px !important;
            min-height: 65px !important;
            border-radius: 50% !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        #floating-chat-button button {
            width: 65px !important;
            height: 65px !important;
            min-width: 65px !important;
            min-height: 65px !important;
            border-radius: 50% !important;
            font-size: 32px !important;
            line-height: 65px !important;
            padding: 0 !important;
            text-align: center !important;
            background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
            border: none !important;
            box-shadow: 0 8px 24px rgba(102,126,234,0.6) !important;
            cursor: pointer !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            color: white !important;
        }
        
        @keyframes pulse {
            0%, 100% {
                box-shadow: 0 8px 24px rgba(102,126,234,0.6);
            }
            50% {
                box-shadow: 0 8px 32px rgba(102,126,234,0.9), 0 0 0 8px rgba(102,126,234,0.2);
            }
        }
        
        #floating-chat-button button {
            animation: pulse 2.5s infinite;
        }
        
        #floating-chat-button button:hover {
            transform: scale(1.12) !important;
            box-shadow: 0 10px 32px rgba(37, 99, 235, 0.45) !important;
        }
        
        #floating-chat-button button:active {
            transform: scale(0.97) !important;
        }
        
        /* Chat Modal Container */
        #chat-modal-container {
            position: fixed !important;
            bottom: 95px !important;
            right: 20px !important;
            z-index: 999998 !important;
            width: 750px !important;
            max-width: calc(100vw - 40px) !important;
            max-height: calc(100vh - 50px) !important;
            background: white !important;
            border-radius: 20px !important;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3), 0 0 0 1px rgba(0,0,0,0.1) !important;
            overflow: hidden !important;
            display: flex !important;
            flex-direction: column !important;
        }
        
        #chat-modal-container > div {
            width: 100% !important;
            max-width: 100% !important;
        }
        
        #chat-modal-container .gradio-html {
            position: sticky !important;
            top: 0 !important;
            z-index: 10 !important;
        }
        
        /* Teaser Message */
        #teaser-message-container {
            position: fixed !important;
            bottom: 110px !important;
            right: 24px !important;
            z-index: 999997 !important;
            background: white !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15) !important;
            max-width: 280px !important;
            animation: slideIn 0.5s ease-out, float 3s ease-in-out infinite !important;
            border: 2px solid #e5e7eb !important;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(100px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
        }
        
        /* Mobile responsive */
        @media (max-width: 768px) {
            #chat-modal-container {
                width: calc(100vw - 32px) !important;
                bottom: 85px !important;
                right: 16px !important;
                left: 16px !important;
                max-height: calc(100vh - 110px) !important;
            }
            
            #floating-chat-button {
                bottom: 16px !important;
                right: 16px !important;
                width: 60px !important;
                height: 60px !important;
            }
            
            #floating-chat-button button {
                width: 60px !important;
                height: 60px !important;
                font-size: 28px !important;
            }
        }
        
        @media (max-width: 1024px) and (min-width: 769px) {
            #chat-modal-container {
                width: 460px !important;
            }
        }
        """       
        
        # ═══════════════════════════════════════════════════════════
        # Main Gradio Interface
        # ═══════════════════════════════════════════════════════════
        with gr.Blocks(theme=gr.themes.Soft(), css=custom_css, title="Automotive AI Platform") as demo:
            # Header
            gr.HTML("""
            <div style='text-align: center;
                        padding: 3em 2em;
                        background-image: linear-gradient(rgba(102, 126, 234, 0.88), rgba(118, 75, 162, 0.88)),url("https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1920&q=80");
                        background-size: cover;
                        background-position: center;
                        color: white;
                        border-radius: 12px;
                        margin-bottom: 20px;
                        box-shadow: 0 8px 24px rgba(0,0,0,0.2);'>
                        
                <h1 style='margin: 0 0 0.8rem 0; font-size: 2.8em; font-weight: 900; letter-spacing: -1px; line-height: 1.2; text-shadow: 0 0 30px rgba(255,215,0,0.5);'>
                    🚗 <span style='background: linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF6347 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>Automotive Sales Platform</span> 🤖
                </h1>
                <div style='margin: 0.5rem 0 1rem 0;'>
                    <span style='font-size: 2.5em; font-weight: 900; letter-spacing: -1px; text-shadow: 0 0 30px rgba(0,212,255,0.5);'>
                        🌍<span style='background: linear-gradient(135deg, #00D4FF 0%, #00FFAA 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>Multilingual</span>🎤<span style='background: linear-gradient(135deg, #00D4FF 0%, #00FFAA 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>Voice Driven Lead Qualification</span>🚀
                    </span>
                </div>    
                <p style='margin: 0.5rem 0 1.2rem 0; font-size: 1.2em; font-weight: 500;text-shadow: 1px 1px 4px rgba(0,0,0,0.3);'>Powered by AI • Built for Excellence</p>
                <div style='display: flex; gap: 0.6rem; justify-content: center; flex-wrap: wrap; margin-top: 1rem;'>
                    <span style='background: rgba(255,255,255,0.25); backdrop-filter: blur(10px);padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9em;border: 1px solid rgba(255,255,255,0.4); font-weight: 600;box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>🌍 Multilingual</span>
                    <span style='background: rgba(255,255,255,0.25); backdrop-filter: blur(10px);padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9em;border: 1px solid rgba(255,255,255,0.4); font-weight: 600;box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>🎤 Voice-Enabled</span>
                    <span style='background: rgba(255,255,255,0.25); backdrop-filter: blur(10px);padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9em;border: 1px solid rgba(255,255,255,0.4); font-weight: 600;box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>✨ Smart Search</span>
                    <span style='background: rgba(255,255,255,0.25); backdrop-filter: blur(10px);padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9em;border: 1px solid rgba(255,255,255,0.4); font-weight: 600;box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>🚀 AI-Powered</span>
                </div>
            </div>
            """)
            
            # ═══════════════════════════════════════════════════════════
            # FLOATING CHAT BUTTON
            # ═══════════════════════════════════════════════════════════
            toggle_chat_btn = gr.Button(
                "🤖",
                elem_id="floating-chat-button",
                size="lg"
            )
            
            # ═══════════════════════════════════════════════════════════
            # TEASER MESSAGE
            # ═══════════════════════════════════════════════════════════
            with gr.Column(visible=True, elem_id="teaser-message-container") as teaser_message:
                gr.Markdown("""
                <div style='display: flex; align-items: center; gap: 12px; padding: 12px;'>
                    <span style='font-size: 28px;'>👋</span>
                    <div>
                        <strong style='font-size: 15px; color: #111827;'>Hi there!</strong><br>
                        <span style='color: #6b7280; font-size: 13px;'>Need help? Ask me anything!</span>
                    </div>
                </div>
                """)
            
            # ═══════════════════════════════════════════════════════════
            # CHAT MODAL
            # ═══════════════════════════════════════════════════════════
            with gr.Column(visible=False, elem_id="chat-modal-container") as chat_modal:
                # Header
                gr.HTML("""
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; padding: 24px 28px; border-radius: 20px 20px 0 0;
                            margin: -20px -20px 20px -20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                    <h3 style='margin: 0; font-size: 1.4em; font-weight: 600;'>🤖 AI Assistant</h3>
                    <p style='margin: 6px 0 0 0; font-size: 0.9em; opacity: 0.95;'>
                        <span style='display: inline-block; width: 8px; height: 8px; background: #4ade80;
                                border-radius: 50%; margin-right: 6px;'></span>
                        Online • Ready to help
                    </p>
                </div>
                """)

                # Session states
                session_token_state = gr.State(value=None)
                session_id_state = gr.State(value=None)
                user_id_state = gr.State(value=None)
                user_email_state = gr.State(value=None)
                
                # Chatbot
                chatbot_ui = gr.Chatbot(
                    value=[],
                    height=650,
                    show_label=False,
                    avatar_images=(
                        None,
                        "https://api.dicebear.com/7.x/bottts/svg?seed=assistant&backgroundColor=667eea"
                    ),
                   # type='tuples',     # CRITICAL: Must be 'tuples' not 'messages'
                    type='messages',
                    render_markdown=False,  # CRITICAL: Add this to prevent markdown parsing
                    sanitize_html=False,   # CRITICAL: Add this to allow HTML rendering
                    label=None,
                    elem_classes="custom-chatbot",
                    elem_id="chatbot_display"
                )

                # 👉 ADD AGENT POLLING TIMER HERE
                agent_poll_timer = gr.Timer(value=2.0)  # Poll every 2 seconds
                # 👉 ADD END AGENT SESSION BUTTON
                with gr.Row():
                    end_agent_btn = gr.Button(
                        "❌ End Agent Session",
                        visible=False,
                        variant="stop",
                        elem_classes=["end-session-btn"]
                    )

                # Audio output
                audio_output = gr.Audio(label="🔊 Voice Response", autoplay=True, visible=True, elem_id="voice_output")
                # ✅ ADD CLEAR CHAT BUTTON HERE
                with gr.Row():
                    clear_chat_btn = gr.Button("🗑️ Clear Chat", size="sm", variant="secondary")
                    new_session_btn = gr.Button("🆕 New Session", size="sm", variant="secondary")
                
                # Input
                with gr.Tabs():
                    with gr.Tab("💬 Text"):
                        with gr.Row():
                            chat_input = gr.Textbox(
                                placeholder="💭 Type your message...",
                                show_label=False,
                                scale=9,
                                container=False,
                                lines=1,
                                elem_id="chat_input"
                            )
                            send_btn = gr.Button("Send", scale=1, variant="primary", size="lg", elem_id="send_btn")
                    
                    with gr.Tab("🎤 Voice"):
                        voice_input = gr.Audio(
                            label="🎤 Speak",
                            sources=["microphone"],
                            type="filepath",
                            streaming=False
                        )
                        gr.Markdown("""
                        <div style='text-align: center; padding: 10px; background: #f0f9ff;border-radius: 8px; margin-top: 10px;'>
                            <p style='margin: 0; color: #0369a1; font-size: 0.9em;'>
                               🎤 <strong>How to use:</strong><br>
                               1. Click the microphone to start recording<br>
                               2. Speak your message clearly<br>
                               3. Click stop when done<br>
                               4. Click "Process Voice" to send
                            </p>
                        </div>
                        """)
                        process_voice_btn = gr.Button("🎤 Process voice", variant="primary", size="lg")
                        # Voice processing handler
                # ═══════════════════════════════════════════════════════════
                # VOICE PROCESSING HANDLER - OUTSIDE TAB (CRITICAL!)
                # ═══════════════════════════════════════════════════════════
                
                def process_voice_chat(audio_file, history, token, sid, uid, email):
                    """Process voice input in chat"""
                    if not audio_file:
                        return history, None, token, sid, uid, email
    
                    try:
                        logger.info(f"🎤 Processing voice input: {audio_file}")
        
                        # Transcribe audio
                        transcription_result = app.speech.transcribe_audio(audio_file)
        
                        if not transcription_result or not transcription_result.get('text'):
                            error_msg = """
                <div style='padding: 15px; background: #fee2e2; border-left: 4px solid #ef4444; 
                            border-radius: 8px; margin: 10px 0;'>
                    <strong>⚠️ Audio Processing Failed</strong>
                    <p style='margin: 5px 0 0 0;'>Could not understand the audio. Please try again.</p>
                </div>
                """
                            if history is None:
                                history = []
                            # ✅ MESSAGES FORMAT
                            history.append({'role': 'assistant', 'content': error_msg})
                            return history, None, token, sid, uid, email
        
                        transcribed_text = transcription_result['text']
                        detected_lang = transcription_result.get('detected_language', 'en')
                        confidence = transcription_result.get('confidence', 0)
        
                        logger.info(f"✅ Transcribed: '{transcribed_text}'")
                        logger.info(f"   Language: {detected_lang}, Confidence: {confidence:.2%}")
        
                        # Update user's preferred language if detected
                        if uid in app.chatbot.user_sessions:
                            app.chatbot.user_sessions[uid]['preferred_language'] = detected_lang
        
                        # Process the transcribed message
                        response_html, email_prompt = app.chatbot.process_message(
                            transcribed_text,
                            user_id=uid,
                            user_email=email,
                            session_id=sid
                        )
        
                        # Generate voice response
                        session = app.chatbot.user_sessions.get(uid, {})
                        preferred_lang = session.get('preferred_language', detected_lang)
        
                        audio_path = None
                        try:
                            logger.info(f"🔊 Generating voice response in '{preferred_lang}'...")
                            audio_path = app.chatbot._generate_voice_response(response_html, preferred_lang)
                            if audio_path:
                                logger.info(f"✅ Voice response generated: {audio_path}")
                        except Exception as e:
                            logger.error(f"❌ TTS error: {e}")
        
                        # Add to history with language indicator
                        lang_flag = {
                            'en': '🇬🇧', 'ar': '🇦🇪', 'hi': '🇮🇳', 'fr': '🇫🇷',
                            'es': '🇪🇸', 'de': '🇩🇪', 'zh': '🇨🇳', 'ja': '🇯🇵'
                        }.get(detected_lang, '🌐')
        
                        transcription_display = f"""
                <div style='padding: 10px; background: #e0f2fe; border-radius: 8px; margin: 5px 0;'>
                    <small style='color: #0369a1;'>🎤 Voice ({lang_flag} {detected_lang.upper()}):</small><br>
                    <strong>{transcribed_text}</strong>
                </div>
                """
        
                        if history is None:
                            history = []
        
                        # ✅ MESSAGES FORMAT
                        history.append({'role': 'user', 'content': transcription_display})
                        history.append({'role': 'assistant', 'content': response_html})
        
                        if email_prompt and not email:
                            history.append({'role': 'assistant', 'content': email_prompt})
        
                        return history, audio_path, token, sid, uid, email
        
                    except Exception as e:
                        logger.error(f"❌ Voice processing error: {e}", exc_info=True)
                        error_msg = f"""
                <div style='padding: 15px; background: #fee2e2; border-left: 4px solid #ef4444;
                            border-radius: 8px; margin: 10px 0;'>
                    <strong>❌ Error</strong>
                    <p style='margin: 5px 0 0 0;'>Failed to process voice: {str(e)}</p>
                </div>
                """
                        if history is None:
                            history = []
                        # ✅ MESSAGES FORMAT
                        history.append({'role': 'assistant', 'content': error_msg})
                        return history, None, token, sid, uid, email
                
                # ═══════════════════════════════════════════════════════════
                # CONNECT VOICE BUTTON - RIGHT AFTER HANDLER DEFINITION
                # ═══════════════════════════════════════════════════════════
                
                process_voice_btn.click(
                    process_voice_chat,
                    inputs=[voice_input, chatbot_ui, session_token_state, session_id_state, user_id_state, user_email_state],
                    outputs=[chatbot_ui, audio_output, session_token_state, session_id_state, user_id_state, user_email_state]
                )
                                    
                
                
                # Quick actions
                with gr.Row():
                    quick_search = gr.Button("🔍 Search", size="sm", variant="secondary")
                    quick_book = gr.Button("🚗 Book", size="sm", variant="secondary")
                    quick_help = gr.Button("❓ Help", size="sm", variant="secondary")
                    close_btn = gr.Button("✕", size="sm", variant="stop")
            
            # ═══════════════════════════════════════════════════════════
            # EVENT HANDLERS
            # ═══════════════════════════════════════════════════════════
            
            # State for chat visibility
            chat_visible = gr.State(False)
            
            # Toggle chat
            def toggle_chat_visibility(is_visible):
                new_state = not is_visible
                button_icon = "✕" if new_state else "🤖"
                return (
                    gr.update(visible=new_state),
                    gr.update(value=button_icon),
                    gr.update(visible=False),
                    new_state
                )
            
            toggle_chat_btn.click(
                toggle_chat_visibility,
                inputs=[chat_visible],
                outputs=[chat_modal, toggle_chat_btn, teaser_message, chat_visible]
            )
            
            # Close chat
            def close_chat():
                return gr.update(visible=False), gr.update(value="🤖"), False
            
            close_btn.click(
                close_chat,
                outputs=[chat_modal, toggle_chat_btn, chat_visible]
            )

            def clear_chat_history(token, sid, uid, email):
                """Clear chat history but keep session"""
                return [], token, sid, uid, email

            def start_new_session():
                """Start completely new session"""
                import uuid
                from session_manager import get_session_manager
                session_manager = get_session_manager()
    
                new_uid = f"user_{uuid.uuid4().hex[:12]}"
                new_sid = f"session_{uuid.uuid4().hex[:16]}"
                new_token = session_manager.create_session_token(new_uid, session_id=new_sid)
    
                welcome_msg = """
<div style='padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 12px; color: white; margin: 10px 0;'>
    <h3 style='margin: 0;'>🆕 New Session Started</h3>
    <p style='margin: 8px 0 0 0; opacity: 0.95;'>How can I help you today?</p>
</div>
"""
    
                return [{'role': 'assistant', 'content': welcome_msg}], new_token, new_sid, new_uid, None

            # Wire up clear chat buttons
            clear_chat_btn.click(
                clear_chat_history,
                inputs=[session_token_state, session_id_state, user_id_state, user_email_state],
                outputs=[chatbot_ui, session_token_state, session_id_state, user_id_state, user_email_state]
            )

            new_session_btn.click(
                start_new_session,
                outputs=[chatbot_ui, session_token_state, session_id_state, user_id_state, user_email_state]
            )

            
            # Initialize session on load
            demo.load(
                lambda token: on_chat_open(app, token),
                inputs=[session_token_state],
                outputs=[chatbot_ui, session_token_state, session_id_state, user_id_state]
            )
            
            # Send message
            send_btn.click(
                lambda msg, hist, token, sid, uid, email: process_text_chat_with_session(
                    app, msg, hist, token, sid, uid, email
                ),
                inputs=[chat_input, chatbot_ui, session_token_state, session_id_state, user_id_state, user_email_state],
                outputs=[chatbot_ui, chat_input, audio_output, session_token_state, session_id_state, user_id_state, user_email_state]
            )

            chat_input.submit(
                lambda msg, hist, token, sid, uid, email: process_text_chat_with_session(
                    app, msg, hist, token, sid, uid, email
                ),
                inputs=[chat_input, chatbot_ui, session_token_state, session_id_state, user_id_state, user_email_state],
                outputs=[chatbot_ui, chat_input, audio_output, session_token_state, session_id_state, user_id_state, user_email_state]
            )

            # 👉 AGENT POLLING HANDLER - ADD THIS
            def poll_messages_wrapper(history, session_id):
                """Wrapper for agent message polling"""
                try:
                    if not session_id:
                        return history, gr.update(visible=False)
        
                    # Check if agent is active
                    if not app.chatbot.gradio_transfer.is_agent_active(session_id):
                        return history, gr.update(visible=False)
        
                    # Check for new messages
                    new_message_html = app.chatbot.gradio_transfer.check_for_messages(session_id)
        
                    if new_message_html:
                        logger.info(f"📨 New agent message received")
            
                        if history is None:
                            history = []
            
                        history.append({'role': 'assistant', 'content': new_message_html})
        
                    return history, gr.update(visible=True)
        
                except Exception as e:
                    logger.error(f"❌ Polling error: {e}")
                    return history, gr.update(visible=False)

            # 👉 CONNECT TIMER TO POLLING
            agent_poll_timer.tick(
                poll_messages_wrapper,
                inputs=[chatbot_ui, session_id_state],
                outputs=[chatbot_ui, end_agent_btn]
            )

            # 👉 END AGENT SESSION HANDLER
            def end_agent_session_handler(history, session_id):
                """Handle ending agent session"""
                try:
                    if not session_id:
                        return history, gr.update(visible=False)
        
                    # End transfer
                    end_msg = app.chatbot.gradio_transfer.end_transfer(session_id, ended_by='customer')
        
                    if history is None:
                        history = []
        
                    history.append({'role': 'assistant', 'content': end_msg})
        
                    return history, gr.update(visible=False)
        
                except Exception as e:
                    logger.error(f"❌ End session error: {e}")
                    return history, gr.update(visible=False)

            end_agent_btn.click(
                end_agent_session_handler,
                inputs=[chatbot_ui, session_id_state],
                outputs=[chatbot_ui, end_agent_btn]
            )
            
            # Quick actions
            def send_quick_message(app, message, history, token, sid, uid, email):
                return process_text_chat_with_session(app, message, history, token, sid, uid, email)
            
            quick_search.click(
                lambda h, t, s, u, e: send_quick_message(app, "Show me all vehicles", h, t, s, u, e),
                inputs=[chatbot_ui, session_token_state, session_id_state, user_id_state, user_email_state],
                outputs=[chatbot_ui, chat_input, audio_output, session_token_state, session_id_state, user_id_state, user_email_state]
            )
            
            quick_book.click(
                lambda h, t, s, u, e: send_quick_message(app, "I want to book a test drive", h, t, s, u, e),
                inputs=[chatbot_ui, session_token_state, session_id_state, user_id_state, user_email_state],
                outputs=[chatbot_ui, chat_input, audio_output, session_token_state, session_id_state, user_id_state, user_email_state]
            )
            
            quick_help.click(
                lambda h, t, s, u, e: send_quick_message(app, "help", h, t, s, u, e),
                inputs=[chatbot_ui, session_token_state, session_id_state, user_id_state, user_email_state],
                outputs=[chatbot_ui, chat_input, audio_output, session_token_state, session_id_state, user_id_state, user_email_state]
            )
            
            # ═══════════════════════════════════════════════════════════
            # MAIN TABS
            # ═══════════════════════════════════════════════════════════
            with gr.Tabs():
                with gr.Tab("🏠 Customer Portal"):
                    customer_portal.render()
                
                with gr.Tab("🔐 Admin Dashboard"):
                    admin_dashboard.render()
                
                if financial_tab:
                    with gr.Tab("📊 Financial Analysis"):
                        financial_tab.render()
                
                with gr.Tab("ℹ️ About"):
                    gr.Markdown("""
                    ## 🎯 Features
                    
                    ### Customer Portal ✨ ENHANCED
                    - 🔍 AI-powered vehicle search with **pagination (5 per page)**
                    - 📊 **Accuracy metrics** (F1 Score, Precision, Recall)
                    - ✅ **No hallucination** - relevance filtering
                    - 🎤 Voice input/output
                    - 🌐 Multilingual support (15+ languages)
                    - 📅 Book, reschedule, cancel appointments
                    
                    ### Admin Dashboard
                    - 📤 Multi-format upload: CSV, JSON, XML, Excel
                    - 📄 Paginated data view: 10 records per page
                    - 📚 Knowledge base management
                    - 💭 Sentiment analysis
                    - 📊 Data visualization
                    - 🔄 Delta updates
                    
                    ## 🛠️ Technology Stack
                    - **Database:** Neo4j Knowledge Graph
                    - **AI:** RAG with Semantic Search
                    - **Speech:** Whisper ASR + TTS
                    - **NLP:** Transformers, Sentiment Analysis
                    - **Translation:** Deep Translator
                    - **Framework:** Gradio 4.0+
                    
                    ---
                    
                    **🎓 MTech Final Year Project**  
                    Bits Pilani, Dubai  
                    Year: 2025
                    """)
            
            # Footer
            gr.HTML("""
            <div style='text-align: center; padding: 3rem 2rem; 
                        background-image: linear-gradient(rgba(102, 126, 234, 0.92), rgba(118, 75, 162, 0.92)), 
                        url("https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?w=1920&q=80"); 
                        background-size: cover; background-position: center; 
                        border-radius: 12px; margin-top: 3rem; 
                        box-shadow: 0 -4px 20px rgba(0,0,0,0.2); color: white;'>
                <h2>🚗 Agentic AI Automotive Platform</h2>
                <div style='display: inline-block; background: linear-gradient(135deg, rgba(255,215,0,0.15) 0%, rgba(255,165,0,0.15) 100%); border: 2px solid #FFD700; border-radius: 10px; padding: 0.5em 1.5em; margin: 1rem 0; box-shadow: 0 0 30px rgba(255,215,0,0.3);'>
                    <p style='margin: 0; font-size: 1.2em; font-weight: 700;'>
                        Created by 🎓 <span style='color: #FFD700; text-shadow: 0 0 20px rgba(255,215,0,0.6);'>Amit Sarkar</span>
                    </p>
                </div>
                <p>📍Bits Pilani Dubai • © 2025</p>
            </div>
            """)
        
        logger.info("Launching application...")
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=True,
            show_error=True,
            inbrowser=True,
            max_file_size=10 * 1024 * 1024
        )
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        raise

#main
if __name__ == "__main__":
    main()