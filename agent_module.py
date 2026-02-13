"""
agent_module.py - Complete Enhanced Agentic AI Core with Test Drive Support
Features:
- ReACT: Reason + Act pattern
- Memory: Conversation history and user context
- Feedback Loop: Learning from interactions
- Sentiment Analysis Integration
- Test Drive Booking Support
- Multi-step Planning
- Autonomous Decision Making
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent:
    """
    Complete Agentic AI with:
    - ReACT: Reason + Act + Observe pattern
    - Memory: Long-term learning and context
    - Feedback Loop: Performance tracking
    - Tool Integration: RAG, Sentiment, Leads, Test Drive, etc.
    """
    
    def __init__(self, tools: Dict[str, Any]):
        """
        Initialize agent with available tools
        
        Args:
            tools: Dictionary of available tools/functions
                   e.g., {'rag': search_fn, 'sentiment': sentiment_fn, 'leads_query': leads_fn}
        """
        self.tools = tools
        self.conversation_history = []
        self.long_term_memory = {}  # User preferences, patterns
        self.feedback_log = []
        self.context = {}
        logger.info(f"✅ Enhanced Agent initialized with {len(tools)} tools: {list(tools.keys())}")
    
    def act(self, user_input: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main ReACT loop: Reason → Act → Observe → Learn
        
        Args:
            user_input: User's input text
            context: Optional context information (language, user_id, etc.)
        
        Returns:
            Agent's complete response with reasoning, results, and response
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"🤖 Agent ReACT Cycle Started")
            logger.info(f"📥 Input: '{user_input[:50]}...'")
            logger.info(f"{'='*60}")
            
            # Update context
            if context:
                self.context.update(context)
            
            # Step 1: REASON - Analyze intent and plan
            reasoning = self._reason(user_input, context)
            logger.info(f"💭 REASON: {reasoning['thought']}")
            logger.info(f"🎯 ACTION: {reasoning['action']}")
            logger.info(f"📊 CONFIDENCE: {reasoning['confidence']:.2%}")
            
            # Step 2: ACT - Execute planned actions
            action_result = self._act_on_reasoning(reasoning, user_input)
            logger.info(f"⚡ ACT: Executed '{reasoning['action']}' - Status: {action_result['status']}")
            
            # Step 3: OBSERVE - Evaluate results
            observation = self._observe(action_result, reasoning)
            logger.info(f"👁️ OBSERVE: Quality={observation['quality']}, Needs refinement={observation.get('needs_refinement', False)}")
            
            # Step 4: RESPOND - Formulate natural language response
            response = self._formulate_response(action_result, observation, reasoning, user_input)
            logger.info(f"💬 RESPONSE: {response[:80]}...")
            
            # Step 5: LEARN - Update memory and improve
            self._learn_from_interaction(user_input, reasoning, observation, response)
            logger.info(f"📚 LEARN: Memory updated")
            
            logger.info(f"{'='*60}\n")
            
            return {
                'reasoning': reasoning,
                'action_result': action_result,
                'observation': observation,
                'response': response,
                'confidence': reasoning.get('confidence', 0.7),
                'intent': reasoning.get('intent', {})
            }
            
        except Exception as e:
            logger.error(f"❌ Agent error: {e}", exc_info=True)
            return self._error_response(str(e))
    
    def _analyze_intent_detailed(self, user_input: str) -> Dict[str, Any]:
        """Detailed intent analysis with scoring"""
        input_lower = user_input.lower()
        
        # Intent patterns with keywords
        intents = {
            'test_drive_booking': {
                'keywords': ['book test drive', 'schedule test drive', 'test drive', 
                            'book a drive', 'want to test', 'try the car', 'test the vehicle',
                            'book drive', 'reserve test drive', 'book_start', 'details_submitted',
                            'select_date', 'confirm_booking'],
                'priority': 1
            },
            'check_availability': {
                'keywords': ['available slots', 'availability', 'free slots', 'when available',
                            'available times', 'check slots', 'show availability', 'open slots'],
                'priority': 1
            },
            'reschedule_booking': {
                'keywords': ['reschedule', 'change date', 'change time', 'move booking',
                            'different date', 'different time', 'postpone', 'change appointment'],
                'priority': 1
            },
            'cancel_booking': {
                'keywords': ['cancel', 'cancel booking', 'cancel test drive', 'dont want',
                            'cancel appointment', 'remove booking', 'delete booking'],
                'priority': 1
            },
            'vehicle_search': {
                'keywords': ['search', 'find', 'show', 'looking', 'want', 'need', 
                            'suv', 'sedan', 'car', 'vehicle', 'luxury', 'electric'],
                'priority': 2
            },
            'appointment': {
                'keywords': ['appointment', 'book', 'schedule', 'visit', 
                            'meeting', 'slot'],
                'priority': 2
            },
            'budget_query': {
                'keywords': ['budget', 'price', 'cost', 'afford', 'expensive', 'cheap', 
                            'aed', 'under', 'within', 'maximum'],
                'priority': 2
            },
            'features_query': {
                'keywords': ['feature', 'specification', 'detail', 'option', 'include', 
                            'equipped', 'comes with', 'has'],
                'priority': 2
            },
            'comparison': {
                'keywords': ['compare', 'versus', 'vs', 'difference', 'better', 
                            'which one', 'or'],
                'priority': 2
            },
            'general_info': {
                'keywords': ['warranty', 'financing', 'trade-in', 'insurance', 'delivery',
                            'service', 'maintenance', 'loan'],
                'priority': 3
            },
            'sentiment_expression': {
                'keywords': ['love', 'hate', 'feel', 'think', 'disappointed', 'happy', 
                            'excited', 'frustrated', 'amazing', 'terrible'],
                'priority': 3
            }
        }
        
        # Score each intent
        scores = {}
        for intent_type, config in intents.items():
            score = sum(1 for keyword in config['keywords'] if keyword in input_lower)
            if score > 0:
                # Apply priority weighting (lower priority = lower score)
                scores[intent_type] = score / config['priority']
        
        # Determine primary intent
        if scores:
            primary_intent = max(scores, key=scores.get)
            confidence = min(scores[primary_intent] * 0.3 + 0.4, 0.95)
        else:
            primary_intent = 'general_query'
            confidence = 0.5
        
        return {
            'type': primary_intent,
            'confidence': confidence,
            'all_scores': scores
        }
    
    def _reason(self, user_input: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        REASON phase: Analyze intent and plan actions
        
        Returns:
            reasoning: {thought, action, confidence, intent, user_history}
        """
        input_lower = user_input.lower()
        
        # Check memory for user context
        user_history = self._get_user_context(context)
        
        # Analyze intent with detailed pattern matching
        intent = self._analyze_intent_detailed(user_input)
        
        # Determine primary action based on intent
        if intent['type'] == 'test_drive_booking':
            thought = "User wants to book a test drive - need to check availability and collect details"
            action = "test_drive_booking"
            confidence = intent['confidence']
        
        elif intent['type'] == 'check_availability':
            thought = "User wants to see available test drive slots"
            action = "check_availability"
            confidence = intent['confidence']
        
        elif intent['type'] == 'reschedule_booking':
            thought = "User wants to reschedule an existing test drive booking"
            action = "reschedule_booking"
            confidence = intent['confidence']
        
        elif intent['type'] == 'cancel_booking':
            thought = "User wants to cancel a test drive booking"
            action = "cancel_booking"
            confidence = intent['confidence']
        
        elif intent['type'] == 'vehicle_search':
            thought = "User wants to search for vehicles based on specific criteria"
            action = "vehicle_search"
            confidence = intent['confidence']
        
        elif intent['type'] == 'appointment':
            thought = "User wants to book, reschedule, or check appointments"
            action = "manage_appointment"
            confidence = intent['confidence']
        
        elif intent['type'] == 'budget_query':
            thought = "User is asking about vehicle pricing and budget options"
            action = "budget_search"
            confidence = intent['confidence']
        
        elif intent['type'] == 'features_query':
            thought = "User wants to know about vehicle features and specifications"
            action = "feature_search"
            confidence = intent['confidence']
        
        elif intent['type'] == 'comparison':
            thought = "User wants to compare different vehicles"
            action = "compare_vehicles"
            confidence = intent['confidence']
        
        elif intent['type'] == 'sentiment_expression':
            thought = "User is expressing feelings or opinions"
            action = "analyze_sentiment"
            confidence = intent['confidence']
        
        elif intent['type'] == 'general_info':
            thought = "User needs general information (warranty, financing, trade-in, etc.)"
            action = "provide_info"
            confidence = intent['confidence']
        
        else:
            thought = "User needs general assistance"
            action = "general_query"
            confidence = 0.6
        
        return {
            'thought': thought,
            'action': action,
            'confidence': confidence,
            'intent': intent,
            'user_history': user_history,
            'timestamp': datetime.now().isoformat()
        }
    
    def _act_on_reasoning(self, reasoning: Dict, user_input: str) -> Dict:
        """
        ACT phase: Execute the planned action using available tools
        
        Returns:
            action_result: {status, data, action, tool_used}
        """
        action = reasoning['action']
        intent = reasoning.get('intent', {})
        
        try:
            # Test Drive Booking
            if action == 'test_drive_booking':
                logger.info("🚗 Processing test drive booking...")
                return {
                    'status': 'success',
                    'data': {'message': 'Test drive booking initiated'},
                    'action': action,
                    'tool_used': 'test_drive_system'
                }
            
            # Check Availability
            elif action == 'check_availability':
                logger.info("📅 Checking availability...")
                return {
                    'status': 'success',
                    'data': {'message': 'Availability check initiated'},
                    'action': action,
                    'tool_used': 'test_drive_system'
                }
            
            # Reschedule Booking
            elif action == 'reschedule_booking':
                logger.info("🔄 Processing reschedule request...")
                return {
                    'status': 'success',
                    'data': {'message': 'Reschedule initiated'},
                    'action': action,
                    'tool_used': 'test_drive_system'
                }
            
            # Cancel Booking
            elif action == 'cancel_booking':
                logger.info("❌ Processing cancellation...")
                return {
                    'status': 'success',
                    'data': {'message': 'Cancellation initiated'},
                    'action': action,
                    'tool_used': 'test_drive_system'
                }
            
            # Vehicle Search
            elif action == 'vehicle_search' and 'rag' in self.tools:
                logger.info("🔍 Executing vehicle search via RAG tool...")
                result = self.tools['rag'](user_input)
                return {
                    'status': 'success',
                    'data': result,
                    'action': action,
                    'tool_used': 'rag'
                }
            
            # Budget Search
            elif action == 'budget_search' and 'rag' in self.tools:
                logger.info("💰 Executing budget-based search...")
                result = self.tools['rag'](user_input)
                return {
                    'status': 'success',
                    'data': result,
                    'action': action,
                    'tool_used': 'rag'
                }
            
            # Feature Search
            elif action == 'feature_search' and 'rag' in self.tools:
                logger.info("✨ Executing feature-based search...")
                result = self.tools['rag'](user_input)
                return {
                    'status': 'success',
                    'data': result,
                    'action': action,
                    'tool_used': 'rag'
                }
            
            # Sentiment Analysis
            elif action == 'analyze_sentiment' and 'sentiment' in self.tools:
                logger.info("😊 Analyzing sentiment...")
                sentiment_result = self.tools['sentiment'](user_input)
                return {
                    'status': 'success',
                    'data': sentiment_result,
                    'action': action,
                    'tool_used': 'sentiment'
                }
            
            # Appointment Management
            elif action == 'manage_appointment':
                logger.info("📅 Processing appointment request...")
                return {
                    'status': 'requires_info',
                    'data': {
                        'message': "I'd be happy to help you book a test drive! Please provide:\n• Your preferred date\n• Vehicle ID (from search results)\n• Your contact information"
                    },
                    'action': action,
                    'tool_used': 'appointment_system'
                }
            
            # Comparison
            elif action == 'compare_vehicles' and 'rag' in self.tools:
                logger.info("⚖️ Executing vehicle comparison...")
                result = self.tools['rag'](user_input)
                return {
                    'status': 'success',
                    'data': result,
                    'action': action,
                    'tool_used': 'rag'
                }
            
            # General Info
            elif action == 'provide_info' and 'rag' in self.tools:
                logger.info("ℹ️ Providing general information...")
                result = self.tools['rag'](user_input)
                return {
                    'status': 'success',
                    'data': result,
                    'action': action,
                    'tool_used': 'rag'
                }
            
            # Leads Query (if tool exists)
            elif 'leads_query' in self.tools and any(word in user_input.lower() for word in ['lead', 'customer', 'prospect']):
                logger.info("👥 Querying leads database...")
                result = self.tools['leads_query'](user_input)
                return {
                    'status': 'success',
                    'data': result,
                    'action': 'leads_query',
                    'tool_used': 'leads_query'
                }
            
            # Default: General Query
            else:
                logger.info("💬 Executing general query...")
                if 'rag' in self.tools:
                    result = self.tools['rag'](user_input)
                else:
                    result = {
                        'message': "I'm here to help! You can ask me about:\n\n🚗 Vehicle search and recommendations\n📅 Booking test drives\n💰 Pricing and financing options\n❓ Warranty, trade-in, and services"
                    }
                return {
                    'status': 'success',
                    'data': result,
                    'action': 'general_query',
                    'tool_used': 'default'
                }
                
        except Exception as e:
            logger.error(f"❌ Action execution error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'action': action,
                'tool_used': 'none'
            }
    
    def _observe(self, action_result: Dict, reasoning: Dict) -> Dict:
        """
        OBSERVE phase: Evaluate the quality of results
        
        Returns:
            observation: {status, quality, result_count, needs_refinement, suggestion}
        """
        status = action_result.get('status')
        data = action_result.get('data', {})
        action = action_result.get('action')
        
        # Success cases
        if status == 'success':
            # Vehicle search results
            if isinstance(data, dict) and 'vehicles' in data:
                vehicles = data.get('vehicles', [])
                
                if len(vehicles) > 0:
                    return {
                        'status': 'success',
                        'quality': 'excellent' if len(vehicles) >= 5 else 'good',
                        'result_count': len(vehicles),
                        'needs_refinement': False,
                        'action_successful': True
                    }
                else:
                    return {
                        'status': 'success',
                        'quality': 'poor',
                        'result_count': 0,
                        'needs_refinement': True,
                        'suggestion': 'Try broader search terms or adjust your filters',
                        'action_successful': False
                    }
            
            # Sentiment analysis results
            elif action == 'analyze_sentiment' and isinstance(data, dict):
                return {
                    'status': 'success',
                    'quality': 'good',
                    'sentiment': data.get('label', 'neutral'),
                    'needs_refinement': False,
                    'action_successful': True
                }
            
            # Test drive booking
            elif action in ['test_drive_booking', 'check_availability', 'reschedule_booking', 'cancel_booking']:
                return {
                    'status': 'success',
                    'quality': 'good',
                    'needs_refinement': False,
                    'action_successful': True
                }
            
            # FAQ/General info
            elif isinstance(data, dict) and 'message' in data:
                return {
                    'status': 'success',
                    'quality': 'adequate',
                    'needs_refinement': False,
                    'action_successful': True
                }
            
            # Default success
            else:
                return {
                    'status': 'success',
                    'quality': 'adequate',
                    'needs_refinement': False,
                    'action_successful': True
                }
        
        # Requires user input
        elif status == 'requires_info':
            return {
                'status': 'awaiting_user_input',
                'quality': 'pending',
                'needs_refinement': False,
                'action_successful': True
            }
        
        # Error cases
        else:
            return {
                'status': 'failed',
                'quality': 'error',
                'needs_refinement': True,
                'error': action_result.get('error', 'Unknown error'),
                'action_successful': False
            }
    
    def _formulate_response(self, action_result: Dict, observation: Dict, 
                           reasoning: Dict, user_input: str) -> str:
        """
        Formulate natural language response based on action results and observation
        
        Returns:
            response: Natural language response string
        """
        status = observation['status']
        quality = observation.get('quality')
        data = action_result.get('data', {})
        action = action_result.get('action')
        
        # Handle different action types
        
        # Test Drive Related Actions - Return empty string (chatbot handles it)
        if action in ['test_drive_booking', 'check_availability', 'reschedule_booking', 'cancel_booking']:
            return ""
        
        # Vehicle Search Results
        if action in ['vehicle_search', 'budget_search', 'feature_search', 'compare_vehicles']:
            if isinstance(data, dict) and 'vehicles' in data:
                vehicles = data.get('vehicles', [])
                
                if len(vehicles) > 0:
                    response = f"✅ Great! I found {len(vehicles)} vehicle(s) matching your search:\n\n"
                    
                    # Show top 3 vehicles
                    for i, v in enumerate(vehicles[:3], 1):
                        response += f"{i}. **{v['year']} {v['make']} {v['model']}** - AED {v['price']:,}\n"
                        if v.get('features'):
                            response += f"   • Features: {', '.join(v['features'][:3])}\n"
                        if v.get('stock', 0) > 0:
                            response += f"   • Stock: {v['stock']} units available ✅\n"
                        else:
                            response += f"   • Stock: Out of stock ❌\n"
                        response += "\n"
                    
                    if len(vehicles) > 3:
                        response += f"_...and {len(vehicles) - 3} more options available_\n"
                    
                    return response.strip()
                
                else:
                    suggestion = observation.get('suggestion', 'Try different search terms')
                    return f"❌ I couldn't find vehicles matching: '{user_input}'\n\n💡 **Suggestion:** {suggestion}\n\nTry:\n• Broader terms (e.g., 'SUV' instead of specific model)\n• Adjust price range\n• Check spelling"
            
            # FAQ or message response
            elif isinstance(data, dict) and 'message' in data:
                return data['message']
        
        # Sentiment Analysis
        elif action == 'analyze_sentiment':
            if isinstance(data, dict):
                sentiment_label = data.get('label', 'NEUTRAL').lower()
                emoji = data.get('emoji', '😊')
                score = data.get('score', 0)
                
                responses = {
                    'positive': f"I can see you're feeling {sentiment_label}! {emoji} That's wonderful! How can I help make your car buying experience even better?",
                    'negative': f"I understand you're feeling {sentiment_label} {emoji}. I'm here to help address any concerns. What can I do to assist you?",
                    'neutral': f"Thank you for sharing your thoughts {emoji}. How can I help you today?"
                }
                
                return responses.get(sentiment_label, responses['neutral'])
        
        # Appointment Management
        elif action == 'manage_appointment':
            if status == 'awaiting_user_input':
                return data.get('message', "I can help you book an appointment. Please provide your details.")
        
        # Leads Query
        elif action == 'leads_query':
            if isinstance(data, dict):
                leads = data.get('leads', [])
                if isinstance(leads, list):
                    return f"📊 I found {len(leads)} lead(s) in our system."
                elif isinstance(leads, dict):
                    return f"📊 Lead information retrieved successfully."
        
        # Error Handling
        if status == 'failed':
            error = observation.get('error', 'Unknown error')
            return f"⚠️ I encountered an issue: {error}\n\nCould you please rephrase your request or try a different query?"
        
        # Default Response
        return """I'm your AI automotive assistant! 🚗

I can help you with:
- 🔍 **Search vehicles** - Find your perfect car
- 📅 **Book test drives** - Schedule your experience
- 💰 **Check pricing** - Get budget options
- ℹ️ **Get information** - Warranty, financing, trade-in
- 😊 **Answer questions** - I'm here to help!

What would you like to know?"""
    
    def _learn_from_interaction(self, user_input: str, reasoning: Dict, 
                                observation: Dict, response: str):
        """
        LEARN phase: Update memory and track performance
        
        Updates:
        - Conversation history
        - Long-term memory (success rates per action)
        - Feedback log
        """
        # Store in conversation history
        interaction = {
            'user_input': user_input,
            'reasoning': reasoning,
            'observation': observation,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'success': observation.get('action_successful', False)
        }
        self.conversation_history.append(interaction)
        
        # Update long-term memory for action patterns
        action = reasoning['action']
        
        if action not in self.long_term_memory:
            self.long_term_memory[action] = {
                'count': 0,
                'successes': 0,
                'success_rate': 0.0,
                'failures': 0,
                'avg_confidence': 0.0
            }
        
        memory = self.long_term_memory[action]
        memory['count'] += 1
        
        # Update success tracking
        if observation.get('action_successful', False):
            memory['successes'] += 1
        else:
            memory['failures'] += 1
        
        # Calculate success rate
        memory['success_rate'] = memory['successes'] / memory['count']
        
        # Update average confidence
        current_avg = memory['avg_confidence']
        new_confidence = reasoning['confidence']
        memory['avg_confidence'] = (current_avg * (memory['count'] - 1) + new_confidence) / memory['count']
        
        # Log feedback
        self.feedback_log.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'success': observation.get('action_successful', False),
            'quality': observation.get('quality'),
            'confidence': reasoning['confidence']
        })
        
        # Keep only last 100 feedback logs
        if len(self.feedback_log) > 100:
            self.feedback_log = self.feedback_log[-100:]
        
        logger.info(f"📚 LEARN: Action '{action}' - Success Rate: {memory['success_rate']:.2%} ({memory['successes']}/{memory['count']})")
    
    def _get_user_context(self, context: Optional[Dict]) -> Dict:
        """Get user context from memory and session"""
        if not context:
            context = {}
        
        # Get recent interactions (last 5)
        recent = self.conversation_history[-5:] if len(self.conversation_history) > 0 else []
        
        # Extract patterns
        recent_actions = [h['reasoning']['action'] for h in recent]
        recent_intents = [h['reasoning'].get('intent', {}).get('type', 'unknown') for h in recent]
        
        return {
            'recent_actions': recent_actions,
            'recent_intents': recent_intents,
            'session_context': context,
            'interaction_count': len(self.conversation_history)
        }
    
    def _error_response(self, error: str) -> Dict:
        """Generate structured error response"""
        return {
            'reasoning': {
                'thought': 'Error occurred during processing',
                'action': 'error',
                'confidence': 0.0,
                'intent': {'type': 'error'}
            },
            'action_result': {
                'status': 'error',
                'error': error,
                'action': 'error'
            },
            'observation': {
                'status': 'failed',
                'quality': 'error',
                'needs_refinement': True
            },
            'response': f"⚠️ I encountered an error: {error}\n\nPlease try again or rephrase your request.",
            'confidence': 0.0
        }
    
    def get_context(self) -> Dict:
        """Get current conversation context"""
        return {
            'history_length': len(self.conversation_history),
            'last_intent': self.conversation_history[-1]['reasoning']['intent'] if self.conversation_history else None,
            'context': self.context
        }
    
    def get_analytics(self) -> Dict:
        """
        Get comprehensive agent performance analytics
        
        Returns:
            analytics: Performance metrics and statistics
        """
        total_interactions = len(self.conversation_history)
        
        if total_interactions == 0:
            return {
                'total_interactions': 0,
                'message': 'No interactions yet'
            }
        
        # Calculate overall success rate
        total_successes = sum(1 for h in self.conversation_history if h.get('success', False))
        overall_success_rate = total_successes / total_interactions
        
        # Action-specific statistics
        action_stats = {}
        for action, data in self.long_term_memory.items():
            action_stats[action] = {
                'count': data['count'],
                'success_rate': data.get('success_rate', 0.0),
                'avg_confidence': data.get('avg_confidence', 0.0),
                'failures': data.get('failures', 0)
            }
        
        # Calculate average confidence
        avg_confidence = sum(h['reasoning']['confidence'] for h in self.conversation_history) / total_interactions
        
        # Recent performance (last 10 interactions)
        recent_10 = self.conversation_history[-10:]
        recent_success_rate = sum(1 for h in recent_10 if h.get('success', False)) / len(recent_10) if recent_10 else 0
        
        return {
            'total_interactions': total_interactions,
            'overall_success_rate': overall_success_rate,
            'recent_success_rate': recent_success_rate,
            'average_confidence': avg_confidence,
            'action_statistics': action_stats,
            'feedback_log_size': len(self.feedback_log),
            'memory_size': len(self.long_term_memory)
        }
    
    def reset(self):
        """Reset agent state (keeps long-term memory)"""
        self.conversation_history = []
        self.context = {}
        logger.info("🔄 Agent conversation state reset (long-term memory preserved)")
    
    def full_reset(self):
        """Complete reset including long-term memory"""
        self.conversation_history = []
        self.long_term_memory = {}
        self.feedback_log = []
        self.context = {}
        logger.info("🔄 Agent fully reset (all memory cleared)")


