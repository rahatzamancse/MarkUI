# MarkUI Backend

FastAPI backend for MarkUI - Convert PDFs to Markdown, JSON, and HTML using the marker library with intelligent storage management.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Redis server
- Poetry (recommended) or pip

### Installation
```bash
# Clone and setup
cd backend
poetry install

# Configure environment
cp env.example .env
# Edit .env with your settings

# Start Redis
redis-server

# Run the backend
poetry run uvicorn app.main:app --reload
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/routes/          # API endpoints
│   ├── core/                # Configuration and Redis
│   ├── schemas/             # Pydantic models
│   └── services/            # Business logic
├── scripts/                 # Utility scripts
├── uploads/                 # PDF storage
├── outputs/                 # Conversion outputs
└── static/                  # Preview images
```

## 🗄️ Storage Management

### Hybrid PDF Storage System

The backend uses an intelligent hybrid approach to manage PDF storage automatically:

#### Key Features
- **Count Limit**: Maximum number of PDFs (default: 50)
- **Size Limit**: Maximum total storage size (default: 5GB)
- **Smart Cleanup**: Prioritizes deletion based on multiple factors
- **Minimum Retention**: Protects recent uploads (default: 24 hours)
- **Background Monitoring**: Automatic cleanup every 30 minutes

#### Configuration
Add to your `.env` file:
```bash
# PDF Storage Management
MAX_STORED_PDFS=50                    # Maximum number of PDFs
MAX_STORAGE_SIZE_MB=5000              # Maximum storage (5GB)
MIN_RETENTION_HOURS=24                # Minimum retention time
CLEANUP_BATCH_SIZE=10                 # Cleanup batch size
STORAGE_CHECK_INTERVAL_MINUTES=30     # Check interval
```

#### Smart Cleanup Algorithm
When limits are exceeded, PDFs are prioritized for deletion based on:
- **Age**: Older files get higher priority (5 points/day)
- **Size**: Larger files get higher priority (3 points/MB)
- **Processing Status**: Unprocessed files get higher priority (+100 points)
- **Access Frequency**: Less accessed files get higher priority (3 points/day)

#### API Endpoints
```bash
# Get storage information
GET /api/v1/pdf/storage/info

# Manual cleanup trigger
POST /api/v1/pdf/storage/cleanup
```

### Example Configurations

**Production Server:**
```bash
MAX_STORED_PDFS=100
MAX_STORAGE_SIZE_MB=10000             # 10GB
MIN_RETENTION_HOURS=48                # 2 days
CLEANUP_BATCH_SIZE=20
STORAGE_CHECK_INTERVAL_MINUTES=15
```

**Development Environment:**
```bash
MAX_STORED_PDFS=20
MAX_STORAGE_SIZE_MB=1000              # 1GB
MIN_RETENTION_HOURS=2                 # 2 hours
CLEANUP_BATCH_SIZE=5
STORAGE_CHECK_INTERVAL_MINUTES=5
```

## 🧹 Database Management

### Redis Cleanup Scripts

Two convenient scripts for managing Redis data:

#### Quick Commands
```bash
# Start fresh (complete reset)
./scripts/reset_redis.sh all

# Check current state
./scripts/reset_redis.sh stats

# Interactive mode
./scripts/reset_redis.sh

# Selective cleanup
./scripts/reset_redis.sh pdfs         # PDFs only
./scripts/reset_redis.sh jobs         # Jobs only
./scripts/reset_redis.sh expired      # Expired keys only
```

#### Development Workflow
```bash
# 1. Clean slate for testing
./scripts/reset_redis.sh all

# 2. Test your application
# Upload PDFs, create conversion jobs

# 3. Monitor storage
./scripts/reset_redis.sh stats

# 4. Test storage management
# Upload more PDFs to trigger automatic cleanup

# 5. Clean up when done
./scripts/reset_redis.sh all
```

#### Advanced Usage
```bash
# Python script with full control
poetry run python scripts/cleanup_redis.py --interactive

# Force operations (no confirmations)
poetry run python scripts/cleanup_redis.py --all --force

# Specific cleanup types
poetry run python scripts/cleanup_redis.py --pdfs --force
poetry run python scripts/cleanup_redis.py --jobs --force
```

### What Gets Cleaned

#### Complete Reset (`all`)
- ✅ All PDF documents and metadata
- ✅ All conversion jobs
- ✅ All user settings
- ✅ All ID counters
- ✅ Everything in Redis

#### Selective Cleanup
- **PDFs**: Metadata only (physical files handled by storage manager)
- **Jobs**: Conversion job data and tracking
- **Settings**: User preferences and configurations
- **Expired**: Only expired keys

## 🔧 Configuration

### Environment Variables

