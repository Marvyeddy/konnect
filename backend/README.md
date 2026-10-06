# Konnect Backend

A production-oriented backend API for **Konnect**, a marketplace platform built with **FastAPI** and designed to support customers, vendors, authentication, onboarding, notifications, background jobs, and cloud deployment.

The backend follows a modular architecture with asynchronous database access, background task processing, real-time notifications, object storage, automated testing, containerization, and infrastructure-as-code deployment.

---

## 🚀 Features

- User registration and authentication
- JWT-based session and refresh tokens
- HTTP-only authentication cookies
- Google authentication support
- Role-based access control
- Customer and vendor profiles
- Vendor onboarding and verification workflow
- Business-license document uploads
- Cloudinary image/document storage
- PostgreSQL database
- SQLModel / SQLAlchemy ORM
- Alembic database migrations
- Redis integration
- Redis Pub/Sub
- Server-Sent Events (SSE) for real-time notifications
- Celery background task processing
- RabbitMQ message broker
- Welcome emails
- Background email processing
- Vendor verification notifications
- Notification persistence
- Rate limiting
- Automated testing with pytest
- Dockerized production deployment
- AWS EC2 deployment
- Terraform infrastructure provisioning
- CI/CD with GitHub Actions
- Ruff linting and formatting

---



# 🏗️ Architecture

Konnect separates synchronous API operations from background processing and real-time communication.

```text
                         ┌──────────────────┐
                         │     Frontend     │
                         └────────┬─────────┘
                                  │
                                  │ HTTP / SSE
                                  ▼
                         ┌──────────────────┐
                         │     FastAPI      │
                         │      Backend     │
                         └───────┬──────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             │                   │                   │
             ▼                   ▼                   ▼
       ┌───────────┐       ┌───────────┐       ┌───────────┐
       │ PostgreSQL│       │   Redis   │       │ Cloudinary│
       │           │       │           │       │           │
       │ Users     │       │ Cache     │       │ Images    │
       │ Vendors   │       │ Pub/Sub   │       │ Documents │
       │ Orders    │       │           │       │           │
       │ Notifications│    │           │       │           │
       └───────────┘       └─────┬─────┘       └───────────┘
                                 │
                                 ▼
                       ┌──────────────────┐
                       │ Redis Notification│
                       │     Listener      │
                       └────────┬─────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  SSE Connection  │
                       │     Manager      │
                       └────────┬─────────┘
                                │
                                ▼
                              Browser


Background Processing
────────────────────────────────────────────────────────────

FastAPI
   │
   │ .delay()
   ▼
RabbitMQ
   │
   ▼
Celery Worker
   │
   ├── Emails
   ├── Notifications
   └── Other background jobs
```

---



# 🧰 Tech Stack


| Technology                | Purpose                         |
| ------------------------- | ------------------------------- |
| **Python 3.13**           | Backend language                |
| **FastAPI**               | REST API framework              |
| **PostgreSQL**            | Primary relational database     |
| **SQLAlchemy / SQLModel** | Database ORM                    |
| **Alembic**               | Database migrations             |
| **Redis**                 | Caching and Pub/Sub             |
| **RabbitMQ**              | Celery message broker           |
| **Celery**                | Background task processing      |
| **Server-Sent Events**    | Real-time browser notifications |
| **Cloudinary**            | Image and document storage      |
| **JWT**                   | Authentication tokens           |
| **Google OAuth**          | Social authentication           |
| **pytest**                | Automated testing               |
| **Ruff**                  | Linting and formatting          |
| **Docker**                | Production containerization     |
| **Terraform**             | Infrastructure as Code          |
| **AWS EC2**               | Production hosting              |
| **GitHub Actions**        | CI/CD                           |
| **uv**                    | Python dependency management    |


---



# 📁 Project Structure

The backend follows a modular structure similar to:

```text
backend/
│
├── main.py
│
├── celery_app.py
│
├── config/
│
├── database/
│
├── models/
│
├── schemas/
│
├── routers/
│
├── services/
│
├── tasks/
│   ├── email_tasks.py
│   └── notification_tasks.py
│
├── external/
│   └── email/
│
├── migrations/
│   └── versions/
│
├── tests/
│
├── Dockerfile
├── entrypoint.sh
├── pyproject.toml
└── uv.lock
```

