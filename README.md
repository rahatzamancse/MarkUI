# MarkUI - PDF to Markdown Converter

A modern, full-stack application for converting PDF documents to Markdown, JSON, and HTML with AI enhancement using the marker library.

## 🚀 Features

- **📄 PDF Upload & Management**: Drag & drop PDF upload with file management
- **🖼️ Visual PDF Preview**: Page-by-page preview with selective conversion
- **🤖 AI Enhancement**: Multiple LLM integrations (OpenAI, Claude, Gemini, Ollama)
- **⚙️ Advanced Options**: All marker library conversion options
- **🎨 Modern UI**: Beautiful, responsive interface with dark/light themes
- **⚡ Real-time Processing**: Live conversion progress and status updates
- **📱 Mobile Friendly**: Responsive design for all devices
- **🔧 Configurable**: Comprehensive settings for API keys and preferences

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with async support
- **Database**: SQLAlchemy with SQLite/PostgreSQL
- **Processing**: Marker library integration with background jobs
- **LLM Support**: Multiple AI service integrations
- **API**: RESTful API with comprehensive endpoints

### Frontend (Svelte 5)
- **Framework**: SvelteKit with TypeScript
- **Styling**: Tailwind CSS 4 with custom components
- **State**: Svelte stores for global state management
- **UI**: Modern, accessible interface with Lucide icons

## 🛠️ Technology Stack

**Backend:**
- FastAPI
- SQLAlchemy
- Marker PDF
- Pydantic v2
- Background Tasks
- Multiple LLM APIs

**Frontend:**
- Svelte 5
- SvelteKit
- TypeScript
- Tailwind CSS 4
- Lucide Icons
- Marked (Markdown)

## 📦 Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- pnpm (recommended)

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e .
   ```

4. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your API keys and settings
   ```

5. **Run the backend**:
   ```bash
   python run.py
   ```

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   pnpm install
   ```

3. **Start development server**:
   ```bash
   pnpm dev
   ```

4. **Open your browser**:
   Navigate to `http://localhost:5173`

## 🚀 Quick Start

1. **Start the backend** (runs on `http://localhost:8000`)
2. **Start the frontend** (runs on `http://localhost:5173`)
3. **Upload a PDF** on the home page
4. **Select pages** for conversion
5. **Choose output format** (Markdown, JSON, HTML)
6. **Configure options** (OCR, LLM enhancement, etc.)
7. **Run conversion** and view results

## 📖 Usage Guide

### PDF Upload
- Drag & drop PDF files or click to browse
- View uploaded PDFs with metadata
- Delete unwanted files

### Conversion Process
1. **Select PDF**: Choose from uploaded files
2. **Preview Pages**: Visual thumbnails with selection
3. **Choose Format**: Markdown, JSON, or HTML output
4. **Configure Options**:
   - Use LLM for enhanced accuracy
   - Force OCR on all text
   - Strip existing OCR
   - Format lines using OCR
   - Enhanced math conversion
   - Image extraction control
   - Output pagination
5. **Select LLM Service** (if using AI enhancement)
6. **Start Conversion**: Real-time progress tracking
7. **View Results**: Formatted output display
8. **Download**: Save converted files

### Settings Configuration
- **Theme**: Light/Dark mode toggle
- **API Keys**: Configure LLM services:
  - Google Gemini
  - OpenAI GPT
  - Anthropic Claude
  - Ollama (local)
  - Google Vertex AI
- **Default Options**: Set conversion preferences
- **Service Settings**: Model selection and endpoints

## 🔧 Configuration

### Environment Variables

Create `.env` file in the backend directory:

```env
# Database
DATABASE_URL=sqlite:///./markui.db

# LLM Services
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
CLAUDE_API_KEY=your_claude_key
OLLAMA_BASE_URL=http://localhost:11434
VERTEX_PROJECT_ID=your_gcp_project

# Server Settings
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### LLM Service Setup

#### OpenAI
1. Get API key from [OpenAI Platform](https://platform.openai.com/)
2. Add to settings or environment variables

#### Google Gemini
1. Get API key from [Google AI Studio](https://makersuite.google.com/)
2. Configure in settings

#### Anthropic Claude
1. Get API key from [Anthropic Console](https://console.anthropic.com/)
2. Add to configuration

#### Ollama (Local)
1. Install [Ollama](https://ollama.ai/)
2. Pull models: `ollama pull llama3.2`
3. Configure base URL in settings

## 📁 Project Structure

```
MarkUI/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Configuration & database
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── pyproject.toml      # Python dependencies
│   └── README.md
├── frontend/               # Svelte 5 frontend
│   ├── src/
│   │   ├── lib/           # Utilities & stores
│   │   ├── routes/        # SvelteKit pages
│   │   └── app.css        # Global styles
│   ├── package.json       # Node dependencies
│   └── README.md
└── README.md              # This file
```

## 🔌 API Endpoints

### PDF Management
- `POST /api/v1/pdfs/upload` - Upload PDF file
- `GET /api/v1/pdfs/` - List uploaded PDFs
- `GET /api/v1/pdfs/{id}` - Get PDF details
- `GET /api/v1/pdfs/{id}/preview` - Get page previews
- `DELETE /api/v1/pdfs/{id}` - Delete PDF

### Conversion Jobs
- `POST /api/v1/conversions/` - Create conversion job
- `GET /api/v1/conversions/` - List conversion jobs
- `GET /api/v1/conversions/{id}` - Get job status
- `GET /api/v1/conversions/{id}/result` - Get conversion result
- `GET /api/v1/conversions/{id}/download` - Download result

### Settings
- `GET /api/v1/settings/` - Get user settings
- `PUT /api/v1/settings/` - Update settings
- `GET /api/v1/settings/llm-services` - Get LLM service info

## 🧪 Development

### Backend Development
```bash
cd backend
pip install -e ".[dev]"
python run.py
```

### Frontend Development
```bash
cd frontend
pnpm dev
```

### Code Quality
```bash
# Backend
cd backend
black .
isort .
flake8 .

# Frontend
cd frontend
pnpm lint
pnpm format
pnpm check
```

## 🚀 Production Deployment

### Backend
```bash
cd backend
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
pnpm build
pnpm preview
```

### Docker (Optional)
```bash
# Backend
docker build -t markui-backend ./backend
docker run -p 8000:8000 markui-backend

# Frontend
docker build -t markui-frontend ./frontend
docker run -p 3000:3000 markui-frontend
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run linting and tests
6. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Marker](https://github.com/VikParuchuri/marker) - PDF conversion engine
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Svelte](https://svelte.dev/) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/) - Styling framework

## 📞 Support

For issues and questions:
1. Check the [documentation](./docs/)
2. Search [existing issues](../../issues)
3. Create a [new issue](../../issues/new)

---

**MarkUI** - Transform your PDFs with AI-powered conversion 🚀