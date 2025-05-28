# MarkUI Backend Scripts

This directory contains utility scripts for managing the MarkUI backend.

## Redis Database Cleanup Scripts

### 🧹 `reset_redis.sh` - Simple Shell Wrapper

The easiest way to clean up Redis data. This script automatically detects your Python environment and provides a simple interface.

#### Usage:

```bash
# Interactive mode (default)
./scripts/reset_redis.sh

# Complete database reset
./scripts/reset_redis.sh all

# Clean only PDF documents
./scripts/reset_redis.sh pdfs

# Clean only conversion jobs
./scripts/reset_redis.sh jobs

# Clean only user settings
./scripts/reset_redis.sh settings

# Clean only expired keys
./scripts/reset_redis.sh expired

# Show database statistics
./scripts/reset_redis.sh stats

# Show help
./scripts/reset_redis.sh help
```

### 🐍 `cleanup_redis.py` - Advanced Python Script

The full-featured cleanup script with more options and detailed control.

#### Usage:

```bash
# Interactive mode
poetry run python scripts/cleanup_redis.py --interactive

# Complete database reset
poetry run python scripts/cleanup_redis.py --all

# Clean specific data types
poetry run python scripts/cleanup_redis.py --pdfs
poetry run python scripts/cleanup_redis.py --jobs
poetry run python scripts/cleanup_redis.py --settings
poetry run python scripts/cleanup_redis.py --counters
poetry run python scripts/cleanup_redis.py --expired

# Show statistics only
poetry run python scripts/cleanup_redis.py --stats

# Force mode (skip confirmations)
poetry run python scripts/cleanup_redis.py --all --force
```

## When to Use These Scripts

### 🔄 **Development & Testing**
- **Complete reset**: When you want to start fresh during development
- **PDF cleanup**: When testing PDF upload limits and storage management
- **Job cleanup**: When testing conversion workflows

### 🧪 **Before Testing Storage Management**
```bash
# Start with a clean slate
./scripts/reset_redis.sh all

# Upload some test PDFs
# Test storage limits and cleanup behavior
```

### 🚀 **Production Maintenance**
- **Expired keys**: Regular cleanup of expired data
- **Selective cleanup**: Remove specific data types without affecting others
- **Statistics**: Monitor database usage

### 🆘 **Troubleshooting**
- **Storage issues**: Clean up when storage limits are exceeded
- **Corrupted data**: Reset specific data types
- **Performance**: Clean up expired or unnecessary data

## Safety Features

### ⚠️ **Confirmations**
- Complete reset requires typing "YES"
- Selective operations ask for confirmation
- Use `--force` to skip confirmations in scripts

### 📊 **Statistics**
- Always shows current database state
- Displays memory usage
- Shows key counts by category

### 🔍 **Detailed Information**
- Interactive mode shows detailed key information
- TTL (Time To Live) information for each key
- Key type and expiration status

## Examples

### Start Fresh for Development
```bash
# Complete reset
./scripts/reset_redis.sh all

# Or use Python script with force
poetry run python scripts/cleanup_redis.py --all --force
```

### Clean Up After Testing
```bash
# Remove test PDFs but keep settings
./scripts/reset_redis.sh pdfs

# Remove test conversion jobs
./scripts/reset_redis.sh jobs
```

### Regular Maintenance
```bash
# Clean expired keys
./scripts/reset_redis.sh expired

# Check current usage
./scripts/reset_redis.sh stats
```

### Interactive Exploration
```bash
# Start interactive mode to explore and clean selectively
./scripts/reset_redis.sh interactive
```

## Prerequisites

### Redis Server
Make sure Redis is running:
```bash
# Check if Redis is running
redis-cli ping

# Start Redis (Ubuntu/Debian)
sudo systemctl start redis-server

# Start Redis (macOS with Homebrew)
brew services start redis

# Start Redis with Docker
docker run -d -p 6379:6379 redis:alpine
```

### Python Environment
The scripts work with:
- Poetry (recommended): `poetry run python`
- Python 3: `python3`
- Python: `python`

### Dependencies
The cleanup scripts use the same dependencies as the main application:
- `redis` package for Redis connectivity
- `pydantic-settings` for configuration

## Configuration

The scripts use the same configuration as the main application:
- Redis URL from environment variables or defaults
- Configuration from `.env` file
- Same Redis database as the application

## Troubleshooting

### Redis Connection Issues
```bash
# Check Redis status
redis-cli ping

# Check Redis configuration
redis-cli info server
```

### Permission Issues
```bash
# Make scripts executable
chmod +x scripts/reset_redis.sh
chmod +x scripts/cleanup_redis.py
```

### Python Environment Issues
```bash
# Use Poetry
poetry install
poetry run python scripts/cleanup_redis.py --stats

# Or use system Python
python3 scripts/cleanup_redis.py --stats
```

### Import Errors
Make sure you're running from the backend directory:
```bash
cd backend
./scripts/reset_redis.sh stats
```

## Integration with Storage Management

These cleanup scripts work well with the hybrid storage management system:

1. **Test Storage Limits**: Clean database, upload PDFs, test automatic cleanup
2. **Reset Counters**: Clean counters to reset PDF/job ID sequences
3. **Simulate Storage Pressure**: Use selective cleanup to test different scenarios
4. **Monitor Usage**: Use stats to monitor storage management effectiveness

## Security Notes

- **Production Use**: Always backup important data before cleanup
- **Access Control**: Ensure Redis access is properly secured
- **Confirmation**: Scripts require explicit confirmation for destructive operations
- **Logging**: All operations are logged for audit purposes

## 🔗 Related Documentation

- [Main Backend README](../README.md) - Complete backend documentation including storage management
- [Environment Configuration](../env.example) - Configuration options 