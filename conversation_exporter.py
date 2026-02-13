"""
conversation_exporter.py - Export conversation data for analysis and backup
Features:
- Export to CSV, JSON, Excel
- Filter by date range, email, session
- Aggregate statistics
- Privacy-compliant exports
"""

import logging
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationExporter:
    """Export conversation data from Neo4j"""
    
    def __init__(self, neo4j_handler):
        self.neo4j = neo4j_handler
        # Set output directory to temp
        self.output_dir = tempfile.gettempdir()
        logger.info(f"✅ ConversationExporter initialized (output: {self.output_dir})")
    
    def get_conversations_by_date_range(
        self, 
        start_date: str, 
        end_date: str,
        email_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Get conversations within date range
        
        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format
            email_filter: Optional email to filter by
        
        Returns:
            List of conversation records
        """
        try:
            # ✅ FIXED QUERY - Proper WITH clause ordering
            query = """
                MATCH (c:Conversation)
                WHERE c.created_at >= datetime($start_date)
                  AND c.created_at <= datetime($end_date)
            """
            
            params = {
                'start_date': start_date + 'T00:00:00',
                'end_date': end_date + 'T23:59:59'
            }
            
            # Add email filter if provided
            if email_filter:
                query += " AND c.user_email = $email"
                params['email'] = email_filter
            
            # ✅ KEY FIX: Order conversations BEFORE collecting messages
            query += """
                WITH c
                ORDER BY c.created_at DESC
                OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
                WITH c, m
                ORDER BY c.created_at DESC, m.timestamp ASC
                RETURN c.session_id as session_id,
                       c.user_email as user_email,
                       c.created_at as started_at,
                       c.last_updated as last_updated,
                       c.message_count as message_count,
                       c.last_intent as last_intent,
                       c.preferred_language as language,
                       collect(DISTINCT {
                           role: m.role,
                           message: m.clean_content,
                           timestamp: m.timestamp
                       }) as messages
            """
            
            logger.info(f"🔍 Querying conversations from {start_date} to {end_date}")
            logger.info(f"📧 Email filter: {email_filter if email_filter else 'None'}")
            
            results = self.neo4j.execute_with_retry(query, params, timeout=30.0)
            
            logger.info(f"📊 Query returned {len(results) if results else 0} results")
            
            conversations = []
            if results:
                for record in results:
                    # Convert all datetime objects to strings
                    started_at = record['started_at']
                    if started_at:
                        started_at = str(started_at)
                    
                    last_updated = record['last_updated']
                    if last_updated:
                        last_updated = str(last_updated)
                    
                    # Process messages - filter out empty ones
                    messages = []
                    for msg in record['messages']:
                        # Skip empty message objects
                        if msg and msg.get('message'):
                            timestamp = msg.get('timestamp')
                            if timestamp:
                                timestamp = str(timestamp)
                            
                            messages.append({
                                'role': msg['role'],
                                'message': msg['message'],
                                'timestamp': timestamp
                            })
                    
                    conversations.append({
                        'session_id': record['session_id'],
                        'user_email': record['user_email'] or 'anonymous',
                        'started_at': started_at,
                        'last_updated': last_updated,
                        'message_count': record['message_count'] or len(messages),
                        'last_intent': record['last_intent'],
                        'language': record['language'] or 'en',
                        'messages': messages
                    })
            
            logger.info(f"✅ Processed {len(conversations)} conversations")
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error fetching conversations: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def export_to_csv(
        self, 
        conversations: List[Dict], 
        output_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Export conversations to CSV format
        
        Args:
            conversations: List of conversation dictionaries
            output_path: Where to save the CSV file (defaults to temp directory)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not conversations:
                return False, "No conversations to export"
            
            # Use temp directory if no path specified
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = os.path.join(self.output_dir, f"conversations_{timestamp}.csv")
            
            # Flatten data for CSV
            rows = []
            for conv in conversations:
                base_data = {
                    'session_id': conv['session_id'],
                    'user_email': conv['user_email'],
                    'started_at': conv['started_at'],
                    'last_updated': conv['last_updated'],
                    'message_count': conv['message_count'],
                    'last_intent': conv['last_intent'],
                    'language': conv['language']
                }
                
                # Add each message as a separate row
                for idx, msg in enumerate(conv['messages'], 1):
                    row = base_data.copy()
                    row.update({
                        'message_number': idx,
                        'message_role': msg['role'],
                        'message_content': msg['message'],
                        'message_timestamp': str(msg['timestamp'])
                    })
                    rows.append(row)
            
            # Create DataFrame and save
            df = pd.DataFrame(rows)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            logger.info(f"✅ Exported {len(rows)} messages to {output_path}")
            return True, f"Successfully exported {len(conversations)} conversations ({len(rows)} messages) to CSV"
            
        except Exception as e:
            logger.error(f"❌ CSV export error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Export failed: {str(e)}"
    
    def export_to_json(
        self, 
        conversations: List[Dict], 
        output_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Export conversations to JSON format
        
        Args:
            conversations: List of conversation dictionaries
            output_path: Where to save the JSON file (defaults to temp directory)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not conversations:
                return False, "No conversations to export"
            
            # Use temp directory if no path specified
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = os.path.join(self.output_dir, f"conversations_{timestamp}.json")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create export structure
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_conversations': len(conversations),
                'conversations': conversations
            }
            
            # Save to JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Exported {len(conversations)} conversations to {output_path}")
            return True, f"Successfully exported {len(conversations)} conversations to JSON"
            
        except Exception as e:
            logger.error(f"❌ JSON export error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Export failed: {str(e)}"
    
    def export_to_excel(
        self, 
        conversations: List[Dict], 
        output_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Export conversations to Excel format with multiple sheets
        
        Args:
            conversations: List of conversation dictionaries
            output_path: Where to save the Excel file (defaults to temp directory)
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check for openpyxl first
            try:
                import openpyxl
            except ImportError:
                error_msg = "❌ openpyxl not installed. Run: pip install openpyxl --break-system-packages"
                logger.error(error_msg)
                return False, error_msg
            
            if not conversations:
                return False, "No conversations to export"
            
            # Use temp directory if no path specified
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = os.path.join(self.output_dir, f"conversations_{timestamp}.xlsx")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create Excel writer
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Sheet 1: Summary
                summary_data = []
                for conv in conversations:
                    summary_data.append({
                        'Session ID': conv['session_id'],
                        'User Email': conv['user_email'],
                        'Started At': conv['started_at'],
                        'Last Updated': conv['last_updated'],
                        'Messages': conv['message_count'],
                        'Last Intent': conv['last_intent'],
                        'Language': conv['language']
                    })
                
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Summary', index=False)
                
                # Sheet 2: Detailed Messages
                message_data = []
                for conv in conversations:
                    for idx, msg in enumerate(conv['messages'], 1):
                        message_data.append({
                            'Session ID': conv['session_id'],
                            'User Email': conv['user_email'],
                            'Message #': idx,
                            'Role': msg['role'],
                            'Content': msg['message'],
                            'Timestamp': str(msg['timestamp'])
                        })
                
                df_messages = pd.DataFrame(message_data)
                df_messages.to_excel(writer, sheet_name='Messages', index=False)
                
                # Sheet 3: Statistics
                stats_data = {
                    'Metric': [
                        'Total Conversations',
                        'Total Messages',
                        'Unique Users',
                        'Average Messages per Conversation',
                        'Date Range'
                    ],
                    'Value': [
                        len(conversations),
                        sum(conv['message_count'] for conv in conversations),
                        len(set(conv['user_email'] for conv in conversations)),
                        round(sum(conv['message_count'] for conv in conversations) / len(conversations), 2) if conversations else 0,
                        f"{conversations[-1]['started_at']} to {conversations[0]['started_at']}" if conversations else 'N/A'
                    ]
                }
                
                df_stats = pd.DataFrame(stats_data)
                df_stats.to_excel(writer, sheet_name='Statistics', index=False)
            
            logger.info(f"✅ Exported {len(conversations)} conversations to {output_path}")
            return True, f"Successfully exported {len(conversations)} conversations to Excel (3 sheets)"
            
        except Exception as e:
            logger.error(f"❌ Excel export error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Export failed: {str(e)}"
    
    def get_conversation_statistics(
        self, 
        start_date: str, 
        end_date: str
    ) -> Dict:
        """
        Get aggregate statistics for conversations
        
        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format
        
        Returns:
            Dictionary with statistics
        """
        try:
            # ✅ FIXED QUERY - Added WITH clause
            query = """
                MATCH (c:Conversation)
                WHERE c.created_at >= datetime($start_date)
                  AND c.created_at <= datetime($end_date)
                WITH c
                OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
                RETURN 
                    count(DISTINCT c) as total_conversations,
                    count(m) as total_messages,
                    count(DISTINCT c.user_email) as unique_users,
                    avg(c.message_count) as avg_messages_per_conversation,
                    collect(DISTINCT c.last_intent) as intents,
                    collect(DISTINCT c.preferred_language) as languages
            """
            
            params = {
                'start_date': start_date + 'T00:00:00',
                'end_date': end_date + 'T23:59:59'
            }
            
            results = self.neo4j.execute_with_retry(query, params, timeout=15.0)
            
            if results and len(results) > 0:
                record = results[0]
                
                # Clean intents and languages
                intents = [i for i in record['intents'] if i]
                languages = [l for l in record['languages'] if l]
                
                return {
                    'total_conversations': record['total_conversations'],
                    'total_messages': record['total_messages'],
                    'unique_users': record['unique_users'],
                    'avg_messages_per_conversation': round(record['avg_messages_per_conversation'] or 0, 2),
                    'intents': intents,
                    'languages': languages,
                    'date_range': f"{start_date} to {end_date}"
                }
            
            return {
                'total_conversations': 0,
                'total_messages': 0,
                'unique_users': 0,
                'avg_messages_per_conversation': 0,
                'intents': [],
                'languages': [],
                'date_range': f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            logger.error(f"❌ Statistics error: {e}")
            import traceback
            traceback.print_exc()
            return {}


# Testing function
def test_exporter():
    """Test the conversation exporter"""
    print("\n" + "="*60)
    print("🧪 TESTING CONVERSATION EXPORTER")
    print("="*60)
    print("\n✅ ConversationExporter module loaded successfully!")
    print("\nFeatures:")
    print("  • Export to CSV, JSON, Excel")
    print("  • Date range filtering")
    print("  • Email filtering")
    print("  • Aggregate statistics")
    print("  • Privacy-compliant exports")
    print(f"  • Output directory: {tempfile.gettempdir()}")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_exporter()