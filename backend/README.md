# MarkUI Backend

FastAPI backend for the MarkUI project - A web interface for the marker PDF conversion library.

## Features

- **PDF Upload & Management**: Upload, list, and manage PDF documents
- **PDF Preview**: Generate preview images for PDF pages
- **Conversion Jobs**: Create and manage PDF conversion jobs with various options
- **Multiple Output Formats**: Support for Markdown, JSON, and HTML output
- **LLM Integration**: Optional LLM enhancement for better conversion quality
- **Settings Management**: Configure LLM services, API keys, and default settings
- **Background Processing**: Asynchronous conversion processing
- **File Management**: Automatic file cleanup and organization

## Installation

1. **Install dependencies**:
   ```bash
   cd backend
   pip install -e .
   ```

2. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Run the application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

- **Database**: SQLite by default, PostgreSQL supported
- **File Storage**: Local file system paths
- **LLM Services**: API keys for Gemini, OpenAI, Claude
- **Ollama**: Local LLM service configuration

### LLM Services

The backend supports multiple LLM services for enhanced conversion:

1. **Google Gemini** - Requires `GEMINI_API_KEY`
2. **OpenAI** - Requires `OPENAI_API_KEY`
3. **Anthropic Claude** - Requires `CLAUDE_API_KEY`
4. **Ollama** - Local models, no API key required
5. **Google Vertex AI** - Requires `VERTEX_PROJECT_ID`

## API Endpoints

### Health Check
- `GET /api/v1/health` - Health check

### PDF Management
- `POST /api/v1/pdf/upload` - Upload PDF
- `GET /api/v1/pdf/list` - List PDFs
- `GET /api/v1/pdf/{pdf_id}` - Get PDF info
- `GET /api/v1/pdf/{pdf_id}/preview` - Get PDF preview
- `DELETE /api/v1/pdf/{pdf_id}` - Delete PDF

### Conversion Jobs
- `POST /api/v1/conversion/jobs` - Create conversion job
- `GET /api/v1/conversion/jobs` - List conversion jobs
- `GET /api/v1/conversion/jobs/{job_id}` - Get job details
- `GET /api/v1/conversion/jobs/{job_id}/result` - Get conversion result
- `GET /api/v1/conversion/jobs/{job_id}/download` - Download result file
- `DELETE /api/v1/conversion/jobs/{job_id}` - Delete job

### Settings
- `GET /api/v1/settings/user` - Get user settings
- `PUT /api/v1/settings/user` - Update user settings
- `GET /api/v1/settings/llm-services` - Get available LLM services

## Marker Options

The backend supports all marker library options:

- **Output Format**: markdown, json, html
- **Page Selection**: Convert specific pages
- **Use LLM**: Enable LLM enhancement
- **Force OCR**: Force OCR on all text
- **Strip Existing OCR**: Remove existing OCR text
- **Format Lines**: Reformat lines using OCR
- **Redo Inline Math**: Enhanced math conversion
- **Disable Image Extraction**: Skip image extraction
- **Paginate Output**: Add page breaks

## Development

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API route handlers
│   ├── core/
│   │   ├── config.py        # Configuration
│   │   └── database.py      # Database setup
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── main.py              # FastAPI app
├── pyproject.toml           # Dependencies
└── README.md
```

### Running Tests

```bash
pytest
```

### Database Migrations

The application uses SQLAlchemy with automatic table creation. For production, consider using Alembic for migrations.

## Docker Support

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```


## Project Structure

```
backend/
├── app/
│   ├── api/routes/          # API endpoints
│   │   ├── health.py        # Health check
│   │   ├── pdf.py          # PDF management
│   │   ├── conversion.py   # Conversion jobs
│   │   └── settings.py     # User settings
│   ├── core/
│   │   ├── config.py       # Configuration management
│   │   └── database.py     # Database setup
│   ├── models/             # SQLAlchemy models
│   │   ├── pdf_document.py
│   │   ├── conversion_job.py
│   │   └── user_settings.py
│   ├── schemas/            # Pydantic schemas
│   │   ├── pdf.py
│   │   ├── conversion.py
│   │   └── settings.py
│   ├── services/           # Business logic
│   │   ├── file_manager.py
│   │   └── marker_service.py
│   └── main.py            # FastAPI app
├── pyproject.toml         # Dependencies
├── env.example           # Environment template
├── README.md             # Documentation
└── run.py               # Startup script
```

## License

MIT License - see LICENSE file for details. 