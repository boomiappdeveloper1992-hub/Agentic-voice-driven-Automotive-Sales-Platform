"""
sentiment_analytics.py - Sentiment Analysis Dashboard Backend
Tracks customer sentiment from chat conversations
"""

import logging
from typing import Dict, Optional, Tuple, List
import plotly.graph_objects as go
from datetime import datetime

logger = logging.getLogger(__name__)


def get_sentiment_analysis(neo4j_connection, email: str = "", phone: str = ""):
    """
    Get comprehensive sentiment analysis for a customer
    
    Args:
        neo4j_connection: Neo4j database connection
        email: Customer email to search
        phone: Customer phone to search
    
    Returns:
        Tuple of (user_profile_html, sentiment_overview_html, timeline_plot, conversations_html)
    """
    try:
        # Validate input
        email = email.strip()
        phone = phone.strip()
        
        if not email and not phone:
            return (
                _empty_state("⚠️ Please enter email or phone number to search"),
                "",
                None,
                ""
            )
        
        logger.info(f"🔍 Searching sentiment data for: email={email}, phone={phone}")
        
        # ═══════════════════════════════════════════════════════════
        # ✅ QUERY 1: Get all conversations for this customer
        # ═══════════════════════════════════════════════════════════
        query = """
            MATCH (c:Conversation)
            WHERE ($email <> '' AND c.user_email = $email)
               OR ($phone <> '' AND EXISTS {
                   MATCH (td:TestDrive)
                   WHERE td.customer_phone = $phone 
                     AND td.customer_email = c.user_email
               })
            OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
            WHERE m.role = 'user' AND m.sentiment IS NOT NULL
            WITH c, 
                 c.user_email as email,
                 c.session_id as session_id,
                 c.created_at as conversation_start,
                 c.avg_sentiment_score as avg_sentiment,
                 c.positive_count as positive_count,
                 c.negative_count as negative_count,
                 c.severe_negative_count as severe_negative_count,
                 c.total_user_messages as total_messages,
                 collect({
                     message: m.clean_content,
                     sentiment: m.sentiment,
                     score: m.sentiment_score,
                     timestamp: m.timestamp
                 }) as messages
            ORDER BY c.created_at DESC
            RETURN email, session_id, conversation_start, avg_sentiment,
                   positive_count, negative_count, severe_negative_count,
                   total_messages, messages
            LIMIT 10
        """
        
        results = neo4j_connection.execute_with_retry(
            query, 
            {'email': email, 'phone': phone},
            timeout=15.0
        )
        
        if not results or len(results) == 0:
            return (
                _empty_state(f"❌ No conversations found for: {email or phone}"),
                "",
                None,
                ""
            )
        
        logger.info(f"✅ Found {len(results)} conversations")
        
        # ═══════════════════════════════════════════════════════════
        # ✅ QUERY 2: Get customer details from TestDrive
        # ═══════════════════════════════════════════════════════════
        user_email = results[0]['email']
        
        user_query = """
            MATCH (td:TestDrive)
            WHERE td.customer_email = $email
            RETURN td.customer_name as name,
                   td.customer_phone as phone,
                   td.customer_email as email
            ORDER BY td.created_at DESC
            LIMIT 1
        """
        
        user_info = neo4j_connection.execute_with_retry(
            user_query,
            {'email': user_email},
            timeout=10.0
        )
        
        # Extract user details
        if user_info and len(user_info) > 0:
            user_name = user_info[0].get('name', 'Unknown Customer')
            user_phone = user_info[0].get('phone', phone or 'N/A')
        else:
            user_name = 'Unknown Customer'
            user_phone = phone or 'N/A'
        
        # ═══════════════════════════════════════════════════════════
        # ✅ CALCULATE OVERALL SENTIMENT METRICS
        # ═══════════════════════════════════════════════════════════
        total_positive = sum(r.get('positive_count', 0) or 0 for r in results)
        total_negative = sum(r.get('negative_count', 0) or 0 for r in results)
        total_severe = sum(r.get('severe_negative_count', 0) or 0 for r in results)
        total_msgs = sum(r.get('total_messages', 0) or 0 for r in results)
        
        # Calculate average sentiment score
        valid_scores = [r.get('avg_sentiment', 0) for r in results if r.get('avg_sentiment') is not None]
        avg_sentiment_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.5
        
        # ═══════════════════════════════════════════════════════════
        # ✅ DETERMINE LEAD STATUS
        # ═══════════════════════════════════════════════════════════
        if total_severe > 0 or avg_sentiment_score < 0.5:
            lead_status = 'cold'
            lead_color = '#ef4444'
            lead_emoji = '❄️'
        elif avg_sentiment_score > 0.5: # and total_positive > total_negative * 2:
            lead_status = 'hot'
            lead_color = '#10b981'
            lead_emoji = '🔥'
        else:
            lead_status = 'warm'
            lead_color = '#f59e0b'
            lead_emoji = '🌡️'
        
        logger.info(f"📊 Lead Status: {lead_status.upper()} | Sentiment: {avg_sentiment_score:.2f}")
        
        # ═══════════════════════════════════════════════════════════
        # ✅ GENERATE UI COMPONENTS
        # ═══════════════════════════════════════════════════════════
        user_profile_html = generate_user_profile_card(
            user_name, user_email, user_phone
        )
        
        sentiment_overview_html = generate_sentiment_overview(
            total_positive, total_negative, total_severe, total_msgs,
            avg_sentiment_score, lead_status, lead_color, lead_emoji
        )
        
        timeline_plot = generate_sentiment_timeline(results)
        
        conversations_html = generate_conversations_list(results)
        
        return (
            user_profile_html,
            sentiment_overview_html,
            timeline_plot,
            conversations_html
        )
        
    except Exception as e:
        logger.error(f"❌ Sentiment analysis error: {e}", exc_info=True)
        return (
            _empty_state(f"❌ Error: {str(e)}"),
            "",
            None,
            ""
        )


