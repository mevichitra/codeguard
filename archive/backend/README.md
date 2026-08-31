# CodeGuard AI Backend

Advanced code analysis platform with AI detection capabilities, security vulnerability scanning, performance analysis, and code quality assessment.

## 🚀 Features

### Core Analysis Capabilities
- **AI-Generated Code Detection**: Machine learning-powered detection of AI-generated code patterns
- **Security Vulnerability Scanning**: OWASP Top 10 + AI-specific vulnerability detection
- **Performance Analysis**: Code complexity and efficiency analysis with bottleneck identification
- **Code Quality Assessment**: Maintainability scoring and improvement recommendations
- **Multi-Language Support**: Python, JavaScript, TypeScript, and more

### API Features
- **RESTful API**: Comprehensive endpoints for programmatic access
- **Batch Processing**: Analyze multiple files simultaneously
- **Real-time Analysis**: Fast analysis with intelligent caching
- **Rate Limiting**: Built-in protection against abuse
- **Authentication**: Secure API access with JWT tokens
- **CI/CD Integration**: Easy integration with development workflows

### Technical Features
- **AST-based Analysis**: Deep code structure understanding
- **Caching Layer**: Redis-powered performance optimization
- **Database Integration**: PostgreSQL for persistent storage
- **Background Tasks**: Celery for long-running operations
- **Monitoring**: Prometheus metrics and health checks
- **Documentation**: Auto-generated OpenAPI/Swagger docs

## 🏗️ Architecture

```
backend/
├── app/
│   ├── api/                 # API routes and endpoints
│   │   ├── __init__.py
│   │   └── routes.py        # Main API routes
│   ├── core/                # Core configuration and utilities
│   │   ├── __init__.py
│   │   ├── config.py        # Application settings
│   │   ├── database.py      # Database connection and session management
│   │   └── redis_client.py  # Redis client and caching utilities
│   ├── models/              # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── analysis.py      # Analysis result models
│   │   ├── project.py       # Project management models
│   │   └── user.py          # User and authentication models
│   ├── services/            # Business logic and analysis engines
│   │   ├── __init__.py
│   │   ├── ai_detector.py   # AI pattern detection system
│   │   ├── ast_parser.py    # Multi-language AST parser
│   │   ├── performance_analyzer.py  # Performance analysis module
│   │   ├── quality_assessor.py      # Code quality assessment
│   │   └── security_scanner.py      # Security vulnerability scanner
│   └── main.py              # FastAPI application entry point
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd codeguard/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database setup**
   ```bash
   # Create database
   createdb codeguard_ai
   
   # Run migrations
   alembic upgrade head
   ```

6. **Start Redis**
   ```bash
   redis-server
   ```

7. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## ⚙️ Configuration

Create a `.env` file in the backend directory:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/codeguard_ai

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=true
ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
ALLOWED_HOSTS=["localhost", "127.0.0.1"]

# Features
ENABLE_AI_DETECTION=true
ENABLE_SECURITY_SCANNING=true
ENABLE_PERFORMANCE_ANALYSIS=true
ENABLE_QUALITY_ASSESSMENT=true

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Caching
CACHE_TTL=3600
CACHE_MAX_SIZE=1000

# Logging
LOG_LEVEL=INFO
LOG_FILE=codeguard.log
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

#### Health Check
```http
GET /api/v1/health
```

#### Code Analysis
```http
POST /api/v1/analyze
Content-Type: application/json

{
  "code": "def hello_world(): print('Hello, World!')",
  "filename": "example.py",
  "analysis_types": ["ai_detection", "security", "performance", "quality"]
}
```

#### File Upload Analysis
```http
POST /api/v1/analyze/file
Content-Type: multipart/form-data

file: <uploaded_file>
analysis_types: ai_detection,security,performance,quality
```

#### Batch Analysis
```http
POST /api/v1/analyze/batch
Content-Type: application/json

{
  "files": [
    {"filename": "file1.py", "code": "..."},
    {"filename": "file2.js", "code": "..."}
  ],
  "analysis_types": ["ai_detection", "security"]
}
```

#### Quick Analysis
```http
POST /api/v1/quick/ai-detection
POST /api/v1/quick/security-score
POST /api/v1/quick/performance-score
POST /api/v1/quick/quality-score
```

#### Analysis History
```http
GET /api/v1/history
GET /api/v1/history/{analysis_id}
```

#### Statistics
```http
GET /api/v1/stats
```

## 🔧 Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py
```

### Code Quality
```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
pylint app/

# Type checking
mypy app/

# Security scan
bandit -r app/
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Performance Profiling
```bash
# Profile API endpoints
python -m cProfile -o profile.stats app/main.py

# Memory profiling
mprof run app/main.py
mprof plot
```

## 🐳 Docker Deployment

### Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/codeguard_ai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=codeguard_ai
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📊 Monitoring

### Metrics
The application exposes Prometheus metrics at `/metrics`:
- Request count and duration
- Analysis processing times
- Cache hit/miss rates
- Database connection pool status
- Memory and CPU usage

### Health Checks
- **Liveness**: `/api/v1/health`
- **Readiness**: `/api/v1/health` (includes dependency checks)

### Logging
Structured logging with configurable levels:
- Request/response logging
- Analysis operation logs
- Error tracking and alerting
- Performance metrics

## 🔒 Security

### Authentication
- JWT token-based authentication
- API key support for service-to-service communication
- Rate limiting per user/IP
- CORS configuration

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- Secure headers
- Encryption at rest and in transit

### Vulnerability Scanning
- Automated dependency scanning
- Code security analysis
- Container image scanning
- Regular security audits

## 🚀 Performance

### Optimization Features
- Redis caching for analysis results
- Database query optimization
- Connection pooling
- Async/await throughout
- Background task processing

### Scaling
- Horizontal scaling support
- Load balancer compatibility
- Database read replicas
- Redis clustering
- Microservice architecture ready

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Write comprehensive tests
- Update documentation
- Use type hints
- Add docstrings to functions and classes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.codeguard.ai](https://docs.codeguard.ai)
- **Issues**: [GitHub Issues](https://github.com/codeguard-ai/codeguard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/codeguard-ai/codeguard/discussions)
- **Email**: support@codeguard.ai

## 🗺️ Roadmap

### Current Version (v1.0)
- ✅ Core analysis engines
- ✅ REST API
- ✅ Multi-language support
- ✅ Caching and performance optimization

### Upcoming Features
- 🔄 GraphQL API
- 🔄 WebSocket real-time analysis
- 🔄 Plugin system for custom analyzers
- 🔄 Advanced ML models for AI detection
- 🔄 Integration with popular IDEs
- 🔄 Advanced reporting and analytics
- 🔄 Team collaboration features
- 🔄 Enterprise SSO integration

## 📈 Analytics

### Supported Languages
- Python (full support)
- JavaScript (full support)
- TypeScript (full support)
- Java (planned)
- C++ (planned)
- Go (planned)
- Rust (planned)

### Analysis Types
1. **AI Detection**: Confidence scoring, pattern analysis
2. **Security**: OWASP Top 10, injection attacks, crypto issues
3. **Performance**: Complexity analysis, bottleneck detection
4. **Quality**: Maintainability, readability, testability

### Metrics Collected
- Cyclomatic complexity
- Halstead metrics
- Lines of code (LOC)
- Maintainability index
- Technical debt ratio
- Security vulnerability count
- Performance bottleneck count
- AI confidence scores

---

**CodeGuard AI** - Securing and optimizing code with artificial intelligence.