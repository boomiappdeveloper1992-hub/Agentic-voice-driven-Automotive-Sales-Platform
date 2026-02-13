"""
sentiment_module.py - Real Sentiment Analysis with Transformers
"""

import logging
from typing import Dict, Any
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Production sentiment analyzer using transformers"""
    
    def __init__(self):
        """Initialize sentiment analysis pipeline"""
        try:
            logger.info("Loading sentiment analysis model...")
            # Using a multilingual model that works well for various languages
            self.analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
                tokenizer="cardiffnlp/twitter-xlm-roberta-base-sentiment"
            )
            logger.info("✅ Sentiment analyzer loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentiment model: {e}")
            logger.info("Falling back to simple sentiment analysis")
            self.analyzer = None
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text
        
        Args:
            text: Input text to analyze
        
        Returns:
            Dictionary with label, score, and analysis
        """
        try:
            if not text or not text.strip():
                return {
                    'label': 'NEUTRAL',
                    'score': 0.5,
                    'text': text,
                    'confidence': 'low'
                }
            
            # Use transformer model if available
            if self.analyzer:
                result = self.analyzer(text[:512])[0]  # Limit to 512 tokens
                
                # Map labels to standard format
                label_map = {
                    'positive': 'POSITIVE',
                    'negative': 'NEGATIVE',
                    'neutral': 'NEUTRAL',
                    'Positive': 'POSITIVE',
                    'Negative': 'NEGATIVE',
                    'Neutral': 'NEUTRAL'
                }
                
                label = label_map.get(result['label'], result['label'].upper())
                score = result['score']
                
                # Determine confidence level
                if score >= 0.9:
                    confidence = 'very high'
                elif score >= 0.75:
                    confidence = 'high'
                elif score >= 0.6:
                    confidence = 'medium'
                else:
                    confidence = 'low'
                
                return {
                    'label': label,
                    'score': score,
                    'text': text,
                    'confidence': confidence,
                    'emoji': self._get_emoji(label)
                }
            
            # Fallback to simple keyword-based analysis
            return self._simple_sentiment_analysis(text)
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return self._simple_sentiment_analysis(text)
    
    def _simple_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """Simple keyword-based sentiment analysis as fallback"""
        text_lower = text.lower()
        
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'love', 'perfect',
            'wonderful', 'fantastic', 'awesome', 'best', 'happy', 'pleased',
            'satisfied', 'interested', 'excited', 'eager'
        ]
        
        negative_words = [
            'bad', 'poor', 'terrible', 'worst', 'hate', 'awful',
            'disappointing', 'disappointed', 'angry', 'frustrated', 'unhappy',
            'unsatisfied', 'problem', 'issue', 'concern', 'expensive'
        ]
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            label = 'POSITIVE'
            score = min(0.6 + (pos_count * 0.1), 0.95)
        elif neg_count > pos_count:
            label = 'NEGATIVE'
            score = min(0.6 + (neg_count * 0.1), 0.95)
        else:
            label = 'NEUTRAL'
            score = 0.5
        
        return {
            'label': label,
            'score': score,
            'text': text,
            'confidence': 'medium' if abs(pos_count - neg_count) > 1 else 'low',
            'emoji': self._get_emoji(label)
        }
    
    def _get_emoji(self, label: str) -> str:
        """Get emoji for sentiment label"""
        emoji_map = {
            'POSITIVE': '😊',
            'NEGATIVE': '😟',
            'NEUTRAL': '😐'
        }
        return emoji_map.get(label, '😐')
    
    def analyze_conversation(self, messages: list) -> Dict[str, Any]:
        """
        Analyze sentiment across multiple messages
        
        Args:
            messages: List of message texts
        
        Returns:
            Overall sentiment analysis
        """
        if not messages:
            return {'label': 'NEUTRAL', 'score': 0.5, 'trend': 'stable'}
        
        sentiments = [self.analyze(msg) for msg in messages]
        
        # Calculate average sentiment
        avg_score = sum(s['score'] for s in sentiments) / len(sentiments)
        
        # Determine overall label
        positive_count = sum(1 for s in sentiments if s['label'] == 'POSITIVE')
        negative_count = sum(1 for s in sentiments if s['label'] == 'NEGATIVE')
        
        if positive_count > negative_count:
            overall_label = 'POSITIVE'
        elif negative_count > positive_count:
            overall_label = 'NEGATIVE'
        else:
            overall_label = 'NEUTRAL'
        
        # Determine trend
        if len(sentiments) >= 2:
            recent = sentiments[-1]['score']
            earlier = sentiments[0]['score']
            if recent > earlier + 0.1:
                trend = 'improving'
            elif recent < earlier - 0.1:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'overall_label': overall_label,
            'average_score': avg_score,
            'trend': trend,
            'message_count': len(sentiments),
            'sentiments': sentiments
        }