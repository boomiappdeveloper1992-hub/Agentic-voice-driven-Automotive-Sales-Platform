"""
gradio_agent_transfer.py - Agent Transfer System for Gradio/Hugging Face
Uses Gradio's state management and polling for real-time updates
"""

import gradio as gr
import logging
import uuid
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GradioAgentTransfer:
    """Agent transfer system optimized for Gradio"""
    
    def __init__(self, neo4j_handler):
        self.neo4j = neo4j_handler
        
        # Transfer queue: List of pending transfers
        self.transfer_queue = []
        
        # Active transfers: {session_id: agent_data}
        self.active_transfers = {}
        
        # Message queues: {session_id: queue.Queue}
        self.message_queues = defaultdict(queue.Queue)
        
        # Typing status: {session_id: {'customer': bool, 'agent': bool}}
        self.typing_status = defaultdict(lambda: {'customer': False, 'agent': False})
        
        # Agent pool
        self.agent_pool = self._initialize_agents()
        
        # Simulated agent responses (for demo)
        self.agent_simulator = AgentSimulator()
        
        logger.info("✅ Gradio Agent Transfer System initialized")
    
    def _initialize_agents(self) -> List[Dict]:
        """Initialize available agents"""
        return [
            {
                'agent_id': 'AGENT-001',
                'name': 'Amit Sarkar',
                'department': 'Sales',
                'status': 'available',
                'specialization': ['luxury_vehicles', 'financing'],
                'avatar': '👩‍💼'
            },
            {
                'agent_id': 'AGENT-002',
                'name': 'Rethabile S',
                'department': 'Technical Support',
                'status': 'available',
                'specialization': ['technical_issues', 'product_features'],
                'avatar': '👨‍💻'
            },
            {
                'agent_id': 'AGENT-003',
                'name': 'Anti colony Expert',
                'department': 'Customer Service',
                'status': 'available',
                'specialization': ['complaints', 'general_support'],
                'avatar': '👩‍💼'
            },
            {
                'agent_id': 'AGENT-004',
                'name': 'Ragu Anti colony',
                'department': 'Manager',
                'status': 'available',
                'specialization': ['escalations', 'complaints', 'vip_customers'],
                'avatar': '👨‍💼'
            }
        ]
    
    def request_transfer(self,
                        session_id: str,
                        reason: str,
                        user_email: str,
                        conversation_history: List[Dict],
                        user_context: Dict,
                        priority: str = 'normal') -> Tuple[str, Dict]:
        """
        Request agent transfer (Gradio-compatible)
        
        Returns:
            Tuple of (response_html, transfer_state)
        """
        try:
            logger.info(f"🔄 Transfer requested - Session: {session_id}")
            
            transfer_id = f"TRF-{uuid.uuid4().hex[:8].upper()}"
            
            # Find available agent
            agent = self._assign_agent(reason, priority)
            
            if not agent:
                return self._queue_transfer(transfer_id, session_id, reason, user_email)
            
            # Create transfer record
            transfer_data = {
                'transfer_id': transfer_id,
                'session_id': session_id,
                'user_email': user_email,
                'reason': reason,
                'priority': priority,
                'agent': agent,
                'conversation_history': conversation_history,
                'user_context': user_context,
                'created_at': datetime.now().isoformat(),
                'status': 'connected'
            }
            
            # Store in active transfers
            self.active_transfers[session_id] = transfer_data
            
            # Update agent status
            self._update_agent_status(agent['agent_id'], 'busy')
            
            # Save to Neo4j
            self._save_transfer_to_neo4j(transfer_data)
            
            # Generate connection UI
            response_html = self._generate_connection_ui(agent, transfer_id, conversation_history)
            
            # Auto-send agent greeting
            threading.Thread(
                target=self._send_delayed_agent_greeting,
                args=(session_id, agent),
                daemon=True
            ).start()
            
            logger.info(f"✅ Transfer connected - Agent: {agent['name']}")
            
            return response_html, transfer_data
            
        except Exception as e:
            logger.error(f"❌ Transfer failed: {e}", exc_info=True)
            return self._error_response(str(e)), {}
    
    def _assign_agent(self, reason: str, priority: str) -> Optional[Dict]:
        """Assign best available agent"""
        available = [a for a in self.agent_pool if a['status'] == 'available']
        
        if not available:
            return None
        
        # For urgent, prefer managers
        if priority == 'urgent':
            managers = [a for a in available if a['department'] == 'Manager']
            if managers:
                return managers[0]
        
        # Match by specialization
        specialization_map = {
            'escalation': 'escalations',
            'complaint': 'complaints',
            'severe_negative_sentiment': 'complaints',
            'repeated_negative_feedback': 'complaints',
            'multiple_failures': 'technical_issues',
            'financing': 'financing',
            'technical': 'technical_issues',
            'sales': 'luxury_vehicles',
            'general': 'general_support',
            'customer_request': 'general_support'
        }
        
        required_spec = specialization_map.get(reason.lower(), 'general_support')
        # Filter available agents
        available = [a for a in self.agent_pool if a['status'] == 'available']
    
        if not available:
            logger.warning("⚠️ No agents available - queuing transfer")
            return None
    
        # 👉 URGENT PRIORITY: Always route to manager
        if priority == 'urgent':
            managers = [a for a in available if a['department'] == 'Manager']
            if managers:
                logger.info(f"🚨 URGENT: Assigned manager '{managers[0]['name']}' for {reason}")
                return managers[0]
            # Fallback to senior agents if no manager
            senior = [a for a in available if 'escalations' in a['specialization']]
            if senior:
                logger.warning(f"⚠️ URGENT: No manager available, assigned senior agent '{senior[0]['name']}'")
                return senior[0]
    
        # 👉 HIGH PRIORITY: Prefer senior agents or specialized staff
        if priority == 'high':
            # Try to find experienced agents (those with 'escalations' or 'complaints')
            experienced = [a for a in available 
                          if 'escalations' in a['specialization'] or 'complaints' in a['specialization']]
            if experienced:
                logger.info(f"⚠️ HIGH: Assigned experienced agent '{experienced[0]['name']}' for {reason}")
                return experienced[0]
    
        # 👉 NORMAL/LOW: Find agents with matching specialization
        specialized = [a for a in available if required_spec in a['specialization']]
    
        if specialized:
            # Sort by workload if tracking (for now, just return first)
            selected = specialized[0]
            logger.info(f"✅ NORMAL: Assigned specialized agent '{selected['name']}' ({required_spec}) for {reason}")
            return selected
    
        # 👉 FALLBACK: Any available agent
        fallback = available[0]
        logger.info(f"ℹ️ FALLBACK: No specialized agent, assigned '{fallback['name']}' for {reason}")
        return fallback
    
    def _update_agent_status(self, agent_id: str, status: str):
        """Update agent status"""
        for agent in self.agent_pool:
            if agent['agent_id'] == agent_id:
                agent['status'] = status
                break
    
    def _send_delayed_agent_greeting(self, session_id: str, agent: Dict):
        """Send agent greeting after delay (simulates typing)"""
        time.sleep(2.5)  # Typing delay
        
        greeting = self.agent_simulator.get_greeting(agent['name'])
        
        # Add to message queue
        self.message_queues[session_id].put({
            'from': 'agent',
            'agent_name': agent['name'],
            'avatar': agent['avatar'],
            'content': greeting,
            'timestamp': datetime.now().isoformat()
        })
    
    def _generate_connection_ui(self, agent: Dict, transfer_id: str, history: List) -> str:
        """Generate transfer connection UI"""
        
        # Format conversation history summary
        history_summary = ""
        if history:
            last_messages = history[-5:]
            history_items = []
            for msg in last_messages:
                role = "You" if msg.get('role') == 'user' else "Bot"
                content = msg.get('message', '')[:100]
                history_items.append(f"<li><strong>{role}:</strong> {content}...</li>")
            history_summary = f"""
<div style='margin: 15px 0; padding: 15px; background: #f9fafb; border-radius: 8px; border-left: 4px solid #3b82f6;'>
    <p style='margin: 0 0 10px 0; font-weight: 600; color: #1f2937;'>📋 Conversation History Shared</p>
    <ul style='margin: 0; padding-left: 20px; font-size: 0.9em; color: #6b7280;'>
        {"".join(history_items)}
    </ul>
</div>
"""
        
        return f"""
<div style='padding: 25px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            border-radius: 16px; color: white; margin: 20px 0; box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            animation: slideIn 0.5s ease-out;'>
    <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 15px;'>
        <div style='font-size: 3em;'>{agent['avatar']}</div>
        <div>
            <h3 style='margin: 0; font-size: 1.4em; font-weight: 600;'>
                ✅ Connected to Human Agent
            </h3>
            <p style='margin: 5px 0 0 0; opacity: 0.95; font-size: 0.95em;'>
                You're now speaking with a real person
            </p>
        </div>
    </div>
    
    <div style='padding: 20px; background: rgba(255,255,255,0.15); border-radius: 12px; margin: 15px 0;
                backdrop-filter: blur(10px);'>
        <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;'>
            <div>
                <p style='margin: 0; font-size: 1.2em; font-weight: 600;'>
                    {agent['name']}
                </p>
                <p style='margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.9;'>
                    {agent['department']} • {agent['agent_id']}
                </p>
            </div>
            <div style='background: rgba(255,255,255,0.3); padding: 5px 12px; border-radius: 20px; font-size: 0.85em;'>
                🟢 Online
            </div>
        </div>
        <p style='margin: 10px 0 0 0; font-size: 0.9em; opacity: 0.9;'>
            <strong>Specializes in:</strong> {', '.join(agent['specialization'][:2])}
        </p>
    </div>
    
    {history_summary}
    
    <div style='padding: 15px; background: rgba(251, 191, 36, 0.2); border-left: 4px solid #fbbf24; 
                border-radius: 8px; margin: 15px 0;'>
        <p style='margin: 0; font-size: 0.9em;'>
            ⏱️ <strong>{agent['name']}</strong> is reviewing your conversation and will respond shortly...
        </p>
    </div>
    
    <div style='margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2);'>
        <p style='margin: 0; font-size: 0.85em; opacity: 0.85;'>
            Transfer ID: <code style='background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 4px;'>{transfer_id}</code>
        </p>
    </div>
</div>

<style>
@keyframes slideIn {{
    from {{
        opacity: 0;
        transform: translateY(-20px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0);
    }}
}}
</style>
"""
    
    def get_agent_response(self, session_id: str, user_message: str) -> Tuple[str, bool]:
        """
        Get agent response for user message
        
        Returns:
            Tuple of (agent_response_html, is_typing)
        """
        if session_id not in self.active_transfers:
            return "", False
        
        transfer = self.active_transfers[session_id]
        agent = transfer['agent']
        
        # Simulate agent thinking/typing
        self.typing_status[session_id]['agent'] = True
        
        # Generate agent response (simulate delay in separate thread)
        threading.Thread(
            target=self._generate_agent_response_async,
            args=(session_id, user_message, agent),
            daemon=True
        ).start()
        
        # Return typing indicator
        typing_html = f"""
<div style='padding: 15px; background: #f3f4f6; border-radius: 12px; margin: 10px 0; 
            display: flex; align-items: center; gap: 10px; border-left: 4px solid #10b981;'>
    <div style='font-size: 1.5em;'>{agent['avatar']}</div>
    <div>
        <p style='margin: 0; font-weight: 600; color: #059669;'>{agent['name']}</p>
        <div style='display: flex; gap: 4px; margin-top: 5px;'>
            <div style='width: 8px; height: 8px; background: #6b7280; border-radius: 50%; 
                        animation: typing 1.4s infinite;'></div>
            <div style='width: 8px; height: 8px; background: #6b7280; border-radius: 50%; 
                        animation: typing 1.4s infinite 0.2s;'></div>
            <div style='width: 8px; height: 8px; background: #6b7280; border-radius: 50%; 
                        animation: typing 1.4s infinite 0.4s;'></div>
        </div>
    </div>
</div>

<style>
@keyframes typing {{
    0%, 60%, 100% {{ transform: translateY(0); opacity: 1; }}
    30% {{ transform: translateY(-8px); opacity: 0.7; }}
}}
</style>
"""
        
        return typing_html, True
    
    def _generate_agent_response_async(self, session_id: str, user_message: str, agent: Dict):
        """Generate agent response asynchronously"""
        # Simulate thinking time
        time.sleep(random.uniform(2.0, 4.0))
        
        # Generate response
        response = self.agent_simulator.generate_response(
            user_message=user_message,
            context=self.active_transfers[session_id].get('reason', 'general'),
            agent_name=agent['name']
        )
        
        # Add to message queue
        self.message_queues[session_id].put({
            'from': 'agent',
            'agent_name': agent['name'],
            'avatar': agent['avatar'],
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Stop typing
        self.typing_status[session_id]['agent'] = False
    
    def check_for_messages(self, session_id: str) -> Optional[str]:
        """
        Check for new agent messages (for polling)
        
        Returns:
            HTML of new message or None
        """
        if session_id not in self.message_queues:
            return None
        
        try:
            # Non-blocking get
            message = self.message_queues[session_id].get_nowait()
            
            # Format message
            return self._format_agent_message(message)
            
        except queue.Empty:
            return None
    
    def _format_agent_message(self, message: Dict) -> str:
        """Format agent message as HTML"""
        timestamp = datetime.fromisoformat(message['timestamp'])
        time_str = timestamp.strftime("%I:%M %p")
        
        return f"""
<div style='padding: 15px; background: #e0f2fe; border-radius: 12px; margin: 10px 0; 
            border-left: 4px solid #0284c7; animation: fadeIn 0.3s ease-in;'>
    <div style='display: flex; align-items: start; gap: 10px;'>
        <div style='font-size: 1.5em; flex-shrink: 0;'>{message['avatar']}</div>
        <div style='flex: 1;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                <p style='margin: 0; font-weight: 600; color: #0c4a6e;'>{message['agent_name']}</p>
                <span style='font-size: 0.8em; color: #64748b;'>{time_str}</span>
            </div>
            <p style='margin: 0; color: #1e293b; line-height: 1.6; white-space: pre-wrap;'>
                {message['content']}
            </p>
        </div>
    </div>
</div>

<style>
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
</style>
"""
    
    def end_transfer(self, session_id: str, ended_by: str = 'customer') -> str:
        """End agent transfer"""
        if session_id not in self.active_transfers:
            return ""
        
        transfer = self.active_transfers[session_id]
        agent = transfer['agent']
        
        # Update agent status
        self._update_agent_status(agent['agent_id'], 'available')
        
        # Update Neo4j
        self._complete_transfer_in_neo4j(transfer['transfer_id'], ended_by)
        
        # Remove from active transfers
        del self.active_transfers[session_id]
        
        # Clear message queue
        if session_id in self.message_queues:
            del self.message_queues[session_id]
        
        logger.info(f"✅ Transfer ended - Session: {session_id}, By: {ended_by}")
        
        return f"""
<div style='padding: 20px; background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>✅ Chat Session Ended</h3>
    <p style='margin: 0; opacity: 0.95; line-height: 1.6;'>
        Thank you for speaking with <strong>{agent['name']}</strong>. 
        I'm back to assist you with any other questions!
    </p>
    <p style='margin: 10px 0 0 0; font-size: 0.9em; opacity: 0.85;'>
        Rate your experience: 
        <span style='cursor: pointer; margin-left: 10px;'>⭐⭐⭐⭐⭐</span>
    </p>
</div>
"""
    
    def is_agent_active(self, session_id: str) -> bool:
        """Check if agent is active for session"""
        return session_id in self.active_transfers
    
    def _save_transfer_to_neo4j(self, transfer_data: Dict):
        """Save transfer to Neo4j"""
        try:
            query = """
            CREATE (t:Transfer {
                transfer_id: $transfer_id,
                session_id: $session_id,
                user_email: $user_email,
                reason: $reason,
                priority: $priority,
                agent_id: $agent_id,
                agent_name: $agent_name,
                created_at: datetime($created_at),
                status: 'active'
            })
            
            WITH t
            MATCH (c:Conversation {session_id: $session_id})
            CREATE (c)-[:TRANSFERRED_TO]->(t)
            
            RETURN t.transfer_id
            """
            
            self.neo4j.execute_with_retry(query, {
                'transfer_id': transfer_data['transfer_id'],
                'session_id': transfer_data['session_id'],
                'user_email': transfer_data['user_email'],
                'reason': transfer_data['reason'],
                'priority': transfer_data['priority'],
                'agent_id': transfer_data['agent']['agent_id'],
                'agent_name': transfer_data['agent']['name'],
                'created_at': transfer_data['created_at']
            })
            
        except Exception as e:
            logger.error(f"Failed to save transfer: {e}")
    
    def _complete_transfer_in_neo4j(self, transfer_id: str, ended_by: str):
        """Mark transfer as completed in Neo4j"""
        try:
            query = """
            MATCH (t:Transfer {transfer_id: $transfer_id})
            SET t.status = 'completed',
                t.ended_at = datetime(),
                t.ended_by = $ended_by
            RETURN t
            """
            
            self.neo4j.execute_with_retry(query, {
                'transfer_id': transfer_id,
                'ended_by': ended_by
            })
            
        except Exception as e:
            logger.error(f"Failed to complete transfer: {e}")
    
    def _queue_transfer(self, transfer_id: str, session_id: str, reason: str, user_email: str) -> Tuple[str, Dict]:
        """Queue transfer when no agents available"""
        self.transfer_queue.append({
            'transfer_id': transfer_id,
            'session_id': session_id,
            'reason': reason,
            'user_email': user_email
        })
        
        position = len(self.transfer_queue)
        wait_time = position * 30  # 30 seconds per position
        
        html = f"""
<div style='padding: 20px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
            border-radius: 12px; color: white; margin: 15px 0;'>
    <h3 style='margin: 0 0 10px 0;'>⏳ You're in Queue</h3>
    <p style='margin: 0 0 15px 0; opacity: 0.95;'>
        All agents are currently busy helping other customers.
    </p>
    <div style='padding: 15px; background: rgba(255,255,255,0.15); border-radius: 8px;'>
        <p style='margin: 0; font-size: 1.1em;'><strong>Queue Position:</strong> #{position}</p>
        <p style='margin: 5px 0 0 0; font-size: 0.9em;'>
            <strong>Estimated Wait:</strong> ~{wait_time} seconds
        </p>
    </div>
</div>
"""
        
        return html, {}
    
    def _error_response(self, error: str) -> str:
        """Generate error response"""
        return f"""
<div style='padding: 20px; background: #fee2e2; border-left: 4px solid #ef4444; 
            border-radius: 8px; margin: 15px 0;'>
    <p style='margin: 0; color: #991b1b; font-weight: 600;'>❌ Transfer Failed</p>
    <p style='margin: 5px 0 0 0; color: #7f1d1d; font-size: 0.9em;'>{error}</p>
</div>
"""


class AgentSimulator:
    """Simulates realistic agent responses"""
    
    def __init__(self):
        self.greetings = [
            "Hi! I've reviewed your conversation and I'm here to help. What can I assist you with?",
            "Hello! I can see what's been happening. Let me help you resolve this.",
            "Good day! I have your full conversation context. How can I assist you today?"
        ]
        
        self.empathy_phrases = [
            "I completely understand your frustration.",
            "I can see why you're concerned about this.",
            "That's definitely not the experience we want you to have.",
            "I hear you, and I apologize for the inconvenience."
        ]
        
        self.solutions = [
            "Here's what I can do to help you with this:",
            "Let me offer you a solution that should resolve this:",
            "Based on your situation, here's what we can do:",
            "I've found the best way to address this for you:"
        ]
    
    def get_greeting(self, agent_name: str) -> str:
        """Get agent greeting"""
        return random.choice(self.greetings)
    
    def generate_response(self, user_message: str, context: str, agent_name: str) -> str:
        """Generate contextual agent response"""
        response_parts = []
        
        # Add empathy for complaints
        if any(word in user_message.lower() for word in ['not happy', 'bad', 'wrong', 'terrible', 'disappointed']):
            response_parts.append(random.choice(self.empathy_phrases))
        
        # Add solution
        response_parts.append(random.choice(self.solutions))
        
        # Add specific solution based on context
        if 'vehicle' in user_message.lower() or 'car' in user_message.lower():
            response_parts.append(
                "I can help you find the perfect vehicle that matches your needs and budget. "
                "I'll also make sure you get our best pricing and financing options. I have saved your number and email, will connect you over the call. You can now End the session by clicking the button"
            )
        elif 'price' in user_message.lower() or 'cost' in user_message.lower():
            response_parts.append(
                "Let me check our current promotions and special offers for you.I have saved your number and email, will connect you over the call. You can now End the session by clicking the button "
                "I may be able to get you a better deal than what you saw initially.I have saved your number and email, will connect you over the call. You can now End the session by clicking the button"
            )
        elif 'not happy' in user_message.lower() or 'sad' in user_message.lower() or 'disappoint' in user_message.lower() or 'fustrating' in user_message.lower():
            response_parts.append(
                "I understand you are disappointed or not happy with our services.I have saved your number and email, will connect you over the call. You can now End the session by clicking the button "
                "I may be able to get you a better deal than what you saw initially.I have saved your number and email, will connect you over the call. You can now End the session by clicking the button"
            )
        elif 'thanks' in user_message.lower() or 'bye' in user_message.lower() or 'ok' in user_message.lower() or 'fine' in user_message.lower() or 'thank you' in user_message.lower():
            response_parts.append(
                "Thank you, see you again."
                "I have saved your number and email, will connect you over the call. You can now End the session by clicking the button"
            )
        else:
            response_parts.append(
                "I'll personally ensure this gets resolved for you right away. "
                "Is there anything specific you'd like me to prioritize?"
                "I have saved your number and email, will connect you over the call. You can now End the session by clicking the button"
                "for now Bye! see you again!"
            )
        
        return "\n\n".join(response_parts)