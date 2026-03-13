# Smart Hostel Management System

**Government Residence Women Polytechnic, Tasgaon**

A Flask web application for managing hostel operations — student admissions, gatepass requests, staff approvals, security verification, and notice boards.

---

## Prerequisites

- **Python 3.10+**
- **PostgreSQL** (running locally or remote)

---

## Setup

### 1. Clone & enter the project

```bash
cd capstone_project
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate       # Linux / macOS
# venv\Scripts\activate        # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/hostel_db
SECRET_KEY=your-secret-key-here
```

> Make sure the PostgreSQL database (`hostel_db`) exists before running the app.  
> Create it with: `createdb hostel_db`

### 5. Run the server

#### Option A — Flask development server

```bash
python app.py
```

Server runs at: **http://localhost:5000**

#### Option B — Uvicorn (production-ready ASGI server)

```bash
uvicorn app:asgi_app --host 0.0.0.0 --port 5000
```

With auto-reload for development:

```bash
uvicorn app:asgi_app --host 0.0.0.0 --port 5000 --reload
```

With multiple workers for production:

```bash
uvicorn app:asgi_app --host 0.0.0.0 --port 5000 --workers 4
```

---

## Usage

1. Open **http://localhost:5000** in your browser
2. **Students** → Click "Student Module" to login
3. **Admin** → Enter password `GRWPT@416312` to access Admin Panel
4. From Admin Panel:
   - **Admission** → Add new students
   - **Staff** → Register/Login as Warden or HOD
   - **Security** → Register/Login as security guard

### Workflow

```
Student submits gatepass → Warden approves/rejects → Student gets QR code
→ Security scans QR (auto-fills form) → Marks OUT/IN → Late fine calculated
```

---

## Project Structure

```
capstone_project/
├── app.py                  # Flask app factory + ASGI wrapper
├── models.py               # SQLAlchemy database models
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore
├── routes/
│   ├── home.py             # Home + Admin routes
│   ├── student.py          # Student module
│   ├── staff.py            # Staff module (Warden/HOD)
│   ├── security.py         # Security module
│   └── admission.py        # Admission module
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── home.html
│   ├── admin_panel.html
│   ├── student/
│   ├── staff/
│   ├── security/
│   └── admission/
└── static/
    ├── css/style.css
    └── qr_codes/           # Auto-generated QR images
```