```bash
# Server Settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Redis
REDIS_URL=redis://localhost:6379

# File Storage
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
STATIC_DIR=static
MAX_FILE_SIZE=104857600               # 100MB

# PDF Storage Management (Hybrid Approach)
MAX_STORED_PDFS=50
MAX_STORAGE_SIZE_MB=5000
MIN_RETENTION_HOURS=24
CLEANUP_BATCH_SIZE=10
STORAGE_CHECK_INTERVAL_MINUTES=30

# LLM Services (Optional)
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
CLAUDE_API_KEY=your_key_here

# Security
SECRET_KEY=your-secret-key-change-this
```

## 📊 Monitoring

### Storage Statistics
```bash
# Current storage state
./scripts/reset_redis.sh stats
```

Shows:
- Total keys in database
- PDF documents count
- Conversion jobs count
- Memory usage
- Storage usage percentages

### API Monitoring
```bash
# Storage information
curl http://localhost:8000/api/v1/pdf/storage/info

# Manual cleanup
curl -X POST http://localhost:8000/api/v1/pdf/storage/cleanup
```

### Logs
The system logs all storage management activities:
- Storage limit checks
- Cleanup operations
- File deletions
- Background task status

## 🛠️ Development

### Running Tests
```bash
# Install dependencies
poetry install

# Run tests (when available)
poetry run pytest

# Type checking
poetry run mypy app/

# Linting
poetry run flake8 app/
```

### Testing Storage Management
```bash
# 1. Clean database
./scripts/reset_redis.sh all

# 2. Set low limits for testing
# Edit .env: MAX_STORED_PDFS=5, MAX_STORAGE_SIZE_MB=100

# 3. Upload test PDFs via API or frontend
# 4. Monitor automatic cleanup
# 5. Check logs for cleanup activities
```

### API Development
```bash
# Start with auto-reload
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access interactive docs
open http://localhost:8000/docs
```

## 🚀 Deployment

### Production Setup
1. **Environment**: Set `DEBUG=false`
2. **Redis**: Use persistent Redis instance
3. **Storage**: Configure appropriate limits
4. **Monitoring**: Set up log monitoring
5. **Backup**: Regular backup of important data

### Docker (Optional)
```bash
# Build image
docker build -t markui-backend .

# Run with Redis
docker run -d --name redis redis:alpine
docker run -d --name markui-backend --link redis:redis markui-backend
```

## 🔒 Security

### Best Practices
- Change default `SECRET_KEY`
- Use environment variables for sensitive data
- Secure Redis access
- Regular security updates
- Monitor file uploads

### Storage Security
- Automatic cleanup prevents storage exhaustion
- File type validation
- Size limits enforced
- Access time tracking

## 🐛 Troubleshooting

### Common Issues

#### Redis Connection
```bash
# Check Redis status
redis-cli ping

# Start Redis
sudo systemctl start redis-server    # Linux
brew services start redis            # macOS
```

#### Storage Issues
```bash
# Check current usage
./scripts/reset_redis.sh stats

# Manual cleanup
./scripts/reset_redis.sh all

# Check storage API
curl http://localhost:8000/api/v1/pdf/storage/info
```

#### Permission Issues
```bash
# Make scripts executable
chmod +x scripts/reset_redis.sh
chmod +x scripts/cleanup_redis.py
```

#### Import Errors
```bash
# Ensure correct directory
cd backend

# Check Python environment
poetry install
poetry run python --version
```

### Performance Issues
- Reduce `CLEANUP_BATCH_SIZE` for slower cleanup
- Increase `STORAGE_CHECK_INTERVAL_MINUTES` for less frequent checks
- Monitor system resources during operations

## 📚 API Reference

### Core Endpoints

#### PDF Management
```bash
POST /api/v1/pdf/upload              # Upload PDF
GET  /api/v1/pdf/{pdf_id}            # Get PDF details
GET  /api/v1/pdf/{pdf_id}/preview    # Get preview images
```

#### Conversion
```bash
POST /api/v1/conversion/start        # Start conversion
GET  /api/v1/conversion/{job_id}     # Get job status
GET  /api/v1/conversion/{job_id}/download  # Download result
```

#### Storage Management
```bash
GET  /api/v1/pdf/storage/info        # Storage statistics
POST /api/v1/pdf/storage/cleanup     # Manual cleanup
```

#### Settings
```bash
GET  /api/v1/settings                # Get user settings
POST /api/v1/settings                # Update settings
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Development Guidelines
- Follow PEP 8 style guide
- Add type hints
- Write comprehensive tests
- Update documentation
- Test storage management features

## 📄 License

[Add your license information here]

## 🔗 Related Documentation

- [Scripts Documentation](scripts/README.md) - Detailed script usage
- [Frontend Repository](../frontend/) - React frontend
- [Marker Library](https://github.com/VikParuchuri/marker) - PDF conversion engine

---

**Need Help?** Check the troubleshooting section or create an issue in the repository. 