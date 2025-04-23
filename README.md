# EduConnect - Mentorship Platform

EduConnect is a comprehensive mentorship platform that connects mentors and mentees for educational and professional development. The platform includes features for 1-on-1 sessions, group sessions, resource libraries, progress tracking, and more.

## Features

- **User Authentication**: Secure login and registration system
- **Mentorship Sessions**: Schedule and manage 1-on-1 and group mentorship sessions
- **Video Conferencing**: Built-in video call functionality for virtual sessions
- **Resource Library**: Create and share educational resources including PDFs and other documents
- **Progress Tracking**: Track mentee progress through milestones and goals
- **Messaging System**: Real-time chat between mentors and mentees
- **Reviews and Feedback**: Leave reviews after completed sessions

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

### Setup Instructions

1. **Clone the repository**

```bash
git clone <repository-url>
cd educonnect
```

2. **Create and activate a virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the root directory with the following variables:

```
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///app.db
FLASK_APP=run.py
FLASK_ENV=development
```

5. **Initialize the database**

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

6. **Run the application**

```bash
python run.py
```

The application will be available at `http://localhost:5000`.

## Usage

1. **Register an account** as either a mentor or mentee
2. **Browse available mentors** and their expertise
3. **Request a session** with a mentor
4. **Join sessions** via the built-in video conferencing tool
5. **Access and share resources** in the resource library
6. **Track progress** through milestones and goals
7. **Leave reviews** after completed sessions

## Development

### Project Structure

```
educonnect/
├── app/                    # Application package
│   ├── auth/               # Authentication blueprint
│   ├── main/               # Main blueprint
│   ├── mentorship/         # Mentorship blueprint
│   ├── sessions/           # Sessions blueprint
│   ├── static/             # Static files
│   ├── templates/          # HTML templates
│   ├── __init__.py         # Application factory
│   └── models.py           # Database models
├── migrations/             # Database migrations
├── .env                    # Environment variables
├── config.py               # Configuration
├── requirements.txt        # Dependencies
└── run.py                  # Application entry point
```

### Running Tests

```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
