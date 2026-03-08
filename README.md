# Student-Aid-Management-System
------------------------------------------------------------------------------

# Project Setup 
---

# Prerequisites

Before starting, make sure you have the following installed:

- Python 3.10 or higher
- Git
- Node.js (LTS recommended)
- pip

Check installations:

```bash
python --version
git --version
node --version
```

---

# Clone the Repository

```bash
git clone https://github.com/Abdelrahman74S/Student-Aid-Management-System.git
```

---

# Create Virtual Environment

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### Windows

```bash
.venv\Scripts\activate
```

---

# Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

---

# Database Setup

Apply migrations:

```bash
python manage.py migrate
```

Create admin user (optional):

```bash
python manage.py createsuperuser
```

---

# Tailwind CSS Setup

This project uses **django-tailwind** with the app named **theme**.

Install Tailwind dependencies:

```bash
python manage.py tailwind install
```

Start Tailwind development server:

```bash
python manage.py tailwind start
```

---

# Run the Django Server

Open another terminal and run:

```bash
python manage.py runserver
```

Then open:

```
http://127.0.0.1:8000
```

---

# Running the Project

You need **two terminals** running.

Terminal 1:

```bash
python manage.py runserver
```

Terminal 2:

```bash
python manage.py tailwind start
```