The exact directory structure may evolve as the application grows.

---



# 🔐 Authentication

Konnect uses token-based authentication with:

- Access/session tokens
- Refresh tokens
- HTTP-only cookies
- Role-based authorization
- Google authentication

Authentication tokens contain information such as:

```json
{
  "sub": "user-id",
  "email": "user@example.com",
  "role": "user"
}
```

The backend supports multiple user roles, including:

```text
USER
VENDOR
ADMIN
PENDING
```

Authentication-related functionality includes:

- Registration
- Login
- Logout
- Refresh tokens
- Current-user retrieval
- Password management
- Google authentication
- Role-based authorization

---



# 👤 User & Vendor Onboarding

Konnect separates user authentication information from profile/business information.

Users can create accounts and subsequently complete vendor onboarding.

The vendor onboarding workflow supports:

- Business information
- Profile image
- Business license
- Document validation
- Cloudinary uploads
- Vendor verification status
- Admin verification workflow

Vendor documents can be uploaded as:

```text
Images
PDF
```

File extension, MIME type, and file-size validation are performed before uploads are accepted.

---



# ☁️ Cloudinary

Cloudinary is used for cloud-based file storage.

Typical resources include:

```text
vendors/profiles
vendors/licenses
```

Sensitive Cloudinary credentials should never be committed to GitHub.

Configure them through environment variables.

---



# 🔔 Notifications

Konnect implements persistent and real-time notifications.

Notifications are stored in PostgreSQL so that users can retrieve them even when they were offline.

For real-time delivery, Konnect uses:

```text
Redis Pub/Sub
+
Server-Sent Events
```



## Notification Flow

For example, when a vendor submits onboarding information:

```text
Vendor
   │
   ▼
FastAPI
   │
   ▼
Celery Task
   │
   ▼
RabbitMQ
   │
   ▼
Celery Worker
   │
   ├──────────────► PostgreSQL
   │                Save notification
   │
   └──────────────► Redis
                    Publish notification
                         │
                         ▼
                 Redis Listener
                         │
                         ▼
                SSE Connection Manager
                         │
                         ▼
                    Admin Browser
```

The Redis Pub/Sub channel is:

```text
notifications
```

The channel is intentionally generic so that both customers and administrators can use the same real-time notification infrastructure.

---



# 📡 Server-Sent Events

The backend provides an SSE endpoint for real-time notifications.

Example:

```text
GET /api/v1/notifications/stream
```

The connection remains open while the client waits for new notification events.

The backend maintains user-specific queues:

```text
User ID
   ↓
asyncio.Queue
   ↓
SSE connection
```

This allows multiple active connections for the same user.

---



# ⚙️ Background Tasks

Konnect uses **Celery** for operations that should not block an API request.

Current background processing includes:

- Welcome emails
- Notification processing
- Vendor onboarding notifications
- Other asynchronous jobs

The architecture is:

```text
FastAPI
   │
   │ .delay()
   ▼
RabbitMQ
   │
   ▼
Celery Worker
```

For example:

```python
send_welcome_email_task.delay(
    email=user.email,
    context=context,
)
```

The HTTP request does not need to wait for the email provider.

---



# 📨 RabbitMQ

RabbitMQ acts as the message broker for Celery.

It separates API requests from background task execution.

```text
FastAPI → RabbitMQ → Celery Worker
```

This makes background processing independent from the API process.

---



# 🗄️ Database

Konnect uses PostgreSQL as its primary database.

The application uses asynchronous database operations through SQLAlchemy/SQLModel.

Database migrations are handled by Alembic.

Example migration command:

```bash
uv run alembic upgrade head
```

Creating a migration:

```bash
uv run alembic revision --autogenerate -m "description"
```

---



# 🧪 Testing

Automated tests are written using pytest.

The backend uses asynchronous testing for FastAPI endpoints and database operations.

Example:

```bash
uv run pytest
```

Tests cover areas such as:

