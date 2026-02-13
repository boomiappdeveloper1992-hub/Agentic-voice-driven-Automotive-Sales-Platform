"""
translation_module.py - Enhanced Translation for Dubai/UAE Market
Handles Gulf Arabic, Indian languages, and mixed-language queries
"""

import logging
import re
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranslationSystem:
    """Production translation system optimized for Dubai/UAE market"""
    
    def __init__(self):
        """Initialize translation system with UAE regional support"""
        
        # Regional language codes (UAE-specific)
        self.supported_languages = {
            'en': 'English',
            
            # Arabic variants (Gulf/UAE preference)
            'ar': 'Arabic (Standard)',
            'ar-AE': 'Arabic (UAE)',
            'ar-SA': 'Arabic (Gulf)',
            
            # Indian languages (large UAE population)
            'hi': 'Hindi',
            'ur': 'Urdu',
            'ta': 'Tamil',
            'te': 'Telugu',
            'ml': 'Malayalam',
            'bn': 'Bengali',
            
            # European languages
            'fr': 'French',
            'es': 'Spanish',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'pt-BR': 'Portuguese (Brazil)',
            
            # Asian languages
            'ru': 'Russian',
            'zh': 'Chinese (Simplified)',
            'zh-CN': 'Chinese (Simplified)',
            'zh-TW': 'Chinese (Traditional)',
            'ja': 'Japanese',
            'ko': 'Korean',
            'th': 'Thai',
            'vi': 'Vietnamese',
            
            # Other
            'fa': 'Persian/Farsi',
            'tr': 'Turkish',
        }
        
        # Initialize providers
        self.langdetect_available = False
        self._initialize_providers()
        
        logger.info(f"✅ Translation system initialized for UAE market")
        logger.info(f"   Supported languages: {len(self.supported_languages)}")
    
    def _initialize_providers(self):
        """Initialize translation providers"""
        try:
            import langdetect
            self.langdetect_available = True
            logger.info("✅ langdetect available")
        except Exception as e:
            logger.warning(f"⚠️ langdetect not available: {e}")
    
    def detect_language(self, text: str) -> str:
        """
        Enhanced language detection with character-based + ML-based methods
        Optimized for Dubai/UAE: Arabic, Hindi, Urdu, English
        
        Args:
            text: Input text
        
        Returns:
            Language code with regional variant (e.g., 'ar', 'hi', 'en')
        """
        if not text or len(text.strip()) < 2:
            logger.warning("Text too short, defaulting to English")
            return 'en'
        
        text_clean = text.strip()
        
        # ========================================
        # PRIORITY 1: Character-Based Detection
        # (Most reliable for non-Latin scripts)
        # ========================================
        
        # Arabic (most common in UAE!)
        arabic_chars = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text_clean))
        if arabic_chars > 0:
            # Check if Gulf dialect markers
            gulf_markers = ['الإمارات', 'دبي', 'أبوظبي', 'ديرهم']
            if any(marker in text_clean for marker in gulf_markers):
                logger.info("🇦🇪 Detected: Gulf Arabic (UAE)")
                return 'ar-AE'
            
            logger.info("🇸🇦 Detected: Standard Arabic")
            return 'ar'
        
        # Hindi/Devanagari (common in UAE)
        if re.search(r'[\u0900-\u097F]', text_clean):
            logger.info("🇮🇳 Detected: Hindi")
            return 'hi'
        
        # Urdu (similar to Arabic script but different)
        urdu_chars = len(re.findall(r'[\u0600-\u06FF]', text_clean))
        urdu_markers = ['ہے', 'کے', 'میں', 'کی']
        if urdu_chars > 0 and any(marker in text_clean for marker in urdu_markers):
            logger.info("🇵🇰 Detected: Urdu")
            return 'ur'
        
        # Chinese
        if re.search(r'[\u4E00-\u9FFF]', text_clean):
            # Simplified vs Traditional (basic check)
            traditional_chars = re.search(r'[\u3400-\u4DBF]', text_clean)
            if traditional_chars:
                logger.info("🇹🇼 Detected: Chinese (Traditional)")
                return 'zh-TW'
            logger.info("🇨🇳 Detected: Chinese (Simplified)")
            return 'zh-CN'
        
        # Japanese
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text_clean):
            logger.info("🇯🇵 Detected: Japanese")
            return 'ja'
        
        # Korean
        if re.search(r'[\uAC00-\uD7AF]', text_clean):
            logger.info("🇰🇷 Detected: Korean")
            return 'ko'
        
        # Russian/Cyrillic
        if re.search(r'[\u0400-\u04FF]', text_clean):
            logger.info("🇷🇺 Detected: Russian")
            return 'ru'
        
        # Thai
        if re.search(r'[\u0E00-\u0E7F]', text_clean):
            logger.info("🇹🇭 Detected: Thai")
            return 'th'
        
        # Tamil
        if re.search(r'[\u0B80-\u0BFF]', text_clean):
            logger.info("Detected: Tamil")
            return 'ta'
        
        # Telugu
        if re.search(r'[\u0C00-\u0C7F]', text_clean):
            logger.info("Detected: Telugu")
            return 'te'
        
        # Bengali
        if re.search(r'[\u0980-\u09FF]', text_clean):
            logger.info("Detected: Bengali")
            return 'bn'
        
        # Malayalam
        if re.search(r'[\u0D00-\u0D7F]', text_clean):
            logger.info("Detected: Malayalam")
            return 'ml'
        
        # Persian/Farsi
        persian_chars = len(re.findall(r'[\u0600-\u06FF]', text_clean))
        persian_markers = ['است', 'که', 'را']
        if persian_chars > 0 and any(marker in text_clean for marker in persian_markers):
            logger.info("🇮🇷 Detected: Persian/Farsi")
            return 'fa'
        
        # ========================================
        # PRIORITY 2: ML-Based Detection
        # (For Latin scripts: English, French, etc.)
        # ========================================
        
        if self.langdetect_available:
            try:
                from langdetect import detect, detect_langs, LangDetectException
                
                # Set seed for consistency
                import langdetect
                langdetect.DetectorFactory.seed = 0
                
                detected = detect(text_clean)
                
                # Check confidence
                try:
                    langs_probs = detect_langs(text_clean)
                    if langs_probs:
                        confidence = langs_probs[0].prob
                        logger.info(f"🔍 langdetect: {detected} (confidence: {confidence:.1%})")
                        
                        if confidence > 0.7:
                            return detected
                        else:
                            logger.warning(f"⚠️ Low confidence ({confidence:.1%}), using fallback")
                except:
                    pass
                
                return detected
                
            except LangDetectException:
                logger.warning("langdetect failed")
            except Exception as e:
                logger.error(f"langdetect error: {e}")
        
        # ========================================
        # PRIORITY 3: Keyword-Based Detection
        # (Last resort for Latin scripts)
        # ========================================
        
        text_lower = text_clean.lower()
        
        # English keywords
        en_keywords = ['the', 'is', 'are', 'and', 'to', 'of', 'a', 'in', 'show', 'car', 'want', 'buy']
        en_count = sum(1 for word in text_lower.split() if word in en_keywords)
        
        # French keywords
        fr_keywords = ['le', 'la', 'de', 'et', 'un', 'une', 'est', 'pour', 'dans']
        fr_count = sum(1 for word in text_lower.split() if word in fr_keywords)
        
        # Spanish keywords
        es_keywords = ['el', 'la', 'de', 'que', 'y', 'en', 'es', 'por', 'un']
        es_count = sum(1 for word in text_lower.split() if word in es_keywords)
        
        if en_count >= 2:
            logger.info("🔍 Keyword-based: English")
            return 'en'
        elif fr_count >= 2:
            logger.info("🔍 Keyword-based: French")
            return 'fr'
        elif es_count >= 2:
            logger.info("🔍 Keyword-based: Spanish")
            return 'es'
        
        # ========================================
        # DEFAULT: English (UAE business language)
        # ========================================
        logger.warning("⚠️ Could not detect language reliably, defaulting to English")
        return 'en'
    
    def translate_to_english(self, text: str, source_lang: Optional[str] = None) -> str:
        """
        Translate any language to English with fallback handling
        
        Args:
            text: Text to translate
            source_lang: Source language code (auto-detect if None)
        
        Returns:
            Translated text in English
        """
        if not text or not text.strip():
            return text
        
        try:
            # Auto-detect if needed
            if not source_lang:
                source_lang = self.detect_language(text)
            
            # Already English?
            if source_lang in ['en', 'en-US', 'en-GB']:
                logger.info("✅ Text already in English")
                return text
            
            # Normalize regional codes for translation
            # GoogleTranslator doesn't support all regional variants
            source_normalized = self._normalize_lang_code(source_lang)
            
            logger.info(f"🌍 Translating: {source_lang} → en")
            logger.info(f"   Text: '{text[:50]}...'")
            
            # Try translation
            translated = self._translate_with_google(text, source_normalized, 'en')
            
            if translated and translated != text:
                logger.info(f"✅ Translation successful: '{translated[:50]}...'")
                return translated
            else:
                logger.warning("⚠️ Translation returned same text, using original")
                return text
            
        except Exception as e:
            logger.error(f"❌ Translation to English failed: {e}")
            return text  # Graceful degradation
    
    def translate_from_english(self, text: str, target_lang: str) -> str:
        """
        Translate English to target language with regional support
        
        Args:
            text: English text to translate
            target_lang: Target language code (supports regional variants)
        
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        try:
            # Already target language?
            if target_lang in ['en', 'en-US', 'en-GB']:
                logger.info("✅ Target is English, no translation needed")
                return text
            
            # Normalize regional codes
            target_normalized = self._normalize_lang_code(target_lang)
            
            logger.info(f"🌍 Translating: en → {target_lang}")
            logger.info(f"   Text: '{text[:50]}...'")
            
            # Try translation
            translated = self._translate_with_google(text, 'en', target_normalized)
            
            if translated and translated != text:
                logger.info(f"✅ Translation successful: '{translated[:50]}...'")
                return translated
            else:
                logger.warning("⚠️ Translation failed, returning original")
                return text
            
        except Exception as e:
            logger.error(f"❌ Translation from English failed: {e}")
            return text
    
    def _normalize_lang_code(self, lang_code: str) -> str:
        """
        Normalize regional language codes for GoogleTranslator
        
        Examples:
            'ar-AE' → 'ar' (Google doesn't support ar-AE)
            'zh-CN' → 'zh-CN' (Google supports this)
            'pt-BR' → 'pt' (unless specified)
        """
        # Map regional variants to GoogleTranslator codes
        mapping = {
            'ar-AE': 'ar',  # UAE Arabic → Standard Arabic
            'ar-SA': 'ar',  # Saudi Arabic → Standard Arabic
            'ar-EG': 'ar',  # Egyptian Arabic → Standard Arabic
            'zh': 'zh-CN',  # Chinese → Simplified
            'pt': 'pt',     # Portuguese → European (can also use pt-BR)
        }
        
        normalized = mapping.get(lang_code, lang_code)
        
        if normalized != lang_code:
            logger.info(f"📝 Normalized: {lang_code} → {normalized}")
        
        return normalized
    
    def _translate_with_google(self, text: str, source: str, target: str) -> str:
        """
        Translate using Google Translate via deep-translator
        Handles long text with chunking
        """
        try:
            from deep_translator import GoogleTranslator
            
            translator = GoogleTranslator(source=source, target=target)
            
            # Handle long text (Google limit: ~5000 chars)
            max_length = 4500  # Leave some buffer
            
            if len(text) > max_length:
                logger.info(f"📄 Text is long ({len(text)} chars), splitting into chunks...")
                
                # Split by sentences or paragraphs
                chunks = self._split_text(text, max_length)
                logger.info(f"   Created {len(chunks)} chunks")
                
                translated_chunks = []
                for i, chunk in enumerate(chunks):
                    try:
                        translated = translator.translate(chunk)
                        translated_chunks.append(translated)
                        logger.info(f"   ✅ Chunk {i+1}/{len(chunks)} translated")
                    except Exception as e:
                        logger.error(f"   ❌ Chunk {i+1} failed: {e}")
                        translated_chunks.append(chunk)  # Use original
                
                return ' '.join(translated_chunks)
            
            else:
                # Single translation
                return translator.translate(text)
            
        except Exception as e:
            logger.error(f"❌ Google Translate error: {e}")
            return text
    
    def _split_text(self, text: str, max_length: int) -> list:
        """Split text into chunks at sentence boundaries"""
        # Try to split at sentence boundaries
        sentences = re.split(r'[.!?]\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate between any two languages with regional support
        
        Args:
            text: Text to translate
            source_lang: Source language code (supports regional)
            target_lang: Target language code (supports regional)
        
        Returns:
            Translated text
        """
        try:
            if source_lang == target_lang:
                return text
            
            # Normalize codes
            source_norm = self._normalize_lang_code(source_lang)
            target_norm = self._normalize_lang_code(target_lang)
            
            return self._translate_with_google(text, source_norm, target_norm)
            
        except Exception as e:
            logger.error(f"❌ Translation error: {e}")
            return text
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported languages with regional variants"""
        return self.supported_languages


# Test function
def test_translation_system():
    """Test translation system with Dubai/UAE focus"""
    print("=" * 70)
    print("TESTING TRANSLATION SYSTEM - UAE/DUBAI EDITION")
    print("=" * 70)
    
    translator = TranslationSystem()
    
    # Test language detection (Dubai-specific)
    print("\n🔍 LANGUAGE DETECTION TESTS")
    print("-" * 70)
    
    test_texts = [
        "I want to buy a luxury SUV",  # English
        "أريد شراء سيارة فاخرة",  # Standard Arabic
        "أبحث عن سيارة في دبي",  # Arabic with Dubai mention
        "मुझे एक कार चाहिए",  # Hindi
        "میں ایک گاڑی خریدنا چاہتا ہوں",  # Urdu
        "Je veux acheter une voiture",  # French
        "show me سيارات BMW",  # Mixed English-Arabic (common in UAE!)
        "luxury cars under 200000 dirham",  # English with context
    ]
    
    for text in test_texts:
        detected = translator.detect_language(text)
        lang_name = translator.supported_languages.get(detected, detected)
        print(f"Text: {text[:40]:40s} → {detected:8s} ({lang_name})")
    
    # Test translations
    print("\n🌍 TRANSLATION TESTS")
    print("-" * 70)
    
    test_cases = [
        ("Show me luxury cars under 200,000 AED", "en", "ar", "English → Arabic"),
        ("أريد شراء سيارة BMW", "ar", "en", "Arabic → English"),
        ("मुझे Toyota Camry चाहिए", "hi", "en", "Hindi → English"),
        ("Je cherche une voiture de luxe", "fr", "en", "French → English"),
    ]
    
    for text, source, target, description in test_cases:
        print(f"\n{description}:")
        print(f"  Original: {text}")
        
        try:
            translated = translator.translate(text, source, target)
            print(f"  Translated: {translated}")
            print(f"  ✅ Success")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_translation_system()