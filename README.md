---
title: Agentic AI Automotive Assistant
emoji: 🚗
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.49.1"
app_file: app.py
pinned: false
license: mit
tags:
  - automotive
  - ai-assistant
  - voice-enabled
  - multilingual
  - rag
  - neo4j
  - chatbot
  - computer-vision
models:
  - sentence-transformers/all-MiniLM-L6-v2
  - openai/whisper-base
python_version: "3.10"
---

# 🚗 Agentic AI Automotive Assistant

An intelligent, multilingual automotive assistant powered by AI, featuring voice interaction, semantic search, and comprehensive vehicle management.

## ✨ Features

### 🎯 Customer Portal
- **🔍 Smart Vehicle Search**: AI-powered semantic search with pagination (5 per page)
- **📊 Accuracy Metrics**: Real-time F1 Score, Precision, and Recall tracking
- **✅ No Hallucination**: Relevance filtering to ensure accurate results
- **🎤 Voice Interaction**: Speech-to-text and text-to-speech support
- **🌐 Multilingual Support**: 15+ languages including Arabic, Hindi, Chinese, and more
- **📅 Appointment Booking**: Schedule, reschedule, and cancel test drives
- **🚗 Test Drive Management**: Easy booking with vehicle ID integration

### 🔐 Admin Dashboard
- **📤 Multi-Format Upload**: CSV, JSON, XML, Excel support
- **📄 Paginated Data View**: Browse 10 records per page
- **📚 Knowledge Base Management**: Real-time stats and updates
- **💭 Sentiment Analysis**: Visualize customer sentiment distribution
- **📊 Interactive Analytics**: Plotly-powered charts and metrics
- **🔄 Delta Updates**: Add/update individual records

### 🤖 AI Chat Assistant
- **💬 Floating Chat Widget**: Always-accessible AI helper
- **🎯 Context-Aware**: Understands vehicle search, booking, and general queries
- **⚡ Real-time Responses**: Instant answers powered by RAG
- **🎨 Beautiful UI**: Modern, responsive chat interface

## 🛠️ Technology Stack

- **Framework**: Gradio 4.44.0
- **Database**: Neo4j Knowledge Graph
- **AI/ML**: 
  - Sentence Transformers (all-MiniLM-L6-v2)
  - OpenAI Whisper (Speech Recognition)
  - Transformers (Sentiment Analysis)
- **Translation**: Deep Translator (Google Translate API)
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly
- **Vector Search**: FAISS

## 📦 Installation

### Prerequisites
- Python 3.10+
- Neo4j Database (local or Aura)
- 4GB+ RAM recommended

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd automotive-assistant
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Neo4j**

Create a `.env` file or set environment variables:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

Or use Neo4j Aura (cloud):
```env
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_aura_password
NEO4J_DATABASE=neo4j
```

4. **Run the application**
```bash
python app.py
```

The app will launch at `http://localhost:7860`

## 📊 Data Formats

### Vehicle Data (CSV/JSON/XML/Excel)

**Required fields:**
- `id`: Unique identifier (e.g., V00001)
- `make`: Manufacturer (e.g., Toyota)
- `model`: Model name (e.g., Camry)
- `year`: Manufacturing year
- `price`: Price in AED

**Optional fields:**
- `features`: Comma-separated list
- `stock`: Available quantity
- `image`: Image URL
- `description`: Vehicle description

**Example CSV:**
```csv
id,make,model,year,price,features,stock,image,description
V00001,Toyota,Camry,2024,95000,"Hybrid,Safety Sense,Leather",5,https://...,Reliable sedan
```

**Example JSON:**
```json
[
  {
    "id": "V00001",
    "make": "Toyota",
    "model": "Camry",
    "year": 2024,
    "price": 95000,
    "features": "Hybrid,Safety Sense,Leather",
    "stock": 5,
    "image": "https://...",
    "description": "Reliable sedan"
  }
]
```

### Lead Data

**Required fields:**
- `name`, `phone`, `email`, `city`, `budget`

**Optional fields:**
- `interest`, `status` (hot/warm/cold), `sentiment`, `notes`

## 🎯 Usage

### Customer Portal

1. **Search Vehicles**
   - Enter text: "luxury SUV under 200k"
   - Or use voice input (microphone icon)
   - View paginated results with metrics

2. **Book Test Drive**
   - Copy vehicle ID from search results
   - Fill booking form
   - Select date and time
   - Choose pickup location

3. **Manage Appointments**
   - View your bookings
   - Reschedule or cancel
   - Check slot availability

### Admin Dashboard

**Login Credentials:**
- Username: `XXXXXXn`
- Password: `XXXXXXXXXX`

1. **Upload Data**
   - Select file (CSV/JSON/XML/Excel)
   - Choose vehicle or lead upload
   - Wait for confirmation

2. **Manual Entry**
   - Add single vehicle or lead
   - Update existing records by ID

3. **View Analytics**
   - Check sentiment distribution
   - Monitor appointment slots
   - Review knowledge base stats

## 🌐 Supported Languages

Arabic, Bengali, Chinese, English, French, German, Hindi, Italian, Japanese, Korean, Portuguese, Russian, Spanish, Turkish, Urdu

## 📈 Accuracy Metrics

The system provides real-time search quality metrics:
- **Precision**: Relevance of returned results
- **Recall**: Coverage of relevant vehicles
- **F1 Score**: Harmonic mean of precision and recall
- **Relevance Score**: Individual vehicle match quality

## 🔒 Security

- Admin authentication required
- Input validation and sanitization
- SQL injection prevention via parameterized queries
- Rate limiting on file uploads

## 🤝 Contributing

This is an academic project for MTech Final Year at BITS Pilani, Dubai.

## 📄 License

MIT License - See LICENSE file for details

## 👨‍💻 Author

**Amit Sarkar**  
MTech Student, BITS Pilani Dubai  
Year: 2025

## 🙏 Acknowledgments

- BITS Pilani, Dubai
- Neo4j for graph database technology
- Hugging Face for model hosting
- Gradio for the UI framework

## 📞 Support

For issues or questions, please open an issue on GitHub or contact the author.

---

**🎓 Academic Project** | **MTech Final Year** | **BITS Pilani Dubai 2025**
