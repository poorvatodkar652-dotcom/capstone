# Software Requirements Specification (SRS)

## Smart Hostel Management System

**Government Residence Women Polytechnic, Tasgaon**

| Field | Details |
|-------|---------|
| **Document Version** | 1.0 |
| **Date** | 13 March 2026 |
| **Project Type** | Capstone Project |
| **Technology** | Python (Tkinter + Pandas) |

---

## 1. Introduction

### 1.1 Purpose
This document provides the complete Software Requirements Specification for the **Smart Hostel Management System** — a desktop application designed to automate hostel operations at Government Residence Women Polytechnic, Tasgaon. It covers functional requirements, non-functional requirements, system design, and module descriptions.

### 1.2 Scope
The system manages:
- Student admission and fee tracking
- Gatepass request and approval workflow
- Security verification with QR-based gatepass
- Staff/Warden/HOD dashboards
- Notice board communication
- Late fine calculation

### 1.3 Definitions and Abbreviations

| Term | Definition |
|------|-----------|
| **GRWPT** | Government Residence Women Polytechnic, Tasgaon |
| **SRS** | Software Requirements Specification |
| **HOD** | Head of Department |
| **QR Code** | Quick Response Code |
| **Gatepass** | Permission slip for students to leave the hostel |
| **Warden** | Hostel warden responsible for approving requests |
| **GUI** | Graphical User Interface |

### 1.4 Overview
The system consists of four primary modules — **Student**, **Staff**, **Security**, and **Admission** — all accessible from a central launcher. Data is stored in Excel files for simplicity and portability.

---

## 2. Overall Description

### 2.1 Product Perspective
This is a standalone desktop application built using Python's Tkinter library. It replaces manual paper-based hostel management processes with a digital system.

### 2.2 Product Functions (High-Level)

```
┌──────────────────────────────────────────────────┐
│            SMART HOSTEL MANAGEMENT SYSTEM         │
├──────────────┬──────────┬──────────┬──────────────┤
│   Student    │  Staff   │ Security │  Admission   │
│   Module     │  Module  │  Module  │   Module     │
├──────────────┼──────────┼──────────┼──────────────┤
│ • Login      │ • Login  │ • Login  │ • Add Student│
│ • Apply      │ • Approve│ • QR     │ • Track Fees │
│   Gatepass   │  /Reject │   Entry  │ • Branch/Year│
│ • View       │ • Gate-  │ • Gate-  │   Management │
│   Status     │   pass   │   pass   │              │
│ • Download   │   Regis- │   Regis- │              │
│   QR Code    │   ter    │   ter    │              │
│ • Notice     │ • Send   │ • Send   │              │
│   Board      │   Notice │   Notice │              │
└──────────────┴──────────┴──────────┴──────────────┘
```

### 2.3 User Classes

| User | Description | Authentication |
|------|-------------|----------------|
| **Student** | Hostel residents who apply for gatepasses and check status | Enrollment + Password + Branch + Year |
| **Warden** | Approves/rejects gatepass requests for their branch/year | Name + DOB + Role + Branch + Year |
| **HOD** | Views all staff and all branch requests (read-only) | Name + DOB + Role + Branch + Year |
| **Security** | Marks student OUT/IN, calculates fines | Name + DOB |
| **Admin** | Accesses the admin panel to launch modules | Password (`GRWPT@416312`) |

### 2.4 Operating Environment
- **OS**: Windows / Linux
- **Language**: Python 3.10+
- **Libraries**: Tkinter, Pandas, openpyxl, qrcode, Pillow
- **Storage**: Microsoft Excel (.xlsx) files

### 2.5 Constraints
- Single-machine deployment (not networked/client-server)
- Data stored in Excel files (not a relational database)
- No encryption for passwords (stored as plain text in Excel)

### 2.6 Assumptions
- Each student has a unique enrollment number
- One warden is assigned per branch-year combination
- The system is operated on a machine with Python and Tkinter installed
- Internet is not required

---

## 3. System Architecture

```
┌─────────────────────────────────────────────┐
│                  home.py                     │
│              (Main Launcher)                 │
│                                              │
│  ┌──────────┐  ┌────────────────────────┐    │
│  │ Student  │  │ Admin Panel (Password) │    │
│  │  Button  │  │  ┌───────┬────────┬──┐ │    │
│  └────┬─────┘  │  │Staff  │Security│Ad││    │
│       │        │  │Module │Module  │mi││    │
│       │        │  └───┬───┴────┬───┴┬─┘│    │
│       │        └──────┼────────┼────┼───┘    │
└───────┼───────────────┼────────┼────┼────────┘
        │               │        │    │
        ▼               ▼        ▼    ▼
   student.py      staff.py  security admission
                                .py     .py
        │               │        │    │
        └───────────────┴────────┴────┘
                        │
                   data/*.xlsx
                  (Excel Storage)
```

Each module runs as an **independent subprocess** launched from `home.py`.

---

## 4. Functional Requirements

### 4.1 Module: Student (`student.py`)

