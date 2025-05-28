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
- **📁 Data Storage**: Redis for fast data storage and caching

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

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **PDF Processing**: marker library for advanced PDF to Markdown conversion
- **Background Jobs**: AsyncIO with Redis for job queuing
- **Data Storage**: Redis
- **File Storage**: Local filesystem with organized directory structure
- **API Documentation**: Automatic OpenAPI/Swagger documentation

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

## 🐳 Docker Deployment

MarkUI provides a single-container Docker solution that runs both frontend and backend together with nginx as a reverse proxy.

### 🚀 Quick Deployment Script

For the easiest deployment experience, use the included deployment script:

```bash
# Make script executable (first time only)
chmod +x deploy.sh

# Deploy locally
./deploy.sh deploy

# Build, deploy, and push to Docker Hub
./deploy.sh push

# Build only
./deploy.sh build
```

### Quick Start with Docker

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd MarkUI
   ```

2. **Configure environment variables**:
   ```bash
   cp docker.env.example .env
   # Edit .env with your API keys and settings
   ```

3. **Build and run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Open `http://localhost` in your browser
   - The frontend and backend are served from the same port (80)

### Manual Docker Build

1. **Build the Docker image**:
   ```bash
   docker build -t markui .
   ```

2. **Run with Redis**:
   ```bash
   # Start Redis
   docker run -d --name redis redis:7-alpine
   
   # Run MarkUI
   docker run -d \
     --name markui \
     --link redis:redis \
     -p 80:80 \
     -e REDIS_URL=redis://redis:6379 \
     -e GEMINI_API_KEY=your_api_key \
     -e OPENAI_API_KEY=your_api_key \
     markui
   ```

### Environment Configuration

The Docker container supports all environment variables from `backend/env.example`. Key variables:

#### Required for LLM Services
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
```

#### Redis Configuration
```env
REDIS_URL=redis://redis:6379
```

#### Security (Change in Production)
```env
SECRET_KEY=your-secret-key-change-this-in-production
```

#### Optional LLM Settings
```env
OPENAI_MODEL=gpt-4
CLAUDE_MODEL_NAME=claude-3-sonnet-20240229
OLLAMA_BASE_URL=http://localhost:11434
VERTEX_PROJECT_ID=your_gcp_project_id
TORCH_DEVICE=auto
```

### Pushing to Docker Hub

1. **Tag your image**:
   ```bash
   docker tag markui your-dockerhub-username/markui:latest
   docker tag markui your-dockerhub-username/markui:v1.0.0
   ```

2. **Login to Docker Hub**:
   ```bash
   docker login
   ```

3. **Push the image**:
   ```bash
   docker push your-dockerhub-username/markui:latest
   docker push your-dockerhub-username/markui:v1.0.0
   ```

4. **Create a repository on Docker Hub**:
   - Go to [Docker Hub](https://hub.docker.com/)
   - Click "Create Repository"
   - Name it `markui`
   - Set visibility (public/private)
   - Add description and documentation

### Using Pre-built Image

Once pushed to Docker Hub, others can use your image:

```bash
# Create environment file
cp docker.env.example .env
# Edit .env with your settings

# Run with docker-compose (update image name in docker-compose.yml)
docker-compose up -d

# Or run directly
docker run -d \
  --name markui \
  -p 80:80 \
  --env-file .env \
  your-dockerhub-username/markui:latest
```

### Docker Architecture

The container includes:
- **Nginx**: Serves frontend static files and proxies API requests
- **FastAPI Backend**: Handles PDF processing and AI integration
- **Frontend Build**: Svelte application built for production
- **Supervisor**: Manages both nginx and backend processes

### Persistent Storage

The Docker setup uses volumes for:
- `markui_uploads`: PDF file uploads
- `markui_outputs`: Conversion results
- `markui_static`: Static assets
- `redis_data`: Redis persistence

### Health Checks and Logs

Check container status:
```bash
# View logs
docker-compose logs -f markui
docker-compose logs -f redis

# Check health
curl http://localhost/api/v1/health
```

### Production Considerations

1. **Environment Variables**: Always set proper API keys and secret keys
2. **Redis Persistence**: The setup includes Redis persistence with AOF
3. **File Storage**: Use volume mounts for persistent file storage
4. **Security**: Update SECRET_KEY and other security settings
5. **Resources**: Ensure adequate CPU/RAM for PDF processing
6. **Backup**: Regularly backup volumes and Redis data

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