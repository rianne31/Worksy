# Worksy

An AI-powered job portal that connects job seekers with employers using advanced matching algorithms and OpenAI integration.

## Features

### For Job Seekers
- Browse and apply to jobs
- Get AI-powered job recommendations
- Track your applications and interviews
- AI resume assistant powered by OpenAI
- Skills analysis and development suggestions
- Messaging system to connect with recruiters

### For Recruiters
- Post and manage job listings
- Review applications
- Schedule interviews
- Find qualified candidates
- Message applicants

## Technology Stack

- **Backend**: Django 4.2
- **Frontend**: Bootstrap 5, HTML, CSS, JavaScript
- **Database**: PostgreSQL
- **AI/ML**: scikit-learn, NLTK, OpenAI
- **Authentication**: django-allauth with social authentication
- **Deployment**: Docker, Gunicorn

## Installation

### Prerequisites
- Docker and Docker Compose
- Git
- Python 3.10+
- pip
- virtualenv (recommended)
- PostgreSQL (for production)

### Quick Start with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd jobportal
```

2. Create environment files:
```bash
cp .env.example .env
```

3. Update the .env file with your settings:
```env
# Database settings
DB_NAME=jobportal
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Email settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
DEFAULT_FROM_EMAIL='Worksy <noreply@worksy.com>'

# OpenAI settings
OPENAI_API_KEY=your_openai_api_key
```

4. Build and start the containers:
```bash
docker-compose up --build
```

5. Access the application:
- Main site: http://localhost:8000
- Admin interface: http://localhost:8000/admin

### Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate   # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create a superuser:
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

## Key Components

### AI Matching System
- Uses NLTK for text processing
- Implements skill-based matching algorithm
- Integrates with OpenAI for enhanced features

### Authentication
- Email verification required
- Social authentication support
- Role-based access control

### Job Management
- Advanced job search and filtering
- Application tracking system
- Interview scheduling
- Status updates and notifications

## Environment Variables

Key environment variables required:

```env
DB_NAME=jobportal
DB_USER=your_username
DB_PASSWORD=your_password
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_app_password
OPENAI_API_KEY=your_openai_key
```

## Docker Configuration

The application uses Docker Compose with two services:
1. `web`: Django application with Gunicorn
2. `db`: PostgreSQL database

### Volumes
- `postgres_data`: Persistent database storage
- `static_volume`: Static files storage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Acknowledgments

- Django framework and community
- OpenAI for AI integration
- Bootstrap for UI components
- All contributors and users

## Docker Bash

```bash
docker-compose exec web bash
```

## Docker Down

```bash
docker-compose down
```

## Docker Down -v

```bash
docker-compose down -v
```

## Docker Compose Up

```bash
docker-compose up
```

## Docker Compose Up -d

```bash
docker-compose up -d
```

## Docker Compose Up -d --build

```bash
docker-compose up -d --build
```

## Update Site Domain

```bash
docker-compose exec web python manage.py update_site_domain
```

## Collect Static

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

## Migrate

```bash
docker-compose exec web python manage.py migrate
```

## Create Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```# Worksy
