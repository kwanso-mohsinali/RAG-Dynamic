# RAG Dynamic - Retrieval Augmented Generation System

A dynamic RAG (Retrieval Augmented Generation) system built with FastAPI, PostgreSQL with pgvector extension, and Redis for scalable document processing and intelligent retrieval.

## 🏗️ Architecture

This project follows a microservices architecture with the following components:

- **API Service**: FastAPI backend for handling HTTP requests
- **Database**: PostgreSQL with pgvector extension for vector storage
- **Message Broker**: Redis for task queuing and caching
- **Task Processing**: Celery workers for background document processing
- **Cloud Storage**: AWS S3 integration for file storage

## 🚀 Features

- **Document Ingestion & Processing**: Download documents from S3 and ingest them asynchronously
- **Vector Storage**: Store and search document embeddings using PostgreSQL pgvector
- **File Download**: Secure file download functionality from S3
- **Scalable Processing**: Background task processing with Celery
- **Health Monitoring**: Built-in health check endpoints
- **Containerized**: Full Docker support with docker-compose

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.11+
- AWS Account (for S3 storage)
- PostgreSQL with pgvector extension

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rag-dynamic
```

### 2. Environment Configuration

Create a `.env` file in the `apps/api/` directory:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
AWS_BUCKET_NAME=your_s3_bucket_name

# Database Configuration
DATABASE_URL=postgresql://postgres:kwanso123@db:5432/rag-dd

# Celery Configuration
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### 3. Run with Docker Compose

```bash
# Build and start all services
docker compose up --build

# Run in detached mode
docker compose up -d
```

### 4. Access the Application

- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5433
- **Redis**: localhost:6379

## 📁 Project Structure

```
rag-dynamic/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── alembic/           # Database migrations
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── config.py      # Configuration settings
│   │   │   ├── main.py        # FastAPI application
│   │   │   ├── s3_utils.py    # AWS S3 utilities
│   │   │   ├── constants/     # Application constants
│   │   │   ├── controllers/   # API controllers
│   │   │   ├── db/           # Database connection
│   │   │   ├── models/       # Data models
│   │   │   └── services/     # Business logic
│   │   ├── celery_app/       # Celery configuration
│   │   └── requirements.txt  # Python dependencies
│   └── web/                  # Frontend (placeholder)
├── docker-compose.yml        # Docker services configuration
├── Dockerfile               # API service container
└── README.md               # Project documentation
```

## 🔧 API Endpoints

### Health Check
- **GET** `/` - Application health status

### File Management
- **GET** `/download/{file_key}` - Download file from S3

## 🐳 Docker Services

### API Service
- **Port**: 8000
- **Framework**: FastAPI with Uvicorn
- **Features**: Auto-reload, file download functionality

### Database Service
- **Image**: pgvector/pgvector:pg16
- **Port**: 5433 (external), 5432 (internal)
- **Features**: PostgreSQL with vector extension for embeddings

### Redis Service
- **Image**: redis:7-alpine
- **Port**: 6379
- **Purpose**: Message broker and caching

### Celery Worker (Optional)
- **Status**: Currently commented out
- **Purpose**: Background document processing
- **Queue**: document_processing

## 📦 Dependencies

### Core Dependencies
- `fastapi==0.116.1` - Modern web framework
- `uvicorn[standard]==0.35.0` - ASGI server
- `pydantic==2.11.1` - Data validation
- `python-dotenv==1.1.1` - Environment management

### Database & Storage
- `psycopg2-binary==2.9.10` - PostgreSQL adapter
- `boto3==1.40.18` - AWS SDK

### Task Processing
- `celery==5.5.3` - Distributed task queue
- `redis==6.4.0` - Redis client

## 🚀 Development

### Local Development Setup

1. **Install dependencies**:
```bash
cd apps/api
pip install -r requirements.txt
```

2. **Start services**:
```bash
# Start only database and redis
docker compose up db redis -d

# Run API locally
cd apps/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations
```bash
# Run migrations (when alembic is configured)
docker compose exec api alembic upgrade head
```

### Celery Workers
```bash
# Start celery worker (when configured)
docker compose up celery-worker
```

## 🔒 Security Considerations

- Store sensitive credentials in environment variables
- Use IAM roles for AWS access in production
- Implement proper authentication and authorization
- Validate file uploads and sanitize inputs
- Use HTTPS in production

## 📈 Scaling

- **Horizontal Scaling**: Add more Celery workers for processing
- **Database**: Use read replicas for better performance
- **Caching**: Leverage Redis for frequently accessed data
- **Load Balancing**: Use nginx or similar for API load balancing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the repository
- Contact the development team

---

**Built with ❤️ by Mohsin and Sami**