def _empty_state(message: str) -> str:
    """Generate empty state HTML"""
    return f"""
<div style='padding: 40px 20px; text-align: center; background: #f9fafb; 
            border-radius: 12px; border: 2px dashed #d1d5db;'>
    <div style='font-size: 3em; margin-bottom: 15px;'>🔍</div>
    <p style='color: #6b7280; font-size: 1.1em; margin: 0;'>{message}</p>
</div>
"""


def generate_user_profile_card(name: str, email: str, phone: str) -> str:
    """Generate user profile card HTML"""
    return f"""
<div style='padding: 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 16px; color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.15);'>
    <div style='text-align: center; margin-bottom: 20px;'>
        <div style='width: 80px; height: 80px; background: rgba(255,255,255,0.2); 
                    border-radius: 50%; margin: 0 auto 15px; display: flex; 
                    align-items: center; justify-content: center; font-size: 2.5em;'>
            👤
        </div>
        <h2 style='margin: 0 0 10px 0; font-size: 1.5em;'>{name}</h2>
        <div style='font-size: 0.9em; opacity: 0.9;'>Customer Profile</div>
    </div>
    
    <div style='background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;'>
        <div style='margin-bottom: 10px; display: flex; align-items: center; gap: 10px;'>
            <span style='font-size: 1.2em;'>📧</span>
            <div style='flex: 1;'>
                <div style='font-size: 0.8em; opacity: 0.8;'>Email Address</div>
                <div style='font-weight: 600; word-break: break-all;'>{email}</div>
            </div>
        </div>
        
        <div style='display: flex; align-items: center; gap: 10px;'>
            <span style='font-size: 1.2em;'>📱</span>
            <div style='flex: 1;'>
                <div style='font-size: 0.8em; opacity: 0.8;'>Phone Number</div>
                <div style='font-weight: 600;'>{phone}</div>
            </div>
        </div>
    </div>
</div>
"""


