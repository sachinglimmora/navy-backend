# ⚓ Glimmora Aegis: Navy Backend

Glimmora Aegis Navy Backend is a sovereign, high-performance API service built with FastAPI, designed for secure naval mission planning, AI-driven analytics, and real-time operations.

---

## 🚀 Tech Stack

- **Core Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Database:** [PostgreSQL](https://www.postgresql.org/) with [SQLAlchemy](https://www.sqlalchemy.org/) & [Alembic](https://alembic.sqlalchemy.org/)
- **Caching:** [Redis](https://redis.io/)
- **Vector Search:** [Qdrant](https://qdrant.tech/)
- **Object Storage:** [MinIO](https://min.io/) (S3 Compatible)
- **AI/LLM Interface:** [Ollama](https://ollama.com/) (Running natively on host)
- **Containerization:** Docker & Docker Compose

---

## 🛠️ Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.10+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/download) (Installed natively)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone git@github.com:sachinglimmora/navy-backend.git
   cd GLIMMORA-Aegis----Navy-Backend
   ```

2. **Set up Environment Variables:**
   ```bash
   cp .env.example .env
   # Update .env with your local configuration
   ```

3. **Initialize Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Start Infrastructure (Docker):**
   ```bash
   docker-compose up -d
   ```

5. **Start Ollama (Native):**
   ```bash
   ollama serve
   ollama pull phi3:mini  # Or your configured model
   ```

6. **Run Migrations:**
   ```bash
   alembic upgrade head
   ```

7. **Run the API:**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`.  
Access the interactive docs at `http://localhost:8000/docs`.

---

## 🏗️ Project Structure

```text
.
├── alembic/            # Database migrations
├── app/
│   ├── main.py         # Application entry point
│   ├── api/            # API v1 routes
│   ├── core/           # Configuration & Security
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic validation schemas
│   ├── services/       # Business logic & integrations
│   └── db/             # Session management
├── seeds/              # Initial seed data
├── docker-compose.yml  # Infrastructure orchestration
└── Dockerfile          # Container specification
```

---

## 🔒 Security

- **JWT Authentication:** Secure user management with access and refresh tokens.
- **Environment Isolation:** Air-gapped capable design for sovereign environments.
- **Secure Storage:** MinIO and PostgreSQL with strict access controls.

---

## 📄 License

This project is proprietary and confidential. © 2026 Glimmora Aegis.
