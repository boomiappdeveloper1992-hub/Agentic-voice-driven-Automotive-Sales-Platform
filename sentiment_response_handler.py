"""
Sentiment Response Handler
Provides context-aware responses based on user sentiment
Handles: Positive, Negative, Mixed, Ambiguous, Slang, Greetings, Farewells
"""

import logging
import random
import re
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentimentResponseHandler:
    """Handle sentiment-based responses with predefined rules"""
    
    def __init__(self):
        # ═══════════════════════════════════════════════════════════
        # POSITIVE SENTIMENT RESPONSES
        # ═══════════════════════════════════════════════════════════
        self.positive_responses = [
            "😊 That's wonderful to hear! How can I assist you further?",
            "🎉 Great! I'm here to help you find your perfect vehicle.",
            "✨ Fantastic! What would you like to explore today?",
            "👍 Excellent! Let me help you with that.",
            "🌟 That's great! How may I assist you further?"
        ]
        
        # ═══════════════════════════════════════════════════════════
        # GREETING RESPONSES
        # ═══════════════════════════════════════════════════════════
        self.greeting_responses = [
            "Hello! 👋 Welcome to our automotive assistant. How can I help you find your perfect vehicle today?",
            "Hi there! 😊 I'm here to help you explore our vehicle collection. What are you looking for?",
            "Hey! 🚗 Great to see you! Whether you're looking for luxury, performance, or economy, I'm here to help.",
            "Greetings! ✨ Ready to find your dream car? Let me know what interests you!",
            "Welcome! 🌟 I can help you search vehicles, book test drives, or answer any questions. What would you like to do?"
        ]
        
        # ═══════════════════════════════════════════════════════════
        # FAREWELL RESPONSES
        # ═══════════════════════════════════════════════════════════
        self.farewell_responses = [
            "Goodbye! 👋 Feel free to come back anytime. Have a great day!",
            "See you later! 🌟 Don't hesitate to return if you need more help. Take care!",
            "Have a wonderful day! 😊 We're here 24/7 whenever you need us.",
            "Bye! ✨ It was great helping you. Come back soon!",
            "Take care! 🚗 Looking forward to assisting you again. Safe travels!"
        ]
        
        self.night_farewells = [
            "Good night! 🌙 Sleep well and come back anytime. Sweet dreams!",
            "Have a restful night! 😴 We'll be here when you need us. Good night!",
            "Sleep tight! ✨ Feel free to continue your search tomorrow. Good night!"
        ]
        
        # ═══════════════════════════════════════════════════════════
        # THANK YOU RESPONSES
        # ═══════════════════════════════════════════════════════════
        self.thank_you_responses = [
            "You're very welcome! 😊 I'm happy I could help. Is there anything else you'd like to know?",
            "My pleasure! 🌟 Feel free to ask if you need anything else.",
            "Glad I could assist! ✨ Don't hesitate to reach out if you have more questions.",
            "You're welcome! 👍 I'm here anytime you need help.",
            "Happy to help! 😊 Let me know if there's anything else I can do for you."
        ]
        
        # ═══════════════════════════════════════════════════════════
        # MIXED/AMBIGUOUS SENTIMENT RESPONSES
        # ═══════════════════════════════════════════════════════════
        self.mixed_responses = [
            "I understand there are some concerns. 🤔 Let me help address them. What specifically can I improve for you?",
            "Thank you for the feedback! 😊 I hear both the positive and the concerns. How can I make your experience better?",
            "I appreciate your honest feedback. 💭 Let me help you find exactly what you're looking for.",
            "Got it! There's room for improvement. 🔧 Let me know what would work better for you."
        ]
        
        # ═══════════════════════════════════════════════════════════
        # NEGATIVE SENTIMENT RESPONSES
        # ═══════════════════════════════════════════════════════════
        self.negative_responses_mild = [
            "I'm sorry to hear that. 😔 Let me see how I can help improve your experience.",
            "I understand your concern. Let me assist you better.",
            "I apologize for any inconvenience. How can I make this right?"
        ]
        
        self.negative_responses_severe = [
            "I sincerely apologize for your experience. 😔 Would you like me to connect you with our support team?",
            "I'm truly sorry about this. Let me escalate this to our specialist team who can assist you better.",
            "I understand your frustration. Would you prefer to speak with a human agent who can provide immediate assistance?"
        ]
        
        # ═══════════════════════════════════════════════════════════
        # KEYWORDS - POSITIVE
        # ═══════════════════════════════════════════════════════════
        self.positive_keywords = [
            'good', 'great', 'excellent', 'awesome', 'fantastic', 'wonderful',
            'perfect', 'amazing', 'love', 'nice', 'beautiful', 'brilliant',
            'superb', 'outstanding', 'happy', 'pleased', 'satisfied',
            'helpful', 'fine', 'cool', 'sweet', 'neat', 'solid',
            'impressive', 'incredible', 'fabulous', 'marvelous'
        ]
        
        # ═══════════════════════════════════════════════════════════
        # KEYWORDS - THANK YOU
        # ═══════════════════════════════════════════════════════════
        self.thank_you_keywords = [
            'thanks', 'thank', 'thank you', 'thankyou', 'thx', 'ty', 'tyvm',
            'appreciate', 'appreciated', 'grateful', 'gratitude'
        ]
        
        # ═══════════════════════════════════════════════════════════
        # KEYWORDS - GREETINGS
        # ═══════════════════════════════════════════════════════════
        self.greeting_keywords = [
            'hi', 'hello', 'hey', 'hiya', 'howdy', 'greetings', 
            'good morning', 'good afternoon', 'good evening',
            'morning', 'afternoon', 'evening', 'sup', 'yo', 'hii', 'heya'
        ]
        
        # ═══════════════════════════════════════════════════════════
        # KEYWORDS - FAREWELLS
        # ═══════════════════════════════════════════════════════════
        self.farewell_keywords = [
            'bye', 'goodbye', 'good bye', 'see you', 'see ya', 'later',
            'catch you later', 'take care', 'farewell', 'cya', 'ttyl',
            'gotta go', 'have to go', 'leaving', 'adios', 'cheerio'
        ]
        
        self.night_farewell_keywords = [
            'good night', 'goodnight', 'night', 'sleep well', 'sweet dreams',
            'gn', 'nite', 'g9'
        ]
        
        # ═══════════════════════════════════════════════════════════
        # KEYWORDS - NEGATIVE
        # ═══════════════════════════════════════════════════════════
        self.negative_keywords = [
            'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate',
            'angry', 'frustrated', 'annoyed', 'disappointed', 'unhappy',
            'useless', 'pathetic', 'disgusting', 'rubbish', 'garbage',
            'poor', 'waste', 'problem', 'issue', 'complaint', 'wrong',
            'error', 'fail', 'failed', 'broken', 'not working', 'sucks',
            'crap', 'shit', 'damn', 'wtf'
        ]
        
        # ═══════════════════════════════════════════════════════════
        # KEYWORDS - SEVERE NEGATIVE (ESCALATION)
        # ═══════════════════════════════════════════════════════════
        self.severe_negative_keywords = [
            'refund', 'scam', 'fraud', 'sue', 'lawyer', 'legal',
            'manager', 'supervisor', 'complaint', 'report', 'unacceptable',
            'disgusting service', 'never again', 'boycott'
        ]
        
        # ═══════════════════════════════════════════════════════════
        # KEYWORDS - MIXED/AMBIGUOUS
        # ═══════════════════════════════════════════════════════════
        self.mixed_indicators = [
            'but', 'however', 'although', 'though', 'except', 'only if',
            'kind of', 'sort of', 'kinda', 'sorta', 'not bad', 'not great',
            'could be better', 'meh', 'okay but', 'ok but', 'alright but'
        ]
        
        # ═══════════════════════════════════════════════════════════
        # SLANG & SHORTCUT MAPPING
        # ═══════════════════════════════════════════════════════════
        self.slang_mapping = {
            # Common shortcuts
            'u': 'you',
            'ur': 'your',
            'r': 'are',
            'y': 'why',
            'pls': 'please',
            'plz': 'please',
            'thx': 'thanks',
            'ty': 'thank you',
            'tyvm': 'thank you very much',
            'np': 'no problem',
            'nvm': 'never mind',
            'idk': 'i dont know',
            'dunno': 'dont know',
            'gonna': 'going to',
            'wanna': 'want to',
            'gotta': 'got to',
            'lemme': 'let me',
            'gimme': 'give me',
            
            # Positive slang
            'lol': 'laughing',
            'lmao': 'laughing',
            'haha': 'laughing',
            'cool': 'good',
            'dope': 'great',
            'lit': 'great',
            'fire': 'excellent',
            'sick': 'awesome',
            'dank': 'great',
            
            # Negative slang
            'wtf': 'what the hell',
            'omg': 'oh my god',
            'smh': 'shaking my head',
            'ffs': 'for goodness sake',
            
            # Neutral/ambiguous
            'meh': 'okay',
            'idc': 'i dont care',
            'whatever': 'okay'
        }
        
        # ═══════════════════════════════════════════════════════════
        # CONTEXTUAL ACKNOWLEDGMENTS
        # ═══════════════════════════════════════════════════════════
        self.acknowledgment_keywords = [
            'ok', 'okay', 'alright', 'sure', 'fine', 'got it', 'understood',
            'i see', 'makes sense', 'right', 'yes', 'yep', 'yeah', 'yup',
            'k', 'kk', 'oki'
        ]
        
        logger.info("✅ SentimentResponseHandler initialized with enhanced capabilities")

        
    
    def normalize_message(self, message: str) -> str:
        """Normalize message by expanding slang and shortcuts"""
        message_lower = message.lower().strip()
        
        # Replace slang/shortcuts
        words = message_lower.split()
        normalized_words = []
        
        for word in words:
            # Remove punctuation for matching
            clean_word = re.sub(r'[^\w\s]', '', word)
            if clean_word in self.slang_mapping:
                normalized_words.append(self.slang_mapping[clean_word])
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def detect_message_type(self, message: str) -> str:
        """
        Detect the type of message: greeting, farewell, thank_you, etc.
        
        Returns:
            Message type: 'greeting', 'farewell', 'night_farewell', 'thank_you', 
                         'acknowledgment', 'sentiment'
        """
            
        message_normalized = self.normalize_message(message)
        message_lower = message.lower().strip()
        
        # Check for night farewells (higher priority)
        if any(kw in message_lower for kw in self.night_farewell_keywords):
            return 'night_farewell'
        
        # Check for greetings
        if any(kw in message_lower for kw in self.greeting_keywords):
            # Exclude if it's "not good" or similar
            if 'not' not in message_lower and 'no' not in message_lower:
                return 'greeting'
        
        # Check for farewells
        if any(kw in message_lower for kw in self.farewell_keywords):
            return 'farewell'
        
        # Check for thank you
        if any(kw in message_normalized for kw in self.thank_you_keywords):
            return 'thank_you'
        
        # Check for simple acknowledgments
        if message_lower in self.acknowledgment_keywords:
            return 'acknowledgment'
        
        # Otherwise, it's sentiment-based
        return 'sentiment'

    def _correct_typos(self, text: str) -> str:
        """Correct common typos before sentiment analysis"""
        if not hasattr(self, 'typo_corrections'):
            self.typo_corrections = {
                'baa': 'bad',
                'baad': 'bad',
                'vry': 'very',
                'verry': 'very',
                'gud': 'good',
                'grt': 'great',
                'wrng': 'wrong',
                'rong': 'wrong',
                'terble': 'terrible',
                'terible': 'terrible',
                'awfl': 'awful',
                'horible': 'horrible',
                'excelent': 'excellent',
                'amazin': 'amazing'
            }
    
        words = text.split()
        corrected = []
    
        for word in words:
            word_lower = word.lower().strip('.,!?')
            if word_lower in self.typo_corrections:
                corrected.append(self.typo_corrections[word_lower])
            else:
                corrected.append(word)
    
        return ' '.join(corrected)
    
    def analyze_sentiment(self, message: str) -> Tuple[str, float, bool]:
        """
        Analyze sentiment of user message
        
        Returns:
            Tuple of (sentiment_label, confidence_score, needs_escalation)
        """
        message = self._correct_typos(message)    
        message_normalized = self.normalize_message(message)
        message_lower = message.lower()
        
        # Check for severe negative sentiment (highest priority)
        if any(keyword in message_lower for keyword in self.severe_negative_keywords):
            return 'severe_negative', 0.95, True

        not_happy_patterns = [
            r'\bnot\s+happy\b',           # "not happy"
            r'\bnot\s+satisfied\b',       # "not satisfied"
            r'\bnot\s+pleased\b',         # "not pleased"
            r'\bunsatisfied\b',           # "unsatisfied"
            r'\bunhappy\b',               # "unhappy"
            r'\bdisappointed\b',          # "disappointed"
            r'\bnot\s+getting\b',         # "not getting" ✅ NEW
            r'\bnot\s+receiving\b',       # "not receiving" ✅ NEW
            r'\bnot\s+finding\b'          # "not finding" ✅ NEW
        ]
        if any(re.search(pattern, message_lower) for pattern in not_happy_patterns):
            return 'negative', 0.90, True  # High confidence, needs escalation

        not_positive_patterns = [
            'not correct', 'not right', 'not good', 'not working', 
            'not helpful', 'not accurate', 'not true', "doesn't work",
            "isn't correct", "isn't right", "isn't good", "aren't correct",
            "aren't right", "aren't good"
        ]

        if any(pattern in message_lower for pattern in not_positive_patterns):
            return 'negative', 0.85, True

        criticism_patterns = [
            'you are bad', 'you are wrong', 'you are incorrect', 'you are terrible',
            'you\'re bad', 'you\'re wrong', 'you\'re incorrect', 'you\'re terrible',
            'this is wrong', 'this is incorrect', 'this is bad', 'this is terrible',
            'answer is wrong', 'answer is incorrect', 'answer is not correct',
            'response is wrong', 'response is incorrect',
            'that is wrong', 'that is incorrect', 'that is bad'
        ]
        if any(pattern in message_lower for pattern in criticism_patterns):
            return 'negative', 0.85, True
    
        # ✅ ADD: Check for simple negative words at start
        if message_lower.strip() in ['bad', 'terrible', 'awful', 'horrible', 'worst', 'wrong']:
            return 'negative', 0.85, False
        
        # Check for mixed/ambiguous sentiment
        has_mixed_indicator = any(indicator in message_lower for indicator in self.mixed_indicators)
        
        # Count positive and negative keywords
        positive_count = sum(1 for kw in self.positive_keywords if kw in message_normalized)
        negative_count = sum(1 for kw in self.negative_keywords if kw in message_normalized)
        
        # Handle "not bad", "not terrible" etc (inverted sentiment)
        not_pattern = r'\b(not|no|never|dont|none)\s+(' + '|'.join(self.negative_keywords) + r')\b'
        if re.search(not_pattern, message_normalized):
            # "not bad" = slightly positive
            negative_count = max(0, negative_count - 1)
            positive_count += 1
        
        # Handle "not good", "not great" etc
        not_positive_pattern = r'\b(not|no|never|dont|none)\s+(' + '|'.join(self.positive_keywords) + r')\b'
        if re.search(not_positive_pattern, message_normalized):
            # "not good" = negative
            positive_count = max(0, positive_count - 1)
            negative_count += 1
        
        # Determine sentiment
        if has_mixed_indicator and positive_count > 0 and negative_count > 0:
            return 'mixed', 0.70, False
        
        if negative_count > positive_count and negative_count >= 2:
            return 'negative', 0.75, False
        elif negative_count > 0 and positive_count == 0:
            return 'negative', 0.60, False
        elif positive_count > negative_count and positive_count >= 1:
            return 'positive', 0.80, False
        elif 'meh' in message_normalized or 'whatever' in message_normalized:
            return 'mixed', 0.60, False
        else:
            return 'neutral', 0.50, False
    
    def get_response(self, message: str, sentiment_label: str = None, 
                     needs_escalation: bool = False) -> Dict[str, any]:
        """
        Get appropriate response based on sentiment and message type
        
        Returns:
            Dict with response, should_escalate, escalation_message
        """
        # First, detect message type
        message_type = self.detect_message_type(message)
        
        response_data = {
            'response': '',
            'should_escalate': False,
            'escalation_message': None,
            'sentiment': message_type,
            'show_support_options': False,
            'message_type': message_type
        }
        
        # ═══════════════════════════════════════════════════════════
        # HANDLE GREETINGS
        # ═══════════════════════════════════════════════════════════
        if message_type == 'greeting':
            response_data['response'] = random.choice(self.greeting_responses)
            response_data['sentiment'] = 'greeting'
            return response_data
        
        # ═══════════════════════════════════════════════════════════
        # HANDLE FAREWELLS
        # ═══════════════════════════════════════════════════════════
        if message_type == 'night_farewell':
            response_data['response'] = random.choice(self.night_farewells)
            response_data['sentiment'] = 'farewell'
            return response_data
        
        if message_type == 'farewell':
            response_data['response'] = random.choice(self.farewell_responses)
            response_data['sentiment'] = 'farewell'
            return response_data
        
        # ═══════════════════════════════════════════════════════════
        # HANDLE THANK YOU
        # ═══════════════════════════════════════════════════════════
        if message_type == 'thank_you':
            response_data['response'] = random.choice(self.thank_you_responses)
            response_data['sentiment'] = 'positive'
            return response_data
        
        # ═══════════════════════════════════════════════════════════
        # HANDLE ACKNOWLEDGMENTS
        # ═══════════════════════════════════════════════════════════
        if message_type == 'acknowledgment':
            response_data['response'] = random.choice([
                "Great! 👍 What would you like to do next?",
                "Perfect! 😊 How else can I assist you?",
                "Sounds good! ✨ Let me know if you need anything else.",
                "Alright! 🌟 Feel free to ask me anything."
            ])
            response_data['sentiment'] = 'neutral'
            return response_data
        
        # ═══════════════════════════════════════════════════════════
        # HANDLE SENTIMENT-BASED MESSAGES
        # ═══════════════════════════════════════════════════════════
        # Analyze sentiment if not provided
        if sentiment_label is None:
            sentiment_label, confidence, needs_escalation = self.analyze_sentiment(message)
        
        response_data['sentiment'] = sentiment_label
        response_data['should_escalate'] = needs_escalation
        
        # Generate response based on sentiment
        if sentiment_label == 'positive':
            response_data['response'] = random.choice(self.positive_responses)
        
        elif sentiment_label == 'mixed':
            response_data['response'] = random.choice(self.mixed_responses)
            response_data['show_support_options'] = True
        
        elif sentiment_label == 'negative':
            response_data['response'] = random.choice(self.negative_responses_mild)
            response_data['show_support_options'] = True
        
        elif sentiment_label == 'severe_negative':
            response_data['response'] = random.choice(self.negative_responses_severe)
            response_data['should_escalate'] = True
            response_data['escalation_message'] = self._generate_escalation_message()
        
        else:  # neutral
            response_data['response'] = random.choice([
                "I'm here to help! 😊 What would you like to know?",
                "Sure thing! How can I assist you today?",
                "Let me know what you're looking for! 🚗",
                "Happy to help! What can I do for you?"
            ])
        
        return response_data
    
    def _generate_escalation_message(self) -> str:
        """Generate escalation message with support options"""
        return """
<div style='padding: 20px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
            border-radius: 12px; color: white; margin: 15px 0;
            box-shadow: 0 4px 12px rgba(245,158,11,0.4);'>
    <h3 style='margin: 0 0 12px 0; display: flex; align-items: center; gap: 10px;'>
        <span style='font-size: 1.5em;'>🆘</span>
        <span>Let Us Help You Better</span>
    </h3>
    <p style='margin: 0 0 15px 0; opacity: 0.95;'>
        I understand this is frustrating. Here are your options:
    </p>
    
    <div style='display: grid; gap: 10px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {
                chatInput.value = "🆘 ESCALATE:urgent_support";
                chatInput.dispatchEvent(new Event("input", { bubbles: true }));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }
        ' style='width: 100%; background: white; color: #d97706; 
                 border: 2px solid white; padding: 14px; border-radius: 10px; 
                 cursor: pointer; font-weight: 600; transition: all 0.2s;'>
            📞 Connect with Support Team
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {
                chatInput.value = "🆘 ESCALATE:manager_request";
                chatInput.dispatchEvent(new Event("input", { bubbles: true }));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }
        ' style='width: 100%; background: rgba(255,255,255,0.2); color: white; 
                 border: 2px solid white; padding: 14px; border-radius: 10px; 
                 cursor: pointer; font-weight: 600; transition: all 0.2s;'>
            👔 Request Manager
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {
                chatInput.value = "🆘 ESCALATE:file_complaint";
                chatInput.dispatchEvent(new Event("input", { bubbles: true }));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }
        ' style='width: 100%; background: rgba(255,255,255,0.2); color: white; 
                 border: 2px solid white; padding: 14px; border-radius: 10px; 
                 cursor: pointer; font-weight: 600; transition: all 0.2s;'>
            📋 File Complaint
        </button>
    </div>
</div>

<div style='padding: 15px; background: #fef3c7; border-radius: 10px; 
            border-left: 4px solid #f59e0b; margin: 15px 0;'>
    <p style='margin: 0; color: #92400e; font-size: 0.9em;'>
        📧 <strong>Email:</strong> support@automotive-ai.com<br>
        📞 <strong>Phone:</strong> +971-4-XXX-XXXX (24/7)<br>
        ⏰ <strong>Average Response:</strong> Under 5 minutes
    </p>
</div>
"""
    
    def generate_support_options(self) -> str:
        """Generate support options for mild negative sentiment"""
        return """
<div style='padding: 15px; background: #f0f9ff; border-radius: 10px; 
            border-left: 4px solid #3b82f6; margin: 15px 0;'>
    <h4 style='margin: 0 0 10px 0; color: #1e40af;'>💡 How Can I Help?</h4>
    <div style='display: grid; gap: 8px;'>
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {
                chatInput.value = "I need help with finding a vehicle";
                chatInput.dispatchEvent(new Event("input", { bubbles: true }));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }
        ' style='background: white; color: #1e40af; border: 2px solid #3b82f6; 
                 padding: 10px; border-radius: 8px; cursor: pointer; font-weight: 500;
                 text-align: left; transition: all 0.2s;'>
            🔍 Help Me Find a Vehicle
        </button>
        
        <button onclick='
            var chatInput = document.querySelector("#chat_input textarea");
            if (chatInput) {
                chatInput.value = "Connect me with a human agent";
                chatInput.dispatchEvent(new Event("input", { bubbles: true }));
                var sendBtn = document.querySelector("#send_btn");
                if (sendBtn) sendBtn.click();
            }
        ' style='background: white; color: #1e40af; border: 2px solid #3b82f6; 
                 padding: 10px; border-radius: 8px; cursor: pointer; font-weight: 500;
                 text-align: left; transition: all 0.2s;'>
            👤 Talk to Human Agent
        </button>
    </div>
</div>
"""