# Test function
def test_agent():
    """Comprehensive test of agent with all features"""
    
    # Mock tools
    def mock_rag(query):
        if 'camry' in query.lower():
            return {
                'vehicles': [
                    {'make': 'Toyota', 'model': 'Camry', 'year': 2024, 'price': 85000, 
                     'features': ['Hybrid', 'Safety Sense', 'Apple CarPlay'], 'stock': 5},
                ],
                'count': 1
            }
        else:
            return {
                'vehicles': [
                    {'make': 'Toyota', 'model': 'Camry', 'year': 2024, 'price': 85000, 
                     'features': ['Hybrid'], 'stock': 5},
                    {'make': 'Honda', 'model': 'Accord', 'year': 2024, 'price': 90000,
                     'features': ['Turbo'], 'stock': 3}
                ],
                'count': 2
            }
    
    def mock_sentiment(text):
        if any(word in text.lower() for word in ['love', 'great', 'excellent']):
            return {'label': 'POSITIVE', 'score': 0.95, 'emoji': '😊'}
        elif any(word in text.lower() for word in ['hate', 'bad', 'terrible']):
            return {'label': 'NEGATIVE', 'score': 0.90, 'emoji': '😞'}
        else:
            return {'label': 'NEUTRAL', 'score': 0.60, 'emoji': '😐'}
    
    def mock_leads_query(query):
        return {
            'leads': [
                {'id': 'L001', 'name': 'Ahmed', 'status': 'hot'},
                {'id': 'L002', 'name': 'Fatima', 'status': 'warm'}
            ]
        }
    
    # Initialize agent with all tools
    tools = {
        'rag': mock_rag,
        'sentiment': mock_sentiment,
        'leads_query': mock_leads_query
    }
    
    agent = Agent(tools)
    
    # Test queries
    test_queries = [
        "Show me affordable sedans under 100k",
        "I'm very excited about buying a car!",
        "What are the features of Toyota Camry?",
        "I feel disappointed with the service",
        "Show me all leads in the system"
    ]
    
    print("\n" + "="*60)
    print("🧪 TESTING ENHANCED AGENT WITH ALL FEATURES")
    print("="*60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─'*60}")
        print(f"Test {i}/{len(test_queries)}")
        print(f"{'─'*60}")
        print(f"🧑 User: {query}")
        print()
        
        result = agent.act(query)
        
        print(f"💭 Reasoning: {result['reasoning']['thought']}")
        print(f"🎯 Action: {result['reasoning']['action']}")
        print(f"📊 Confidence: {result['confidence']:.2%}")
        print(f"👁️ Observation: {result['observation']['quality']}")
        print()
        print(f"🤖 Agent Response:")
        print(f"{result['response']}")
        print()
    
    # Show analytics
    print("\n" + "="*60)
    print("📊 AGENT PERFORMANCE ANALYTICS")
    print("="*60)
    analytics = agent.get_analytics()
    print(f"Total Interactions: {analytics['total_interactions']}")
    print(f"Overall Success Rate: {analytics['overall_success_rate']:.2%}")
    print(f"Average Confidence: {analytics['average_confidence']:.2%}")
    print(f"\nAction Statistics:")
    for action, stats in analytics['action_statistics'].items():
        print(f"  • {action}:")
        print(f"    - Count: {stats['count']}")
        print(f"    - Success Rate: {stats['success_rate']:.2%}")
        print(f"    - Avg Confidence: {stats['avg_confidence']:.2%}")
    
    print("\n✅ Enhanced Agent Test Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_agent()