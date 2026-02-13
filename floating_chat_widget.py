"""
FLOATING CHATBOT WIDGET - Professional Chat Bubble (Bottom-Right Corner)
Like Intercom, Drift, or LiveChat widgets!
"""

# ═══════════════════════════════════════════════════════════════════
# SOLUTION: Floating Chat Widget (Bottom-Right Corner)
# ═══════════════════════════════════════════════════════════════════

"""
WHAT YOU GET:
- 💬 Chat bubble in bottom-right corner (always visible)
- 🔔 Shows message: "Hi! Need help? Ask me anything!"
- 🎨 Professional design like Intercom/Drift
- 📱 Click to expand full chat
- ❌ Close button to minimize
- 🌟 Floating above all content
- 🎯 Available on ALL pages (Customer & Admin)
"""

# ═══════════════════════════════════════════════════════════════════
# IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════

def create_floating_chatbot_widget(app):
    """Create professional floating chat widget"""
    
    from chatbot_module import AutomotiveChatbot
    
    # Initialize chatbot
    chatbot = AutomotiveChatbot(app)
    
    def chat_with_bot(message, history, chat_open):
        """Handle chat messages"""
        if not message:
            return history, "", chat_open
        
        response = chatbot.process_message(message, user_role="customer")
        history = history or []
        history.append((message, response))
        
        return history, "", chat_open
    
    def toggle_chat(current_state):
        """Toggle chat window open/closed"""
        return not current_state
    
    # CSS for floating widget
    css = """
    <style>
        /* Floating Chat Button */
        #chat-bubble-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        
        #chat-bubble-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        
        #chat-bubble-btn svg {
            width: 32px;
            height: 32px;
            fill: white;
        }
        
        /* Notification Badge */
        .chat-notification {
            position: absolute;
            top: -5px;
            right: -5px;
            background: #f44336;
            color: white;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            font-size: 12px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        /* Welcome Message Tooltip */
        .chat-tooltip {
            position: fixed;
            bottom: 90px;
            right: 20px;
            background: white;
            padding: 15px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            max-width: 280px;
            z-index: 9998;
            animation: slideIn 0.5s ease;
        }
        
        @keyframes slideIn {
            from { 
                opacity: 0;
                transform: translateY(20px);
            }
            to { 
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .chat-tooltip::after {
            content: '';
            position: absolute;
            bottom: -10px;
            right: 25px;
            width: 0;
            height: 0;
            border-left: 10px solid transparent;
            border-right: 10px solid transparent;
            border-top: 10px solid white;
        }
        
        .chat-tooltip h4 {
            margin: 0 0 5px 0;
            color: #667eea;
            font-size: 14px;
        }
        
        .chat-tooltip p {
            margin: 0;
            color: #666;
            font-size: 13px;
        }
        
        .chat-tooltip-close {
            position: absolute;
            top: 5px;
            right: 5px;
            background: none;
            border: none;
            color: #999;
            cursor: pointer;
            font-size: 16px;
        }
        
        /* Floating Chat Window */
        .chat-window {
            position: fixed;
            bottom: 90px;
            right: 20px;
            width: 380px;
            height: 550px;
            background: white;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            z-index: 9998;
            display: flex;
            flex-direction: column;
            animation: slideUp 0.3s ease;
        }
        
        @keyframes slideUp {
            from { 
                opacity: 0;
                transform: translateY(30px);
            }
            to { 
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .chat-window-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 16px 16px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .chat-window-header h3 {
            margin: 0;
            font-size: 18px;
        }
        
        .chat-window-close {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s;
        }
        
        .chat-window-close:hover {
            background: rgba(255,255,255,0.3);
        }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            .chat-window {
                width: calc(100% - 40px);
                height: calc(100% - 100px);
                bottom: 10px;
                right: 20px;
                left: 20px;
            }
            
            .chat-tooltip {
                max-width: calc(100% - 100px);
            }
        }
    </style>
    """
    
    # HTML for floating widget
    widget_html = """
    <div id="floating-chat-widget">
        <!-- Chat Bubble Button -->
        <button id="chat-bubble-btn" onclick="toggleChatWindow()">
            <svg viewBox="0 0 24 24">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
            </svg>
            <span class="chat-notification">1</span>
        </button>
        
        <!-- Welcome Tooltip -->
        <div class="chat-tooltip" id="chat-tooltip">
            <button class="chat-tooltip-close" onclick="closeTooltip()">×</button>
            <h4>👋 Hi there!</h4>
            <p>Need help finding the perfect car? Ask me anything!</p>
        </div>
    </div>
    
    <script>
        // Auto-hide tooltip after 5 seconds
        setTimeout(function() {
            var tooltip = document.getElementById('chat-tooltip');
            if (tooltip) {
                tooltip.style.animation = 'slideOut 0.3s ease';
                setTimeout(function() { 
                    tooltip.style.display = 'none'; 
                }, 300);
            }
        }, 5000);
        
        function closeTooltip() {
            document.getElementById('chat-tooltip').style.display = 'none';
        }
        
        function toggleChatWindow() {
            // This will be handled by Gradio component visibility
            var event = new CustomEvent('toggleChat');
            document.dispatchEvent(event);
        }
    </script>
    """
    
    # Create Gradio components
    with gr.Group(visible=False) as chat_window:
        with gr.Column():
            gr.HTML("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 20px; border-radius: 12px 12px 0 0; 
                        margin: -20px -20px 20px -20px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h3 style='margin: 0;'>🤖 AI Assistant</h3>
                    <button onclick='document.getElementById("close-chat-btn").click()' 
                            style='background: rgba(255,255,255,0.2); border: none; color: white; 
                                   width: 30px; height: 30px; border-radius: 50%; cursor: pointer;'>
                        ✕
                    </button>
                </div>
                <p style='margin: 5px 0 0 0; font-size: 13px; opacity: 0.9;'>
                    Ask me anything about vehicles!
                </p>
            </div>
            """)
            
            chatbot_ui = gr.Chatbot(
                value=[("", "👋 Hi! I'm your AI assistant. How can I help you today?\n\nTry:\n• 'Show me SUVs under 300k'\n• 'Book test drive'\n• 'Check availability'")],
                height=380,
                show_label=False,
                bubble_full_width=False
            )
            
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="Type your message...",
                    show_label=False,
                    scale=4,
                    container=False
                )
                send_btn = gr.Button("📤", scale=1, variant="primary")
            
            with gr.Row():
                gr.Button("🔍 Search", size="sm", scale=1)
                gr.Button("🚗 Book", size="sm", scale=1)
                gr.Button("📋 Help", size="sm", scale=1)
                close_btn = gr.Button("✕ Close", size="sm", scale=1, elem_id="close-chat-btn")
    
    # State for chat visibility
    chat_open = gr.State(False)
    
    # Event handlers
    send_btn.click(
        chat_with_bot,
        [msg_input, chatbot_ui, chat_open],
        [chatbot_ui, msg_input, chat_open]
    )
    
    msg_input.submit(
        chat_with_bot,
        [msg_input, chatbot_ui, chat_open],
        [chatbot_ui, msg_input, chat_open]
    )
    
    close_btn.click(
        lambda: gr.update(visible=False),
        None,
        chat_window
    )
    
    return css, widget_html, chat_window


# ═══════════════════════════════════════════════════════════════════
# INTEGRATION INTO APP.PY
# ═══════════════════════════════════════════════════════════════════

"""
STEP 1: Add to main() function
================================

def main():
    logger.info("Starting application...")
    
    try:
        app = AutomotiveAssistantApp()
        
        customer_portal = create_customer_portal(app)
        admin_dashboard = create_admin_dashboard(app)
        
        # Create floating chatbot
        chat_css, chat_widget_html, chat_window = create_floating_chatbot_widget(app)
        
        with gr.Blocks(theme=gr.themes.Soft(), 
                      css=chat_css,  # ADD CSS HERE
                      title="Automotive AI Platform") as demo:
            
            gr.Markdown(header_html)
            
            # Add floating chat widget HTML (BEFORE tabs)
            gr.HTML(chat_widget_html)
            
            with gr.Tabs():
                with gr.Tab("🏠 Customer Portal"):
                    customer_portal.render()
                
                with gr.Tab("🔐 Admin Dashboard"):
                    admin_dashboard.render()
                
                with gr.Tab("ℹ️ About"):
                    gr.Markdown(about_content)
            
            # Add floating chat window (AFTER tabs)
            chat_window.render()
            
            gr.Markdown(footer_html)
        
        demo.launch(...)
"""


# ═══════════════════════════════════════════════════════════════════
# ALTERNATIVE: SIMPLER VERSION (Pure CSS/JS)
# ═══════════════════════════════════════════════════════════════════

SIMPLE_FLOATING_CHAT = """
<!-- Add this in main() function after gr.Markdown(header_html) -->

<div id="floating-chat-container">
    <!-- Chat Button -->
    <button id="chat-btn" onclick="toggleChat()" 
            style='position: fixed; bottom: 20px; right: 20px; z-index: 9999;
                   width: 60px; height: 60px; border-radius: 50%;
                   background: linear-gradient(135deg, #667eea, #764ba2);
                   border: none; box-shadow: 0 4px 12px rgba(102,126,234,0.4);
                   cursor: pointer; transition: all 0.3s;'>
        <span style='font-size: 28px;'>💬</span>
        <span style='position: absolute; top: -5px; right: -5px;
                     background: #f44336; color: white; width: 20px; height: 20px;
                     border-radius: 50%; font-size: 12px; font-weight: bold;
                     display: flex; align-items: center; justify-content: center;'>
            1
        </span>
    </button>
    
    <!-- Welcome Tooltip -->
    <div id="chat-tooltip" 
         style='position: fixed; bottom: 90px; right: 20px; z-index: 9998;
                background: white; padding: 15px 20px; border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.15); max-width: 280px;
                animation: slideIn 0.5s ease;'>
        <button onclick="document.getElementById('chat-tooltip').style.display='none'"
                style='position: absolute; top: 5px; right: 5px; background: none;
                       border: none; color: #999; cursor: pointer; font-size: 16px;'>
            ×
        </button>
        <h4 style='margin: 0 0 5px 0; color: #667eea; font-size: 14px;'>
            👋 Hi there!
        </h4>
        <p style='margin: 0; color: #666; font-size: 13px;'>
            Need help? Ask me anything about vehicles!
        </p>
    </div>
    
    <!-- Chat Window -->
    <div id="chat-window" 
         style='position: fixed; bottom: 90px; right: 20px; z-index: 9998;
                width: 380px; height: 550px; background: white;
                border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.2);
                display: none; flex-direction: column;'>
        
        <div style='background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white; padding: 20px; border-radius: 16px 16px 0 0;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <h3 style='margin: 0; font-size: 18px;'>🤖 AI Assistant</h3>
                    <p style='margin: 5px 0 0 0; font-size: 13px; opacity: 0.9;'>
                        Online • Ready to help
                    </p>
                </div>
                <button onclick="toggleChat()"
                        style='background: rgba(255,255,255,0.2); border: none; color: white;
                               width: 30px; height: 30px; border-radius: 50%; cursor: pointer;'>
                    ✕
                </button>
            </div>
        </div>
        
        <div id="chat-messages" 
             style='flex: 1; overflow-y: auto; padding: 20px; background: #f8f9fa;'>
            <div style='background: white; padding: 12px; border-radius: 12px;
                        margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                <strong style='color: #667eea;'>🤖 AI Assistant:</strong>
                <p style='margin: 5px 0 0 0; color: #333;'>
                    Hi! I'm your automotive AI assistant. How can I help you today?
                </p>
                <div style='margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap;'>
                    <button onclick="sendQuickMessage('Show me SUVs under 300k')"
                            style='background: #e3f2fd; border: none; padding: 8px 12px;
                                   border-radius: 20px; cursor: pointer; font-size: 12px;
                                   color: #1976d2;'>
                        🔍 Search vehicles
                    </button>
                    <button onclick="sendQuickMessage('Book test drive')"
                            style='background: #f3e5f5; border: none; padding: 8px 12px;
                                   border-radius: 20px; cursor: pointer; font-size: 12px;
                                   color: #7b1fa2;'>
                        🚗 Book test drive
                    </button>
                    <button onclick="sendQuickMessage('Help')"
                            style='background: #fff3e0; border: none; padding: 8px 12px;
                                   border-radius: 20px; cursor: pointer; font-size: 12px;
                                   color: #e65100;'>
                        ❓ Help
                    </button>
                </div>
            </div>
        </div>
        
        <div style='padding: 15px; border-top: 1px solid #e0e0e0; background: white;
                    border-radius: 0 0 16px 16px;'>
            <div style='display: flex; gap: 10px;'>
                <input id="chat-input" type="text" 
                       placeholder="Type your message..."
                       style='flex: 1; padding: 12px; border: 1px solid #e0e0e0;
                              border-radius: 24px; font-size: 14px;'
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()"
                        style='background: linear-gradient(135deg, #667eea, #764ba2);
                               border: none; color: white; width: 45px; height: 45px;
                               border-radius: 50%; cursor: pointer; font-size: 20px;'>
                    📤
                </button>
            </div>
        </div>
    </div>
