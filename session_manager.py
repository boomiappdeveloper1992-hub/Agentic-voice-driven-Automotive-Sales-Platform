"""
session_manager.py - Browser Session Management with Cookies
Handles persistent sessions across page refreshes
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionManager:
    """Manage browser sessions with JWT tokens"""
    
    def __init__(self, secret_key: str = "automotive-ai-secret-2025"):
        """
        Initialize session manager
        
        Args:
            secret_key: Secret key for JWT signing
        """
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.session_duration_hours = 24 * 7  # 7 days
        logger.info("✅ Session Manager initialized")
    
    def create_session_token(self, user_id: str, email: Optional[str] = None, 
                            session_id: Optional[str] = None) -> str:
        """
        Create JWT session token
        
        Args:
            user_id: Unique user identifier
            email: Optional email
            session_id: Optional session ID
        
        Returns:
            JWT token string
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                import uuid
                session_id = f"session_{uuid.uuid4().hex[:16]}"
            
            # Create payload
            payload = {
                'user_id': user_id,
                'session_id': session_id,
                'email': email,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=self.session_duration_hours)).isoformat()
            }
            
            # Generate token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            logger.info(f"🔑 Created session token for user: {user_id}, session: {session_id[:20]}...")
            
            return token
            
        except Exception as e:
            logger.error(f"❌ Token creation error: {e}")
            return None
    
    def verify_session_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded payload or None if invalid
        """
        try:
            if not token:
                return None
            
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            expires_at = datetime.fromisoformat(payload['expires_at'])
            if datetime.now() > expires_at:
                logger.warning(f"⚠️ Token expired for user: {payload.get('user_id')}")
                return None
            
            logger.info(f"✅ Valid session token for user: {payload.get('user_id')}")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Token verification error: {e}")
            return None
    
    def generate_user_id(self, identifier: str = None) -> str:
        """
        Generate anonymous user ID from browser fingerprint
        
        Args:
            identifier: Browser identifier (user agent, IP, etc.)
        
        Returns:
            Hashed user ID
        """
        if not identifier:
            import uuid
            identifier = str(uuid.uuid4())
        
        # Hash to create consistent ID
        user_id = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        return f"user_{user_id}"
    
    def refresh_token(self, old_token: str) -> Optional[str]:
        """
        Refresh an existing token
        
        Args:
            old_token: Existing JWT token
        
        Returns:
            New token or None
        """
        payload = self.verify_session_token(old_token)
        
        if not payload:
            return None
        
        # Create new token with same data
        return self.create_session_token(
            user_id=payload['user_id'],
            email=payload.get('email'),
            session_id=payload['session_id']
        )


# Singleton instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get singleton session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


# Test function
def test_session_manager():
    """Test session management"""
    print("\n" + "="*60)
    print("🧪 TESTING SESSION MANAGER")
    print("="*60)
    
    manager = get_session_manager()
    
    # Test 1: Create token
    print("\n1️⃣ Creating session token...")
    token = manager.create_session_token("test_user", email="test@example.com")
    print(f"   Token: {token[:50]}...")
    
    # Test 2: Verify token
    print("\n2️⃣ Verifying token...")
    payload = manager.verify_session_token(token)
    if payload:
        print(f"   ✅ Valid! User: {payload['user_id']}, Session: {payload['session_id']}")
    else:
        print(f"   ❌ Invalid token")
    
    # Test 3: Generate user ID
    print("\n3️⃣ Generating anonymous user ID...")
    user_id = manager.generate_user_id("Mozilla/5.0...")
    print(f"   User ID: {user_id}")
    
    print("\n" + "="*60)
    print("✅ Session Manager Test Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_session_manager()