def generate_sentiment_overview(positive: int, negative: int, severe: int, 
                                total: int, avg_score: float, status: str,
                                color: str, emoji: str) -> str:
    """Generate sentiment overview HTML"""
    
    positive_pct = (positive / total * 100) if total > 0 else 0
    negative_pct = ((negative + severe) / total * 100) if total > 0 else 0
    neutral = total - positive - negative - severe
    neutral_pct = (neutral / total * 100) if total > 0 else 0
    
    return f"""
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb; margin-top: 20px;'>
    <h3 style='margin: 0 0 20px 0; color: #374151;'>📊 Sentiment Overview</h3>
    
    <!-- Lead Status Badge -->
    <div style='text-align: center; margin-bottom: 25px;'>
        <div style='background: {color}; color: white; padding: 15px 30px; 
                    border-radius: 25px; display: inline-block; font-size: 1.2em;
                    box-shadow: 0 4px 12px {color}40;'>
            <span style='font-size: 1.5em; margin-right: 10px;'>{emoji}</span>
            <strong>{status.upper()} LEAD</strong>
        </div>
    </div>
    
    <!-- Sentiment Score -->
    <div style='text-align: center; margin-bottom: 25px;'>
        <div style='font-size: 0.9em; color: #6b7280; margin-bottom: 10px;'>
            Average Sentiment Score
        </div>
        <div style='font-size: 3em; font-weight: 700; color: {color};'>
            {avg_score:.1%}
        </div>
        <div style='width: 200px; height: 8px; background: #e5e7eb; border-radius: 4px; 
                    margin: 15px auto; overflow: hidden;'>
            <div style='width: {avg_score * 100}%; height: 100%; background: {color}; 
                        border-radius: 4px; transition: width 0.3s;'></div>
        </div>
    </div>
    
    <!-- Message Breakdown -->
    <div style='background: #f9fafb; padding: 15px; border-radius: 10px;'>
        <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; text-align: center;'>
            <div>
                <div style='font-size: 2em; color: #10b981;'>😊</div>
                <div style='font-size: 1.5em; font-weight: 700; color: #10b981; margin: 5px 0;'>
                    {positive}
                </div>
                <div style='font-size: 0.85em; color: #6b7280;'>Positive</div>
                <div style='font-size: 0.75em; color: #9ca3af; margin-top: 3px;'>{positive_pct:.1f}%</div>
            </div>
            
            <div>
                <div style='font-size: 2em; color: #6b7280;'>😐</div>
                <div style='font-size: 1.5em; font-weight: 700; color: #6b7280; margin: 5px 0;'>
                    {neutral}
                </div>
                <div style='font-size: 0.85em; color: #6b7280;'>Neutral</div>
                <div style='font-size: 0.75em; color: #9ca3af; margin-top: 3px;'>{neutral_pct:.1f}%</div>
            </div>
            
            <div>
                <div style='font-size: 2em; color: #ef4444;'>😞</div>
                <div style='font-size: 1.5em; font-weight: 700; color: #ef4444; margin: 5px 0;'>
                    {negative + severe}
                </div>
                <div style='font-size: 0.85em; color: #6b7280;'>Negative</div>
                <div style='font-size: 0.75em; color: #9ca3af; margin-top: 3px;'>{negative_pct:.1f}%</div>
            </div>
        </div>
    </div>
    
    <!-- Total Messages -->
    <div style='text-align: center; margin-top: 15px; padding-top: 15px; 
                border-top: 1px solid #e5e7eb;'>
        <div style='font-size: 0.85em; color: #6b7280;'>Total Messages Analyzed</div>
        <div style='font-size: 1.3em; font-weight: 700; color: #374151; margin-top: 5px;'>
            {total}
        </div>
    </div>
    
    {f'''
    <div style="margin-top: 15px; padding: 15px; background: #fee2e2; 
                border-radius: 8px; border-left: 4px solid #ef4444;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.5em;">⚠️</span>
            <div>
                <strong style="color: #991b1b;">Risk Alert</strong>
                <div style="color: #7f1d1d; font-size: 0.9em; margin-top: 3px;">
                    Customer has expressed severe negative sentiment ({severe} messages)
                </div>
            </div>
        </div>
    </div>
    ''' if severe > 0 else ''}
</div>
"""