</div>

<script>
// Auto-hide tooltip
setTimeout(function() {
    var tooltip = document.getElementById('chat-tooltip');
    if (tooltip) tooltip.style.display = 'none';
}, 5000);

// Toggle chat window
function toggleChat() {
    var chatWindow = document.getElementById('chat-window');
    if (chatWindow.style.display === 'none' || !chatWindow.style.display) {
        chatWindow.style.display = 'flex';
        document.getElementById('chat-tooltip').style.display = 'none';
    } else {
        chatWindow.style.display = 'none';
    }
}

// Send message
function sendMessage() {
    var input = document.getElementById('chat-input');
    var message = input.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('You', message, '#667eea');
    input.value = '';
    
    // Simulate bot response (replace with actual Gradio API call)
    setTimeout(function() {
        addMessageToChat('AI Assistant', 
            'I received your message: "' + message + '". Let me help you with that!',
            '#764ba2'
        );
    }, 1000);
}

// Quick message buttons
function sendQuickMessage(text) {
    document.getElementById('chat-input').value = text;
    sendMessage();
}

// Add message to chat UI
function addMessageToChat(sender, message, color) {
    var messagesDiv = document.getElementById('chat-messages');
    var messageDiv = document.createElement('div');
    messageDiv.style.cssText = 'background: white; padding: 12px; border-radius: 12px; ' +
                                'margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);';
    messageDiv.innerHTML = '<strong style="color: ' + color + ';">' + 
                           (sender === 'You' ? '👤' : '🤖') + ' ' + sender + ':</strong>' +
                           '<p style="margin: 5px 0 0 0; color: #333;">' + message + '</p>';
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Make chat button bounce on hover
document.getElementById('chat-btn').addEventListener('mouseenter', function() {
    this.style.transform = 'scale(1.1)';
});
document.getElementById('chat-btn').addEventListener('mouseleave', function() {
    this.style.transform = 'scale(1)';
});
</script>

<style>
@keyframes slideIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

#chat-btn:hover {
    transform: scale(1.1) !important;
    box-shadow: 0 6px 20px rgba(102,126,234,0.6) !important;
}

#chat-window {
    animation: slideUp 0.3s ease;
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Mobile responsive */
@media (max-width: 768px) {
    #chat-window {
        width: calc(100% - 40px) !important;
        height: calc(100% - 100px) !important;
        bottom: 10px !important;
        right: 20px !important;
        left: 20px !important;
    }
}
</style>
"""

# ═══════════════════════════════════════════════════════════════════
# USAGE IN APP.PY
# ═══════════════════════════════════════════════════════════════════

"""
SIMPLE WAY (Recommended):
========================

In main() function, add this AFTER the header:

```python
with gr.Blocks(...) as demo:
    gr.Markdown(header_html)
    
    # ADD THIS LINE:
    gr.HTML(SIMPLE_FLOATING_CHAT)
    
    with gr.Tabs():
        # ... your existing tabs ...
```

That's it! The floating chat widget will appear on all pages!
"""