| ID | Requirement | Priority |
|----|------------|----------|
| SR-01 | System shall allow students to login with Enrollment, Password, Branch, and Year | High |
| SR-02 | System shall verify student credentials against branch Excel file | High |
| SR-03 | System shall display a student dashboard after successful login | High |
| SR-04 | System shall allow students to submit gatepass requests with Reason, Out Date, In Date, and Place | High |
| SR-05 | System shall generate a QR code for each gatepass request | High |
| SR-06 | System shall save the QR code as a PNG file in `data/qr_codes/` | Medium |
| SR-07 | System shall allow students to view the status of their gatepass requests | High |
| SR-08 | System shall allow students to download/open QR code for approved requests | Medium |
| SR-09 | System shall display fine details (late days, fine amount, fine status) | Medium |
| SR-10 | System shall allow students to view the notice board | Low |

### 4.2 Module: Staff (`staff.py`)

| ID | Requirement | Priority |
|----|------------|----------|
| ST-01 | System shall allow staff to register with Name, DOB, Role, Branch, Year | High |
| ST-02 | System shall allow staff to login with the registered credentials | High |
| ST-03 | System shall show role-specific dashboard (Warden vs HOD) | High |
| ST-04 | **Warden**: Shall view pending gatepass requests for their branch/year | High |
| ST-05 | **Warden**: Shall approve or reject individual requests | High |
| ST-06 | **Warden**: Shall view the gatepass register for their branch/year | Medium |
| ST-07 | **Warden**: Shall send notices to the notice board | Medium |
| ST-08 | **HOD**: Shall view all registered staff | Medium |
| ST-09 | **HOD**: Shall view requests from all branches | Medium |
| ST-10 | **HOD**: Shall send notices to the notice board | Medium |

### 4.3 Module: Security (`security.py`)

| ID | Requirement | Priority |
|----|------------|----------|
| SE-01 | System shall allow security guards to register with Name, DOB, Contact, Gender | High |
| SE-02 | System shall allow security guards to login | High |
| SE-03 | System shall allow marking student OUT/IN with actual date-time | High |
| SE-04 | System shall automatically calculate late days based on expected vs actual IN date | High |
| SE-05 | System shall calculate fine at ₹50 per late day | High |
| SE-06 | System shall record payment mode and verifier details | Medium |
| SE-07 | System shall display a full gatepass register with search functionality | Medium |
| SE-08 | System shall allow sending notices | Low |
| SE-09 | System shall allow viewing existing notices | Low |

### 4.4 Module: Admission (`admission.py`)

| ID | Requirement | Priority |
|----|------------|----------|
| AD-01 | System shall allow adding a student with enrollment, name, hostel, room, branch, year, password | High |
| AD-02 | System shall track fees: Total, Paid, Remaining, Status (Paid/Partial/Due) | High |
| AD-03 | System shall prevent duplicate enrollment numbers within a branch/year | High |
| AD-04 | System shall validate that fees are numeric values | Medium |
| AD-05 | System shall validate that paid fees do not exceed total fees | Medium |
| AD-06 | System shall store data in branch-specific Excel files with year-wise sheets | High |

### 4.5 Module: Home / Launcher (`home.py`)

| ID | Requirement | Priority |
|----|------------|----------|
| HM-01 | System shall display a home screen with institution banner | High |
| HM-02 | System shall provide a Student Module button accessible to all | High |
| HM-03 | System shall provide a hidden admin login (GRWPT label) | High |
| HM-04 | System shall authenticate admin with password `GRWPT@416312` | High |
| HM-05 | System shall display admin panel with Staff, Security, Admission buttons | High |
| HM-06 | System shall launch each module as an independent subprocess | High |

---

## 5. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|------------|
| NF-01 | **Usability** | GUI must be intuitive with clear labels and color-coded buttons |
| NF-02 | **Usability** | System must open modules in maximized/full-screen windows |
| NF-03 | **Portability** | System must work on both Windows and Linux |
| NF-04 | **Performance** | Module launch time shall be under 3 seconds |
| NF-05 | **Reliability** | Data files shall be auto-created if missing |
| NF-06 | **Maintainability** | Each module is an independent Python file for easy maintenance |
| NF-07 | **Data Integrity** | System shall prevent duplicate student enrollment entries |
| NF-08 | **Availability** | System shall work offline without internet connectivity |

---

## 6. Data Storage Design

### 6.1 Excel File Schema

#### `data/{BRANCH}.xlsx` (one file per branch, one sheet per year)

| Column | Type | Description |
|--------|------|-------------|
| Enrollment | Text | Unique student ID |
| StudentName | Text | Full name |
| HostelName | Text | Hostel assigned |
| RoomNumber | Text | Room number |
| Branch | Text | CO, IT, ENTC, EJ, DD, CE |
| Year | Text | FY, SY, TY |
| Password | Text | Login password |
| TotalFees | Numeric | Total hostel fees |
| PaidFees | Numeric | Amount paid |
| RemainingFees | Numeric | Total - Paid |
| FeesStatus | Text | Paid / Partial / Due |