def generate_sentiment_timeline(conversations: list) -> go.Figure:
    """Generate sentiment timeline plot using Plotly"""
    
    if not conversations:
        # Return empty plot
        fig = go.Figure()
        fig.add_annotation(
            text="No data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        return fig
    
    # Extract data for plotting
    dates = []
    scores = []
    labels = []
    colors = []
    
    for conv in conversations:
        conv_date = conv['conversation_start']
        avg_score = conv.get('avg_sentiment', 0.5)
        
        if avg_score is None:
            avg_score = 0.5
        
        # ✅ FIX: Convert Neo4j DateTime to Python datetime string
        if conv_date is not None:
            # Handle Neo4j DateTime objects
            if hasattr(conv_date, 'to_native'):
                # Neo4j DateTime with to_native() method
                conv_date = conv_date.to_native()
            elif hasattr(conv_date, 'year'):
                # Already a datetime-like object
                pass
            else:
                # String - parse it
                try:
                    from datetime import datetime
                    conv_date = datetime.fromisoformat(str(conv_date).replace('Z', '+00:00'))
                except:
                    conv_date = datetime.now()
        else:
            from datetime import datetime
            conv_date = datetime.now()
        
        dates.append(conv_date)
        scores.append(avg_score)
        
        # Determine label and color
        if avg_score > 0.7:
            labels.append('Positive 😊')
            colors.append('#10b981')
        elif avg_score < 0.3:
            labels.append('Negative 😞')
            colors.append('#ef4444')
        else:
            labels.append('Neutral 😐')
            colors.append('#f59e0b')
    
    # Reverse to show chronological order (oldest first)
    dates = dates[::-1]
    scores = scores[::-1]
    labels = labels[::-1]
    colors = colors[::-1]
    
    # Create plot
    fig = go.Figure()
    
    # Add line trace
    fig.add_trace(go.Scatter(
        x=dates,
        y=scores,
        mode='lines+markers',
        name='Sentiment Score',
        line=dict(color='#667eea', width=3),
        marker=dict(
            size=12, 
            color=scores, 
            colorscale=[[0, '#ef4444'], [0.5, '#f59e0b'], [1, '#10b981']],
            showscale=False,
            line=dict(width=2, color='white')
        ),
        text=labels,
        hovertemplate='<b>%{text}</b><br>Score: %{y:.2f}<br>Date: %{x|%Y-%m-%d %H:%M}<extra></extra>'
    ))
    
    # Add threshold lines
    fig.add_hline(
        y=0.7, 
        line_dash="dash", 
        line_color="rgba(16, 185, 129, 0.3)", 
        annotation_text="Positive Threshold",
        annotation_position="right"
    )
    fig.add_hline(
        y=0.3, 
        line_dash="dash", 
        line_color="rgba(239, 68, 68, 0.3)", 
        annotation_text="Negative Threshold",
        annotation_position="right"
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': "Sentiment Timeline",
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title="Date",
        yaxis_title="Sentiment Score",
        yaxis_range=[0, 1],
        hovermode='closest',
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Arial, sans-serif"),
        margin=dict(l=60, r=60, t=60, b=60)
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    
    return fig


def generate_conversations_list(conversations: list) -> str:
    """Generate conversations list HTML"""
    
    html = """
<div style='padding: 20px; background: white; border-radius: 12px; 
            border: 2px solid #e5e7eb;'>
    <h3 style='margin: 0 0 20px 0; color: #374151;'>💬 Conversation History</h3>
    <div style='font-size: 0.9em; color: #6b7280; margin-bottom: 15px;'>
        Showing most recent conversations (up to 10)
    </div>
"""
    
    for idx, conv in enumerate(conversations, 1):
        session_id = conv['session_id']
        conv_date = conv['conversation_start']
        
        # ✅ FIX: Format date properly
        if conv_date is not None:
            # Handle Neo4j DateTime objects
            if hasattr(conv_date, 'to_native'):
                conv_date = conv_date.to_native()
            elif hasattr(conv_date, 'strftime'):
                # Already a Python datetime
                pass
            else:
                # String - parse it
                try:
                    from datetime import datetime
                    conv_date = datetime.fromisoformat(str(conv_date).replace('Z', '+00:00'))
                except:
                    conv_date = datetime.now()
            
            formatted_date = conv_date.strftime('%Y-%m-%d %H:%M')
        else:
            formatted_date = "Unknown date"
        
        avg_sentiment = conv.get('avg_sentiment', 0.5)
        if avg_sentiment is None:
            avg_sentiment = 0.5
        
        messages = conv.get('messages', [])
        total_msgs = conv.get('total_messages', len(messages))
        
        # Determine sentiment color and label
        if avg_sentiment > 0.7:
            sentiment_color = '#10b981'
            sentiment_label = 'Positive 😊'
            sentiment_bg = '#d1fae5'
        elif avg_sentiment < 0.3:
            sentiment_color = '#ef4444'
            sentiment_label = 'Negative 😞'
            sentiment_bg = '#fee2e2'
        else:
            sentiment_color = '#f59e0b'
            sentiment_label = 'Neutral 😐'
            sentiment_bg = '#fef3c7'
        
        html += f"""
    <div style='margin-bottom: 15px; padding: 15px; background: {sentiment_bg}; 
                border-radius: 10px; border-left: 4px solid {sentiment_color};'>
        <div style='display: flex; justify-content: space-between; align-items: start; 
                    margin-bottom: 10px; flex-wrap: wrap; gap: 10px;'>
            <div style='flex: 1; min-width: 200px;'>
                <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 5px;'>
                    <strong style='color: #374151; font-size: 0.95em;'>
                        Conversation #{idx}
                    </strong>
                </div>
                <div style='font-size: 0.85em; color: #6b7280;'>
                    📅 {formatted_date}
                </div>
                <div style='font-size: 0.8em; color: #9ca3af; margin-top: 3px;'>
                    Session: {session_id[:20]}...
                </div>
            </div>
            <div style='text-align: right;'>
                <div style='background: {sentiment_color}; color: white; padding: 6px 12px; 
                            border-radius: 12px; font-size: 0.85em; display: inline-block;
                            box-shadow: 0 2px 4px {sentiment_color}40;'>
                    {sentiment_label}
                </div>
                <div style='font-size: 0.75em; color: #6b7280; margin-top: 5px;'>
                    Score: {avg_sentiment:.2f} | {total_msgs} messages
                </div>
            </div>
        </div>
        
        <div style='background: white; padding: 10px; border-radius: 8px; 
                    max-height: 200px; overflow-y: auto;'>
            <div style='font-size: 0.85em; font-weight: 600; color: #6b7280; 
                        margin-bottom: 8px;'>
                Key Messages:
            </div>
"""
        
        # Show key messages (filter out None messages)
        valid_messages = [msg for msg in messages if msg and msg.get('message') and msg.get('sentiment')]
        
        if valid_messages:
            for msg in valid_messages[:5]:  # Show first 5 messages
                sentiment_emoji = {
                    'positive': '😊',
                    'negative': '😞',
                    'severe_negative': '😡',
                    'neutral': '😐',
                    'mixed': '🤔'
                }.get(msg['sentiment'], '💬')
                
                message_text = msg['message']
                if len(message_text) > 120:
                    message_text = message_text[:120] + '...'
                
                html += f"""
            <div style='margin: 5px 0; padding: 8px; background: #f9fafb; 
                        border-radius: 6px; font-size: 0.85em; display: flex; 
                        align-items: start; gap: 8px;'>
                <span style='font-size: 1.2em; flex-shrink: 0;'>{sentiment_emoji}</span>
                <span style='color: #4b5563; flex: 1;'>{message_text}</span>
            </div>
"""
        else:
            html += """
            <div style='padding: 15px; text-align: center; color: #9ca3af; font-size: 0.85em;'>
                No analyzed messages in this conversation
            </div>
"""
        
        html += """
        </div>
    </div>
"""
    
    html += "</div>"
    return html


# Test function
def test_sentiment_analytics():
    """Test sentiment analytics module"""
    print("\n" + "="*60)
    print("🧪 TESTING SENTIMENT ANALYTICS MODULE")
    print("="*60)
    print("\n✅ Sentiment analytics module loaded successfully!")
    print("\nFeatures:")
    print("  • User profile cards")
    print("  • Sentiment overview with lead status")
    print("  • Interactive timeline plots")
    print("  • Conversation history with key messages")
    print("  • Risk alerts for negative sentiment")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    test_sentiment_analytics()