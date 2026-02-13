"""
setup.py - Automated Setup and Initialization Script
Run this first to set up the entire system
"""

import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_python_version():
    """Check if Python version is 3.9+"""
    if sys.version_info < (3, 9):
        logger.error("Python 3.9 or higher is required!")
        logger.error(f"Current version: {sys.version}")
        return False
    logger.info(f"✅ Python version: {sys.version.split()[0]}")
    return True


def install_dependencies():
    """Install required dependencies"""
    logger.info("Installing dependencies...")
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Dependencies installed successfully")
            return True
        else:
            logger.error(f"❌ Installation failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error installing dependencies: {e}")
        return False


def create_env_file():
    """Create .env file if it doesn't exist"""
    env_path = Path(".env")
    
    if env_path.exists():
        logger.info("✅ .env file already exists")
        return True
    
    logger.info("Creating .env file...")
    
    env_content = """# Neo4j Configuration
NEO4J_URI=neo4j+s://50ad6469.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=xr2vCSD0RHLbfb3Bzzlpds04tm3fARSgvGHqZRkfevc
NEO4J_DATABASE=neo4j
AURA_INSTANCEID=50ad6469
AURA_INSTANCENAME=VoiceAssistance_multilingual

# OpenAI Configuration (Optional - for premium TTS)
# OPENAI_API_KEY=your_openai_api_key_here

# Hugging Face (Optional - for private models)
# HF_TOKEN=your_huggingface_token_here

# Application Settings
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SERVER_PORT=7860
"""
    
    try:
        with open(env_path, 'w') as f:
            f.write(env_content)
        logger.info("✅ .env file created")
        return True
    except Exception as e:
        logger.error(f"❌ Error creating .env file: {e}")
        return False


def create_directories():
    """Create necessary directories"""
    directories = [
        "data",
        "data/vehicles",
        "data/embeddings",
        "logs",
        "temp"
    ]
    
    logger.info("Creating directory structure...")
    
    try:
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info("✅ Directories created")
        return True
    except Exception as e:
        logger.error(f"❌ Error creating directories: {e}")
        return False


def test_neo4j_connection():
    """Test Neo4j connection"""
    logger.info("Testing Neo4j connection...")
    
    try:
        from neo4j_handler import Neo4jHandler
        
        handler = Neo4jHandler()
        handler.close()
        
        logger.info("✅ Neo4j connection successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Neo4j connection failed: {e}")
        logger.error("Please check your Neo4j credentials in .env file")
        return False


def initialize_database():
    """Initialize Neo4j database with schema and data"""
    logger.info("Initializing Neo4j database...")
    
    try:
        from neo4j_handler import Neo4jHandler
        
        handler = Neo4jHandler()
        
        # Seed data
        logger.info("Seeding initial data...")
        handler.seed_initial_data()
        
        # Get stats
        stats = handler.get_knowledge_graph_stats()
        logger.info(f"✅ Database initialized:")
        logger.info(f"   - Leads: {stats['leads']}")
        logger.info(f"   - Vehicles: {stats['vehicles']}")
        logger.info(f"   - Appointments: {stats['appointments']}")
        logger.info(f"   - Relationships: {stats['relationships']}")
        
        handler.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


def test_models():
    """Test if AI models can be loaded"""
    logger.info("Testing AI models...")
    
    tests = {
        'Sentiment Analysis': False,
        'Embeddings': False,
        'Translation': False
    }
    
    # Test sentiment
    try:
        from sentiment_module import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("This is a test")
        tests['Sentiment Analysis'] = True
        logger.info("✅ Sentiment Analysis model loaded")
    except Exception as e:
        logger.warning(f"⚠️  Sentiment model: {e}")
    
    # Test embeddings
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        tests['Embeddings'] = True
        logger.info("✅ Embedding model loaded")
    except Exception as e:
        logger.warning(f"⚠️  Embedding model: {e}")
    
    # Test translation
    try:
        from translation_module import TranslationSystem
        translator = TranslationSystem()
        tests['Translation'] = True
        logger.info("✅ Translation system loaded")
    except Exception as e:
        logger.warning(f"⚠️  Translation system: {e}")
    
    return all(tests.values())


def display_next_steps():
    """Display next steps for the user"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print("\n📋 Next Steps:\n")
    print("1. Review the .env file and update if needed")
    print("   - Add OPENAI_API_KEY for premium TTS (optional)")
    print("\n2. Start the application:")
    print("   python app.py")
    print("\n3. Access the application:")
    print("   http://localhost:7860")
    print("\n4. Admin Dashboard Login:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n5. Test with sample queries:")
    print("   - 'Show me luxury SUVs under 200000 AED'")
    print("   - 'I want to book a test drive'")
    print("   - 'What electric vehicles do you have?'")
    print("\n📚 Documentation:")
    print("   - README.md - Full documentation")
    print("   - GitHub: https://github.com/your-username/automotive-ai")
    print("\n💡 Tips:")
    print("   - Use voice input for best experience")
    print("   - Try different languages (auto-detected)")
    print("   - Explore the Knowledge Graph in Admin panel")
    print("\n" + "="*60)
    print("Good luck with your MTech presentation! 🎓")
    print("="*60 + "\n")


def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("🚗 AGENTIC AI AUTOMOTIVE PLATFORM - SETUP")
    print("="*60 + "\n")
    
    steps = [
        ("Checking Python version", check_python_version),
        ("Creating .env file", create_env_file),
        ("Creating directories", create_directories),
        ("Installing dependencies", install_dependencies),
        ("Testing Neo4j connection", test_neo4j_connection),
        ("Initializing database", initialize_database),
        ("Testing AI models", test_models),
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        print(f"\n📌 {step_name}...")
        try:
            if not step_func():
                failed_steps.append(step_name)
                logger.error(f"❌ {step_name} failed")
        except Exception as e:
            logger.error(f"❌ {step_name} failed: {e}")
            failed_steps.append(step_name)
    
    print("\n" + "="*60)
    
    if not failed_steps:
        display_next_steps()
        return 0
    else:
        print("⚠️  SETUP COMPLETED WITH WARNINGS")
        print("="*60)
        print("\nFailed steps:")
        for step in failed_steps:
            print(f"  ❌ {step}")
        print("\nThe application may still work with reduced functionality.")
        print("Please check the errors above and fix them if needed.\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)