- Authentication
- User creation
- API endpoints
- Database behavior
- Background task dispatch
- Authentication flows
- Notifications

External services such as email providers should be mocked during tests.

For example, an email test can verify that:

```python
send_welcome_email_task.delay(...)
```

was called without sending a real email.

---



# 🧹 Code Quality

Ruff is used for linting and formatting.

Run linting:

```bash
uv run ruff check .
```

Format the project:

```bash
uv run ruff format .
```

The project can also use Git hooks to prevent commits when linting, formatting, or tests fail.

---



# 📦 Dependency Management

Konnect uses `uv`.

Install dependencies:

```bash
uv sync
```

Add a dependency:

```bash
uv add package-name
```

Add a development dependency:

```bash
uv add --dev package-name
```

The `uv.lock` file is committed so that environments can reproduce the project's dependency versions.

---



# 🔑 Environment Variables

Create a `.env` file for local development.

Example:

```env
# Application
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://username:password@host:5432/konnect

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery / RabbitMQ
CELERY_BROKER_URL=amqp://username:password@host:5672//

# Authentication
SECRET_KEY=your-secret-key
SESSION_EXPIRY_TOKEN=...
REFRESH_EXPIRY_TOKEN=...

# Google Authentication
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Cloudinary
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

# Email
SMTP_HOST=...
SMTP_PORT=...
SMTP_USERNAME=...
SMTP_PASSWORD=...
```

**Never commit** `.env` **to GitHub.**

Add it to `.gitignore`:

```gitignore
.env
.env.*
!.env.example
```

An `.env.example` file can be committed with placeholder values.

---



# 🛠️ Local Development



## Requirements

Install:

- Python 3.13+
- uv
- PostgreSQL
- Redis
- RabbitMQ

Docker is **not required for local development**.

The application can connect to externally hosted services when local resources are unavailable.

---



## 1. Clone the repository

```bash
git clone https://github.com/<your-username>/<your-repository>.git
cd <your-repository>
```

---



## 2. Install dependencies

```bash
uv sync
```

---



## 3. Configure environment variables

Create:

```text
.env
```

and configure the required variables.

---



## 4. Run database migrations

```bash
uv run alembic upgrade head
```

---



## 5. Start FastAPI

From the repository root:

```bash
uv run --directory backend fastapi dev main.py
```

The API will be available locally at:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
/docs
```

Alternative documentation:

```text
/redoc
```

---



## 6. Start Celery

In another terminal:

```bash
uv run --directory backend celery \
  -A backend.celery_app:celery_app \
  worker \
  --loglevel=info
```

The Celery worker connects to the configured RabbitMQ broker.

---



# 🐳 Docker

Docker is used for production deployment.

The backend contains a Dockerfile designed to build the application image.

The production architecture can run:

```text
FastAPI
Celery
PostgreSQL
Redis
RabbitMQ
```

as separate services.

FastAPI and Celery can use the same application image while running different commands.

Example:

```text
FastAPI container
    ↓
uvicorn / FastAPI

Celery container
    ↓
celery worker
```

---



# ☁️ AWS Deployment

Konnect is designed to run on AWS EC2 using Docker.

Infrastructure is provisioned using Terraform.

Production architecture:

```text
                    Internet
                       │
                       ▼
                  AWS EC2
                       │
              ┌────────┴────────┐
              │                 │
         FastAPI            Celery
              │                 │
              │                 │
              ├──────┬──────────┘
              │      │
              ▼      ▼
         PostgreSQL RabbitMQ
              │
              ▼
            Redis
```

Terraform is used to provision infrastructure such as:

- EC2
- Security groups
- Networking
- Elastic IP
- SSH key pair
- IAM-related resources where required

The application is containerized and deployed to the EC2 instance.

---



# 🏗️ Terraform

Infrastructure configuration is maintained separately from application code.

Typical workflow:

```bash
terraform init
```

Review changes:

```bash
terraform plan
```

Apply infrastructure:

```bash
terraform apply
```

Destroy infrastructure when required:

```bash
terraform destroy
```

Terraform state should be handled securely and should not expose secrets.

---



# 🚀 Production Deployment

A typical production workflow is:

```text
Developer
    │
    ▼
