"""
Financial RAG Smart Initialization
✅ Checks for existing Q&A JSON first (fast path)
✅ Only generates if needed (slow path)
✅ Guaranteed repository root storage
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

def initialize_financial_rag():
    """
    Smart Financial RAG initialization with caching
    
    Fast Path (< 1 second):
    - Checks if automotive_qa_index.json exists in repository root
    - If yes, loads pre-generated Q&A
    
    Slow Path (2-3 minutes):
    - Generates Q&A from PDFs
    - Saves to repository root
    """
    
    # ✅ REPOSITORY ROOT PATH (persistent, free, visible in Files tab)
    QA_JSON_FILE = "automotive_qa_index.json"  # Repository root
    
    logger.info("="*60)
    logger.info("🚀 Initializing Financial RAG Module")
    logger.info("="*60)
    
    try:
        from financial_rag_module import AutomotiveFinancialRAG
        
        # ═══════════════════════════════════════════════════════════
        # FAST PATH: Load from existing JSON
        # ═══════════════════════════════════════════════════════════
        if os.path.exists(QA_JSON_FILE):
            file_size_kb = os.path.getsize(QA_JSON_FILE) / 1024
            abs_path = os.path.abspath(QA_JSON_FILE)
            
            logger.info("⚡ FAST PATH: Found existing Q&A file!")
            logger.info(f"📄 File: {QA_JSON_FILE}")
            logger.info(f"📍 Path: {abs_path}")
            logger.info(f"💾 Size: {file_size_kb:.2f} KB")
            logger.info("⏱️ Loading in <1 second...")
            
            # Initialize WITHOUT Q&A generation
            financial_rag = AutomotiveFinancialRAG(skip_qa_generation=True)
            
            # Load from file
            try:
                with open(QA_JSON_FILE, 'r', encoding='utf-8') as f:
                    financial_rag.qa_index = json.load(f)
                
                # Update the path reference
                financial_rag.qa_json_path = QA_JSON_FILE
                
                logger.info(f"✅ Loaded {len(financial_rag.qa_index)} Q&A pairs")
                
                # Show statistics
                if financial_rag.qa_index:
                    companies = {}
                    for qa in financial_rag.qa_index:
                        company = qa.get('company', 'Unknown')
                        companies[company] = companies.get(company, 0) + 1
                    
                    logger.info("🏢 Q&A Distribution:")
                    for company, count in sorted(companies.items()):
                        logger.info(f"   • {company}: {count} pairs")
                
                logger.info("="*60)
                logger.info("✅ Financial RAG Ready (Fast Mode)")
                logger.info("⚡ Initialization: <1 second")
                logger.info("="*60)
                
                return financial_rag
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in {QA_JSON_FILE}: {e}")
                logger.info("🔨 Will regenerate Q&A...")
                # Fall through to slow path
                
            except Exception as e:
                logger.error(f"❌ Error loading Q&A: {e}")
                logger.info("🔨 Will regenerate Q&A...")
                # Fall through to slow path
        
        # ═══════════════════════════════════════════════════════════
        # SLOW PATH: Generate Q&A from PDFs
        # ═══════════════════════════════════════════════════════════
        logger.info("🔨 SLOW PATH: Generating Q&A from PDFs...")
        logger.info("⏱️ This will take 2-3 minutes (one-time setup)")
        logger.info("💡 Next restart will be <1 second!")
        
        # Full initialization (will generate Q&A)
        financial_rag = AutomotiveFinancialRAG()
        
        # ✅ FORCE SAVE TO REPOSITORY ROOT
        if financial_rag.qa_index and len(financial_rag.qa_index) > 0:
            try:
                logger.info("💾 Saving Q&A to repository root...")
                
                # Save with explicit path
                with open(QA_JSON_FILE, 'w', encoding='utf-8') as f:
                    json.dump(financial_rag.qa_index, f, indent=2, ensure_ascii=False)
                
                # Verify file exists
                if os.path.exists(QA_JSON_FILE):
                    file_size_kb = os.path.getsize(QA_JSON_FILE) / 1024
                    abs_path = os.path.abspath(QA_JSON_FILE)
                    
                    logger.info("="*60)
                    logger.info("✅ Q&A JSON SAVED TO REPOSITORY ROOT!")
                    logger.info("="*60)
                    logger.info(f"📄 File: {QA_JSON_FILE}")
                    logger.info(f"📍 Absolute path: {abs_path}")
                    logger.info(f"📊 Q&A Pairs: {len(financial_rag.qa_index)}")
                    logger.info(f"💾 File size: {file_size_kb:.2f} KB")
                    
                    # Count per company
                    companies = {}
                    for qa in financial_rag.qa_index:
                        company = qa.get('company', 'Unknown')
                        companies[company] = companies.get(company, 0) + 1
                    
                    logger.info("🏢 Q&A Distribution:")
                    for company, count in sorted(companies.items()):
                        logger.info(f"   • {company}: {count} pairs")
                    
                    logger.info("="*60)
                    logger.info("🔥 NEXT STEPS TO MAKE PERSISTENT:")
                    logger.info("="*60)
                    logger.info("1. Go to your Space's 'Files' tab")
                    logger.info(f"2. You should see: {QA_JSON_FILE}")
                    logger.info("3. Click the file")
                    logger.info("4. Click 'Commit to main' button")
                    logger.info("5. Restart Space → loads in <1 second!")
                    logger.info("="*60)
                    
                    # Update the module's path reference
                    financial_rag.qa_json_path = QA_JSON_FILE
                    
                else:
                    logger.error(f"❌ File was not created: {QA_JSON_FILE}")
                    logger.error("❌ Check file permissions!")
                    
            except Exception as e:
                logger.error(f"❌ Failed to save Q&A JSON: {e}")
                logger.error(f"   Path: {QA_JSON_FILE}")
                logger.error(f"   Working directory: {os.getcwd()}")
                
                # Try alternative locations
                alternative_paths = [
                    "./automotive_qa_index.json",
                    "/tmp/automotive_qa_index.json",
                    "/data/automotive_qa_index.json"
                ]
                
                for alt_path in alternative_paths:
                    try:
                        logger.info(f"🔄 Trying alternative: {alt_path}")
                        os.makedirs(os.path.dirname(alt_path) or '.', exist_ok=True)
                        
                        with open(alt_path, 'w', encoding='utf-8') as f:
                            json.dump(financial_rag.qa_index, f, indent=2, ensure_ascii=False)
                        
                        if os.path.exists(alt_path):
                            logger.info(f"✅ Saved to: {alt_path}")
                            financial_rag.qa_json_path = alt_path
                            break
                    except:
                        continue
        else:
            logger.warning("⚠️ No Q&A pairs generated")
        
        logger.info("="*60)
        logger.info("✅ Financial RAG Ready")
        logger.info("="*60)
        
        return financial_rag
        
    except ImportError as e:
        logger.error(f"❌ Cannot import financial_rag_module: {e}")
        logger.error("💡 Make sure financial_rag_module.py is in the repository")
        return None
        
    except Exception as e:
        logger.error(f"❌ Financial RAG initialization failed: {e}")
        logger.error(f"   Full error: {str(e)}")
        
        import traceback
        logger.error(traceback.format_exc())
        
        return None


# ==========================================
# DIAGNOSTIC FUNCTION
# ==========================================

def check_qa_json_status():
    """
    Check if Q&A JSON exists and show status
    Useful for debugging
    """
    logger.info("="*60)
    logger.info("🔍 Q&A JSON File Check")
    logger.info("="*60)
    
    locations = [
        ("Repository Root", "./automotive_qa_index.json"),
        ("Current Directory", "automotive_qa_index.json"),
        ("App Root", "/app/automotive_qa_index.json"),
        ("/tmp", "/tmp/automotive_qa_index.json"),
        ("/tmp/outputs", "/tmp/outputs/automotive_qa_index.json"),
        ("/data", "/data/automotive_qa_index.json"),
        ("/data/outputs", "/data/outputs/automotive_qa_index.json")
    ]
    
    found_files = []
    
    for name, path in locations:
        if os.path.exists(path):
            file_size = os.path.getsize(path) / 1024  # KB
            abs_path = os.path.abspath(path)
            
            logger.info(f"✅ Found at {name}:")
            logger.info(f"   Path: {path}")
            logger.info(f"   Absolute: {abs_path}")
            logger.info(f"   Size: {file_size:.2f} KB")
            
            # Try to read Q&A count
            try:
                with open(path, 'r') as f:
                    qa_data = json.load(f)
                    logger.info(f"   Q&A Pairs: {len(qa_data)}")
                    
                    if qa_data:
                        companies = set(qa.get('company', 'Unknown') for qa in qa_data)
                        logger.info(f"   Companies: {', '.join(sorted(companies))}")
            except:
                logger.info("   (Could not read Q&A count)")
            
            found_files.append((name, path, file_size))
            logger.info("")
        else:
            logger.info(f"❌ Not found at {name}: {path}")
    
    logger.info("="*60)
    
    if found_files:
        logger.info(f"📊 Summary: Found {len(found_files)} Q&A file(s)")
        logger.info("="*60)
        return found_files
    else:
        logger.info("❌ No Q&A JSON files found anywhere!")
        logger.info("💡 Run initialization to generate")
        logger.info("="*60)
        return []


# ==========================================
# USAGE EXAMPLES
# ==========================================

"""
USAGE IN app.py:

# Replace this line (line 43):
    self.financial_rag = AutomotiveFinancialRAG()

# With this:
    from financial_rag_init import initialize_financial_rag
    self.financial_rag = initialize_financial_rag()

That's it! The wrapper handles everything:
- Fast path: <1 second if JSON exists
- Slow path: 2-3 minutes first time
- Auto-saves to repository root
- Shows clear instructions for persistence
"""
