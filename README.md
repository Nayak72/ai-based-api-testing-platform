# AI-Powered API Testing Platform

A comprehensive API testing platform that uses AI to generate test cases from OpenAPI/Postman specifications, executes them, and provides detailed analysis and reports.

## Features

- **AI-Powered Test Generation**: Automatically generates functional, edge, malformed, and security test cases from API specifications
- **Multiple AI Providers**: Supports OpenRouter and NVIDIA NIM with automatic fallback
- **Async Test Execution**: Concurrent test execution with configurable concurrency, rate limiting, and cancellation
- **OWASP API Top 10 Coverage**: Security tests covering all 10 OWASP API security risks
- **Detailed Reporting**: HTML and PDF reports with risk analysis and recommendations
- **Modern Frontend**: React + TypeScript + Tailwind CSS with dark mode support
- **JWT Authentication**: Secure authentication with refresh token rotation

## Tech Stack

### Backend
- FastAPI (async)
- MongoDB + Motor (async driver)
- Pydantic v2 for validation
- JWT authentication with bcrypt
- httpx for HTTP requests
- prance for OpenAPI parsing
- Jinja2 + WeasyPrint for reports
- OpenRouter / NVIDIA NIM for AI

### Frontend
- React 18 + TypeScript
- Vite for development/build
- Tailwind CSS v3
- React Router v6
- TanStack Query for data fetching
- Phosphor Icons

## Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 6+
- OpenRouter API key (or NVIDIA NIM API key)

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment file and configure
cp .env.example .env
# Edit .env with your API keys and settings

# Start MongoDB (if not running)
# mongod --dbpath /path/to/data

# Run the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Configuration

### Environment Variables

Key environment variables in `.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT signing key (32+ chars) | Yes |
| `MONGODB_URI` | MongoDB connection string | Yes |
| `OPENROUTER_API_KEY` | OpenRouter API key | Yes* |
| `NIM_API_KEY` | NVIDIA NIM API key | Yes* |

*At least one AI provider key is required.

### AI Provider Setup

1. **OpenRouter**: Sign up at https://openrouter.ai and get an API key
2. **NVIDIA NIM**: Get an API key from https://build.nvidia.com

## Usage

1. **Register/Login**: Create an account or sign in
2. **Upload Specification**: Upload an OpenAPI (YAML/JSON) or Postman Collection
3. **Parse**: The spec will be parsed and validated automatically
4. **Generate Tests**: Click "Generate Tests" to create test cases using AI
5. **Run Tests**: Create a test run with desired configuration
6. **View Results**: Monitor progress in real-time (2s polling)
7. **Analyze**: Trigger AI analysis for security/functional insights
8. **Reports**: Generate HTML/PDF reports with findings

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   │   ├── routes/       # Route handlers
│   │   │   ├── schemas/      # Pydantic schemas
│   │   │   └── deps.py       # Dependencies
│   │   ├── core/             # Core functionality
│   │   │   ├── security.py   # JWT, password hashing
│   │   │   ├── exceptions.py # Custom exceptions
│   │   │   └── logging.py    # Structured logging
│   │   ├── db/               # Database layer
│   │   │   ├── models.py     # Pydantic models
│   │   │   ├── mongo.py      # MongoDB connection
│   │   │   └── repositories/ # Data access
│   │   ├── parsers/          # Spec parsers
│   │   ├── generators/       # Test generators
│   │   ├── executor/         # Test execution
│   │   ├── analyzer/         # Result analysis
│   │   ├── reports/          # Report generation
│   │   └── ai/               # AI providers
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/            # Page components
│   │   ├── components/       # Reusable components
│   │   ├── hooks/            # Custom hooks
│   │   ├── api/              # API client
│   │   └── auth/             # Auth components
│   └── package.json
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Get current user

### Specifications
- `POST /api/v1/specs` - Upload spec
- `GET /api/v1/specs` - List specs
- `GET /api/v1/specs/{id}` - Get spec details
- `POST /api/v1/specs/{id}/parse` - Parse/re-parse spec
- `GET /api/v1/specs/{id}/endpoints` - List endpoints
- `DELETE /api/v1/specs/{id}` - Delete spec

### Test Cases
- `POST /api/v1/specs/{id}/test-cases/generate` - Generate tests
- `GET /api/v1/specs/{id}/test-cases` - List test cases
- `GET /api/v1/specs/{id}/test-cases/{tc_id}` - Get test case
- `PATCH /api/v1/specs/{id}/test-cases/{tc_id}` - Update test case
- `DELETE /api/v1/specs/{id}/test-cases/{tc_id}` - Delete test case

### Test Runs
- `POST /api/v1/runs` - Create run
- `GET /api/v1/runs` - List runs
- `GET /api/v1/runs/{id}` - Get run details
- `GET /api/v1/runs/{id}/results` - Get run results
- `POST /api/v1/runs/{id}/cancel` - Cancel run
- `POST /api/v1/runs/{id}/retry-failed` - Retry failed tests
- `POST /api/v1/runs/{id}/analyze` - Trigger AI analysis

### Reports
- `POST /api/v1/reports` - Generate report
- `GET /api/v1/reports` - List reports
- `GET /api/v1/reports/{id}` - Get report
- `GET /api/v1/reports/{id}/download` - Download report
- `GET /api/v1/reports/runs/{run_id}` - Get latest report for run

## Development

### Backend Commands

```bash
# Run linter
ruff check .

# Format code
ruff check . --fix

# Type check
pyright

# Run tests
pytest
```

### Frontend Commands

```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint
npm run lint
```

## License

MIT License - see LICENSE file for details