#### `data/requests.xlsx`

| Column | Type | Description |
|--------|------|-------------|
| Enrollment | Text | Student ID |
| StudentName | Text | Full name |
| Branch | Text | Branch code |
| Year | Text | Year code |
| Reason | Text | Reason for gatepass |
| OutDate | Text | Requested out date-time |
| InDate | Text | Requested in date-time |
| Place | Text | Destination |
| Status | Text | Pending / Approved / Rejected |
| QRFile | Text | Path to QR code image |
| ActualInDate | Text | Actual return date-time |
| LateDays | Text | Number of late days |
| Fine | Text | Fine amount (₹50/day) |
| FineStatus | Text | Paid / Unpaid / No Fine |
| RejectReason | Text | Reason for rejection |
| RequestDateTime | Text | Timestamp of request |

#### `data/staff.xlsx`

| Column | Type | Description |
|--------|------|-------------|
| Name | Text | Staff name |
| DOB | Text | Date of birth (YYYY-MM-DD) |
| Role | Text | Warden / HOD |
| Branch | Text | Branch code |
| Year | Text | Year code |

#### `data/security.xlsx`

| Column | Type | Description |
|--------|------|-------------|
| Name | Text | Security guard name |
| DOB | Text | Date of birth |
| Contact | Text | Phone number |
| Gender | Text | Male / Female / Other |

#### `data/notices.xlsx`

| Column | Type | Description |
|--------|------|-------------|
| DateTime | Text | Timestamp |
| SenderRole | Text | Staff / Security |
| Message | Text | Notice content |

---

## 7. User Interface Design

### 7.1 Color Scheme

| Element | Color | Hex Code |
|---------|-------|----------|
| Header / Primary | Dark Blue | `#1e3c72` |
| Background | Light Blue-Gray | `#f2f6ff` |
| Accent / Title | Gold | `#ffd700` |
| Text | Dark Gray | `#333333` |
| Button Text | White | `#ffffff` |

### 7.2 Screen Flow

```
Home Screen
├── Student Module Button → Student Login → Student Dashboard
│                                           ├── Gatepass Request
│                                           ├── Request & Fine Status
│                                           ├── Notice Board
│                                           └── Logout
│
└── GRWPT (Hidden) → Admin Login → Admin Panel
                                    ├── Staff Module → Staff Login/Register → Staff Dashboard
                                    │                                         ├── View/Approve Requests (Warden)
                                    │                                         ├── Gatepass Register (Warden)
                                    │                                         ├── View All Staff (HOD)
                                    │                                         ├── All Branch Requests (HOD)
                                    │                                         ├── Send Notice
                                    │                                         ├── View Notices
                                    │                                         └── Logout
                                    │
                                    ├── Security Module → Security Login/Register → Security Dashboard
                                    │                                                ├── Gatepass Entry (QR Scan)
                                    │                                                ├── Gatepass Register
                                    │                                                ├── Send Notice
                                    │                                                ├── View Notices
                                    │                                                └── Logout
                                    │
                                    └── Admission Module → Student Admission + Fees Form
```

---

## 8. Gatepass Workflow

```
Student submits          Warden reviews           Security marks
gatepass request    →    and approves/rejects  →  OUT/IN entry
(QR generated)           the request              (Fine calculated)

┌──────────┐        ┌──────────┐        ┌──────────┐
│ Student  │        │  Warden  │        │ Security │
│          │        │          │        │          │
│ Apply    │───────▶│ Approve/ │───────▶│ Mark     │
│ Gatepass │        │ Reject   │        │ OUT/IN   │
│          │        │          │        │          │
│ Status:  │        │ Status:  │        │ Calculate│
│ Pending  │        │ Approved │        │ Late &   │
│          │        │ Rejected │        │ Fine     │
└──────────┘        └──────────┘        └──────────┘
```

---

## 9. Hardware & Software Requirements

### 9.1 Hardware Requirements

| Component | Minimum Requirement |
|-----------|-------------------|
| Processor | Intel i3 or equivalent |
| RAM | 2 GB |
| Storage | 100 MB free space |
| Display | 1024 × 768 resolution |

### 9.2 Software Requirements

| Software | Version |
|----------|---------|
| Operating System | Windows 10+ / Linux |
| Python | 3.10 or higher |
| Libraries | pandas, openpyxl, qrcode, Pillow |

---

## 10. Future Enhancements

| Enhancement | Description |
|-------------|-------------|
| Database Migration | Move from Excel to SQLite or MySQL for better data integrity |
| Password Encryption | Hash passwords instead of storing plain text |
| QR Code Scanning | Integrate camera-based QR code scanning for security module |
| Email Notifications | Send email alerts for approved/rejected gatepasses |
| Dashboard Analytics | Graphs showing request trends, fine collections, etc. |
| Multi-User Network | Client-server architecture for simultaneous access |
| Mobile App | Android/iOS companion app for students |

---

## 11. Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Guide | | | |
| Student 1 | | | |
| Student 2 | | | |
| HOD | | | |
