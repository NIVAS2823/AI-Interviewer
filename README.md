# AI Interviewer / HR Assistant Platform

An intelligent, automated interview system powered by VideoSDK agents and advanced AI.

## 🚀 Features

- **AI-Powered Video Interviews**: Real-time interviews with AI agents (avatar + voice)
- **Intelligent Question Generation**: Based on resumes and job descriptions
- **Automated Scoring & Feedback**: Comprehensive evaluation with detailed insights
- **Candidate Pipeline Management**: For HR teams to manage screening workflows
- **Resume Parsing**: AI-powered extraction of structured data from PDFs

## 🛠 Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: React 18 + Vite
- **Databases**: MongoDB (primary), Redis (cache)
- **Video/AI**: VideoSDK Agents, Claude AI, Deepgram (STT), ElevenLabs (TTS)
- **Infrastructure**: Docker, Docker Compose

## 📋 Prerequisites

- Docker & Docker Compose (v2.0+)
- Node.js 18+ (for local frontend development)
- Python 3.10+ (for local backend development)

## 🏃 Quick Start

### 1. Clone the repository
```bash
git clone <repo-url>
cd ai-interviewer-platform
```

### 2. Set up environment variables
```bash
# Copy example env files
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Edit .env files with your credentials
```

### 3. Start all services with Docker Compose
```bash
make up
# OR
docker-compose up -d
```

### 4. Verify services are running
```bash
make status
# OR
docker-compose ps
```

### 5. Access the application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MongoDB**: localhost:27017
- **Redis**: localhost:6379

## 📦 Available Commands
```bash
make up          # Start all services
make down        # Stop all services
make restart     # Restart all services
make logs        # View logs from all services
make logs-backend # View backend logs only
make logs-frontend # View frontend logs only
make status      # Check service status
make clean       # Remove all containers and volumes
make test        # Run all tests
make shell-backend # Enter backend container shell
make shell-db    # Enter MongoDB shell
```

## 🧪 Running Tests
```bash
# Backend tests
make test-backend

# Frontend tests
make test-frontend

# All tests
make test
```

## 📚 Project Structure
```
ai-interviewer-platform/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── core/     # Core config & DB
│   │   ├── models/   # Database models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # Business logic
│   │   └── utils/    # Utilities
│   └── tests/        # Backend tests
├── frontend/         # React + Vite application
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       └── hooks/
└── docker-compose.yml
```

## 🔧 Development Workflow

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

## 🌐 API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔐 Environment Variables

See `.env.example` files for required configuration:
- MongoDB connection string
- Redis URL
- VideoSDK API keys
- AI service credentials (Claude, Deepgram, ElevenLabs)
- JWT secret key

## 📖 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Database Schema](docs/database.md)
- [Deployment Guide](docs/deployment.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 📞 Support

- Email: support@aiinterviewer.com
- Issues: GitHub Issues
- Docs: https://docs.aiinterviewer.com