GitHub
    │
    ▼
CI/CD
    │
    ▼
Docker Image
    │
    ▼
Container Registry
    │
    ▼
AWS EC2
    │
    ▼
Docker Compose
    │
    ├── FastAPI
    ├── Celery
    ├── PostgreSQL
    ├── Redis
    └── RabbitMQ
```

The production Compose configuration uses service names for internal communication.

For example, Celery connects to RabbitMQ using:

```text
rabbitmq
```

rather than:

```text
localhost
```

because containers communicate through the Docker network.

---



# 🔄 CI/CD

GitHub Actions can be used to automate:

```text
Push
 ↓
Lint
 ↓
Format check
 ↓
Tests
 ↓
Build Docker image
 ↓
Push image
 ↓
Deploy
```

A deployment should only proceed when the required checks pass.

---



# 🩺 Health & Reliability

The backend is designed with production reliability in mind.

Examples include:

- Database health checks
- Redis health checks
- RabbitMQ health checks
- Container restart policies
- Background task processing
- Persistent notification storage
- Real-time notification delivery
- Database migrations
- Automated testing
- Environment-based configuration

---



# 🔒 Security Considerations

The application follows several security practices:

- Passwords are never stored in plain text
- Authentication tokens use signed JWTs
- Authentication cookies can be HTTP-only
- Sensitive configuration is stored in environment variables
- Uploads are validated by extension and MIME type
- Upload sizes are restricted
- Role-based authorization is enforced
- API endpoints can be rate-limited
- Secrets are excluded from source control

Production deployments should additionally use:

- HTTPS
- Secure cookies
- Proper CORS configuration
- Restricted AWS security groups
- Secret management
- Database backups
- Monitoring and logging

---



# 📊 Request & Background Processing

A normal API request:

```text
Client
  ↓
FastAPI
  ↓
Service Layer
  ↓
PostgreSQL
  ↓
Response
```

A background operation:

```text
Client
  ↓
FastAPI
  ↓
Celery .delay()
  ↓
RabbitMQ
  ↓
Celery Worker
  ↓
External Service / Database / Redis
```

A real-time notification:

```text
Celery Worker
  ↓
Redis Pub/Sub
  ↓
FastAPI Redis Listener
  ↓
SSE Manager
  ↓
Browser
```

---



# 📚 API Documentation

When the development server is running, interactive API documentation is available at:

```text
/docs
```

ReDoc is available at:

```text
/redoc
```

FastAPI automatically generates OpenAPI documentation from the API definitions.

---



# 🎯 Project Goals

Konnect is being developed with a focus on:

- Clean backend architecture
- Asynchronous programming
- Scalable background processing
- Secure authentication
- Real-time communication
- Reliable data persistence
- Cloud deployment
- Infrastructure as Code
- Automated testing
- Maintainable production code

---



# 👨‍💻 Development Philosophy

The backend separates responsibilities between different components rather than putting everything inside FastAPI request handlers.

For example:

```text
FastAPI
→ API / HTTP

PostgreSQL
→ Persistent data

Redis
→ Fast access + real-time event distribution

RabbitMQ
→ Message transport

Celery
→ Background execution

SSE
→ Real-time browser delivery

Cloudinary
→ File storage

Terraform
→ Infrastructure

Docker
→ Application packaging
```

This separation makes the system easier to maintain and scale as new features are introduced.

---



# 📌 Roadmap

Potential future improvements include:

- [ ] Expanded notification types
- [ ] More Celery background jobs
- [ ] Celery retry policies
- [ ] Scheduled/background maintenance jobs
- [ ] Improved observability
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Centralized logging
- [ ] Redis caching strategies
- [ ] More comprehensive integration tests
- [ ] Automated production deployments

---



# 📄 License

This project is currently maintained as a private/proprietary project.

If the repository becomes open source, add the appropriate license here.

---



# 👋 Author

**Marvelous Anyatonwu**

Backend / Full-Stack Engineer

Built with:

**Python · FastAPI · PostgreSQL · Redis · RabbitMQ · Celery · Docker · Terraform · AWS**