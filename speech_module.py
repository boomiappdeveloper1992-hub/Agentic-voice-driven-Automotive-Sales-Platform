"""
speech_module.py - Enhanced Multilingual Speech System
- Whisper ASR (99 languages)
- Multiple TTS providers with fallbacks
- Full language detection and mapping
"""

import logging
import os
from typing import Optional, Dict
import tempfile
import time
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpeechSystem:
    """Production speech system with full multilingual support"""
    
    def __init__(self):
        """Initialize speech system with all providers"""
        self.whisper_model = None
        self.openai_client = None
        self.edge_available = False
        self.pyttsx3_engine = None
        
        # Rate limiting for gTTS
        self.gtts_last_request = 0
        self.gtts_min_delay = 3
        self.gtts_fail_count = 0
        self.gtts_max_fails = 3
        self.gtts_cooldown_until = None
        
        # Whisper language mapping
        self.whisper_languages = {
            'en': 'English', 'ar': 'Arabic', 'hi': 'Hindi', 'ur': 'Urdu',
            'fr': 'French', 'es': 'Spanish', 'de': 'German', 'it': 'Italian',
            'pt': 'Portuguese', 'ru': 'Russian', 'zh': 'Chinese', 'ja': 'Japanese',
            'ko': 'Korean', 'th': 'Thai', 'vi': 'Vietnamese', 'ta': 'Tamil',
            'te': 'Telugu', 'ml': 'Malayalam', 'bn': 'Bengali', 'fa': 'Persian',
            'tr': 'Turkish', 'he': 'Hebrew', 'el': 'Greek', 'nl': 'Dutch',
            'sv': 'Swedish', 'no': 'Norwegian', 'da': 'Danish', 'fi': 'Finnish',
            'pl': 'Polish', 'uk': 'Ukrainian', 'cs': 'Czech', 'ro': 'Romanian',
        }
        
        self._initialize_whisper()
        self._initialize_openai()
        self._initialize_edge_tts()
        self._initialize_pyttsx3()
    
    def _initialize_whisper(self):
        """Initialize Whisper for ASR"""
        try:
            import whisper
            logger.info("📥 Loading Whisper model...")
            # Use 'base' for balance between speed and accuracy
            # Options: tiny, base, small, medium, large
            self.whisper_model = whisper.load_model("base")
            logger.info(f"✅ Whisper loaded - Supports {len(self.whisper_languages)} languages")
        except Exception as e:
            logger.warning(f"⚠️ Whisper not available: {e}")
            self.whisper_model = None
    
    def _initialize_openai(self):
        """Initialize OpenAI for TTS"""
        try:
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("✅ OpenAI TTS initialized")
            else:
                logger.info("ℹ️ OPENAI_API_KEY not set - will use free alternatives")
                self.openai_client = None
        except Exception as e:
            logger.info(f"ℹ️ OpenAI not available: {e}")
            self.openai_client = None
    
    def _initialize_edge_tts(self):
        """Initialize Edge TTS"""
        try:
            import edge_tts
            self.edge_available = True
            logger.info("✅ Edge TTS available (free Microsoft TTS)")
        except ImportError:
            logger.info("ℹ️ Edge TTS not installed (pip install edge-tts)")
            self.edge_available = False
    
    def _initialize_pyttsx3(self):
        """Initialize pyttsx3 offline TTS"""
        try:
            import pyttsx3
            self.pyttsx3_engine = pyttsx3.init()
            logger.info("✅ pyttsx3 initialized (offline TTS)")
        except Exception as e:
            logger.info(f"ℹ️ pyttsx3 not available: {e}")
            self.pyttsx3_engine = None
    
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict[str, str]:
        """
        Convert speech to text using Whisper (supports 99 languages)
        
        Args:
            audio_path: Path to audio file
            language: Optional language hint (ISO 639-1 code or 'auto')
        
        Returns:
            Dict with:
                - 'text': Transcribed text
                - 'detected_language': Detected language code
                - 'confidence': Detection confidence (if available)
        """
        try:
            if not self.whisper_model:
                logger.error("❌ Whisper model not loaded")
                return {"text": "", "detected_language": "en", "confidence": 0.0}
            
            logger.info(f"🎤 Transcribing audio: {audio_path}")
            
            # Check file exists
            if not os.path.exists(audio_path):
                logger.error(f"❌ Audio file not found: {audio_path}")
                return {"text": "", "detected_language": "en", "confidence": 0.0}
            
            # Load audio
            try:
                import librosa
                audio_data, sr = librosa.load(audio_path, sr=16000)
                logger.info(f"   📊 Audio loaded: {len(audio_data)} samples, {sr}Hz")
            except Exception as e:
                logger.warning(f"⚠️ Librosa failed, using Whisper's loader: {e}")
                audio_data = audio_path
            
            # Prepare transcription options
            transcribe_options = {
                'task': 'transcribe',
                'fp16': False,
                'verbose': False,
                'temperature': 0.0,  # More deterministic
            }
            
            # Add language hint if provided
            if language and language not in ['auto', 'unknown']:
                whisper_lang = self._map_to_whisper_lang(language)
                if whisper_lang in self.whisper_languages:
                    transcribe_options['language'] = whisper_lang
                    logger.info(f"   🌍 Language hint: {language} → {whisper_lang}")
                else:
                    logger.warning(f"⚠️ Language '{language}' not supported, auto-detecting")
            else:
                logger.info(f"   🔍 Auto-detecting language...")
            
            # Transcribe with Whisper
            result = self.whisper_model.transcribe(audio_data, **transcribe_options)
            
            text = result['text'].strip()
            detected_lang = result.get('language', 'en')
            
            # Get language name
            lang_name = self.whisper_languages.get(detected_lang, detected_lang.upper())
            
            logger.info(f"✅ Transcription complete")
            logger.info(f"   🌍 Detected: {detected_lang} ({lang_name})")
            logger.info(f"   📝 Text: '{text[:100]}{'...' if len(text) > 100 else ''}'")
            
            return {
                "text": text,
                "detected_language": detected_lang,
                "confidence": 1.0  # Whisper doesn't provide confidence, assume high
            }
            
        except Exception as e:
            logger.error(f"❌ Transcription error: {e}", exc_info=True)
            return {"text": "", "detected_language": "en", "confidence": 0.0}
    
    def _map_to_whisper_lang(self, lang_code: str) -> str:
        """
        Map language codes to Whisper's expected format
        Handles regional variants (e.g., ar-AE → ar)
        """
        # Regional variant mapping
        mapping = {
            'ar-AE': 'ar', 'ar-SA': 'ar', 'ar-EG': 'ar',  # Arabic variants
            'zh-CN': 'zh', 'zh-TW': 'zh',  # Chinese variants
            'pt-BR': 'pt',  # Portuguese (Brazil)
            'en-US': 'en', 'en-GB': 'en',  # English variants
        }
        
        # Return mapped code or base language (first 2 chars)
        if lang_code in mapping:
            return mapping[lang_code]
        
        # Extract base language (e.g., 'ar-AE' → 'ar')
        base_lang = lang_code.split('-')[0]
        return base_lang
    
    def synthesize_speech(self, text: str, language: str = 'en', voice: str = 'alloy') -> Optional[str]:
        """
        Convert text to speech with multiple fallback providers
        
        Priority:
        1. OpenAI TTS (best quality, requires API key, English only)
        2. Edge TTS (free, good quality, many languages)
        3. gTTS (free, rate limited, many languages)
        4. pyttsx3 (offline, basic quality)
        
        Args:
            text: Text to synthesize
            language: Language code (ISO 639-1)
            voice: Voice name (OpenAI: alloy, echo, fable, onyx, nova, shimmer)
        
        Returns:
            Path to generated audio file or None
        """
        if not text or len(text) > 1000:
            logger.warning("⚠️ Text too long or empty, skipping TTS")
            return None
        
        try:
            # Normalize language code
            lang_normalized = self._map_to_whisper_lang(language)
            
            logger.info(f"🔊 Generating speech in {lang_normalized}...")
            
            # Priority 1: OpenAI TTS (if available and English)
            if self.openai_client and lang_normalized == 'en':
                result = self._synthesize_openai(text, voice)
                if result:
                    return result
                logger.warning("⚠️ OpenAI TTS failed, trying fallbacks...")
            
            # Priority 2: Edge TTS (if available)
            if self.edge_available:
                result = self._synthesize_edge_tts(text, lang_normalized)
                if result:
                    return result
                logger.warning("⚠️ Edge TTS failed, trying fallbacks...")
            
            # Priority 3: gTTS (with rate limiting)
            if self._can_use_gtts():
                result = self._synthesize_gtts(text, lang_normalized)
                if result:
                    return result
                logger.warning("⚠️ gTTS failed, trying last fallback...")
            else:
                logger.warning("⚠️ gTTS in cooldown, skipping...")
            
            # Priority 4: pyttsx3 (offline)
            if self.pyttsx3_engine and lang_normalized == 'en':
                result = self._synthesize_pyttsx3(text)
                if result:
                    return result
            
            logger.error("❌ All TTS providers failed")
            return None
            
        except Exception as e:
            logger.error(f"❌ TTS error: {e}", exc_info=True)
            return None
    
    def _can_use_gtts(self) -> bool:
        """Check if gTTS is available (not in cooldown)"""
        if self.gtts_cooldown_until:
            if datetime.now() < self.gtts_cooldown_until:
                remaining = (self.gtts_cooldown_until - datetime.now()).seconds
                logger.debug(f"⏳ gTTS cooldown: {remaining}s remaining")
                return False
            else:
                logger.info("✅ gTTS cooldown expired")
                self.gtts_cooldown_until = None
                self.gtts_fail_count = 0
        
        if self.gtts_fail_count >= self.gtts_max_fails:
            logger.warning(f"⚠️ gTTS disabled: {self.gtts_fail_count} failures")
            return False
        
        return True
    
    def _synthesize_openai(self, text: str, voice: str) -> Optional[str]:
        """OpenAI TTS (premium quality, English only)"""
        try:
            logger.info("   🎤 Trying OpenAI TTS...")
            
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text[:4096]
            )
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            response.stream_to_file(temp_file.name)
            
            logger.info(f"   ✅ OpenAI TTS: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"   ❌ OpenAI TTS error: {e}")
            return None
    
    def _synthesize_edge_tts(self, text: str, language: str) -> Optional[str]:
        """Edge TTS (free Microsoft TTS, many languages)"""
        try:
            import edge_tts
            import asyncio
            
            logger.info(f"   🎤 Trying Edge TTS ({language})...")
            
            # Voice mapping for common languages
            voice_map = {
                'en': 'en-US-AriaNeural',
                'ar': 'ar-SA-ZariyahNeural',
                'hi': 'hi-IN-SwaraNeural',
                'ur': 'ur-PK-AsadNeural',
                'fr': 'fr-FR-DeniseNeural',
                'es': 'es-ES-ElviraNeural',
                'de': 'de-DE-KatjaNeural',
                'it': 'it-IT-ElsaNeural',
                'pt': 'pt-BR-FranciscaNeural',
                'ru': 'ru-RU-SvetlanaNeural',
                'zh': 'zh-CN-XiaoxiaoNeural',
                'ja': 'ja-JP-NanamiNeural',
                'ko': 'ko-KR-SunHiNeural',
                'th': 'th-TH-PremwadeeNeural',
                'vi': 'vi-VN-HoaiMyNeural',
                'ta': 'ta-IN-PallaviNeural',
                'te': 'te-IN-ShrutiNeural',
            }
            
            voice = voice_map.get(language, 'en-US-AriaNeural')
            
            async def _generate():
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(temp_file.name)
                return temp_file.name
            
            audio_file = asyncio.run(_generate())
            logger.info(f"   ✅ Edge TTS: {audio_file}")
            return audio_file
            
        except Exception as e:
            logger.error(f"   ❌ Edge TTS error: {e}")
            return None
    
    def _synthesize_gtts(self, text: str, language: str) -> Optional[str]:
        """gTTS with rate limiting"""
        try:
            from gtts import gTTS
            
            # Rate limiting
            current_time = time.time()
            elapsed = current_time - self.gtts_last_request
            
            if elapsed < self.gtts_min_delay:
                wait_time = self.gtts_min_delay - elapsed
                logger.info(f"   ⏳ Rate limit: waiting {wait_time:.1f}s")
                time.sleep(wait_time)
            
            logger.info(f"   🎤 Trying gTTS ({language})...")
            
            # Language mapping
            lang_map = {
                'en': 'en', 'ar': 'ar', 'hi': 'hi', 'ur': 'ur',
                'fr': 'fr', 'es': 'es', 'de': 'de', 'it': 'it',
                'pt': 'pt', 'ru': 'ru', 'zh': 'zh-CN', 'ja': 'ja',
                'ko': 'ko', 'th': 'th', 'vi': 'vi', 'ta': 'ta', 'te': 'te'
            }
            
            tts_lang = lang_map.get(language, 'en')
            
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            tts.save(temp_file.name)
            
            self.gtts_last_request = time.time()
            self.gtts_fail_count = 0
            
            logger.info(f"   ✅ gTTS: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            error_str = str(e)
            
            if "429" in error_str or "Too Many Requests" in error_str:
                self.gtts_fail_count += 1
                logger.error(f"   ⚠️ gTTS rate limit (fail {self.gtts_fail_count}/{self.gtts_max_fails})")
                
                if self.gtts_fail_count >= self.gtts_max_fails:
                    self.gtts_cooldown_until = datetime.now() + timedelta(minutes=5)
                    logger.warning("   🔒 gTTS locked for 5 minutes")
                
                return None
            
            logger.error(f"   ❌ gTTS error: {e}")
            self.gtts_fail_count += 1
            return None
    
    def _synthesize_pyttsx3(self, text: str) -> Optional[str]:
        """pyttsx3 offline TTS (English only, basic quality)"""
        try:
            logger.info("   🎤 Trying pyttsx3 (offline)...")
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            
            self.pyttsx3_engine.save_to_file(text, temp_file.name)
            self.pyttsx3_engine.runAndWait()
            
            logger.info(f"   ✅ pyttsx3: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"   ❌ pyttsx3 error: {e}")
            return None
    
    def speech_to_speech(self, audio_path: str, target_language: str = 'en') -> Optional[str]:
        """
        Complete speech-to-speech pipeline
        1. Transcribe input audio
        2. Translate if needed (handled by translation module)
        3. Synthesize in target language
        """
        try:
            # Transcribe
            result = self.transcribe_audio(audio_path)
            if not result or not result['text']:
                return None
            
            text = result['text']
            
            # Synthesize in target language
            output_audio = self.synthesize_speech(text, target_language)
            
            return output_audio
            
        except Exception as e:
            logger.error(f"❌ Speech-to-speech error: {e}")
            return None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get supported languages for Whisper ASR"""
        return self.whisper_languages


# Test function
def test_speech_system():
    """Test complete multilingual speech system"""
    print("=" * 70)
    print("TESTING MULTILINGUAL SPEECH SYSTEM")
    print("=" * 70)
    
    speech = SpeechSystem()
    
    # Show providers
    print("\n📊 Available Providers:")
    print(f"   Whisper ASR: {'✅' if speech.whisper_model else '❌'}")
    print(f"   OpenAI TTS: {'✅' if speech.openai_client else '❌'}")
    print(f"   Edge TTS: {'✅' if speech.edge_available else '❌'}")
    print(f"   gTTS: ✅ (with rate limiting)")
    print(f"   pyttsx3: {'✅' if speech.pyttsx3_engine else '❌'}")
    
    # Test TTS in multiple languages
    test_texts = [
        ("Hello, how can I help you find a car today?", 'en', "English"),
        ("مرحبا، كيف يمكنني مساعدتك اليوم؟", 'ar', "Arabic"),
        ("नमस्ते, मैं आपकी कैसे मदद कर सकता हूं?", 'hi', "Hindi"),
        ("Bonjour, comment puis-je vous aider?", 'fr', "French"),
    ]
    
    print(f"\n🔊 Testing TTS (Multiple Languages):")
    print("-" * 70)
    
    for text, lang, lang_name in test_texts:
        print(f"\n{lang_name} ({lang}):")
        print(f"   Text: {text[:50]}...")
        
        audio_file = speech.synthesize_speech(text, language=lang)
        
        if audio_file:
            print(f"   ✅ Generated: {audio_file}")
        else:
            print(f"   ❌ Failed")
    
    print("\n" + "=" * 70)
    print("✅ SPEECH SYSTEM TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_speech_system()