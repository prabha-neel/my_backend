===== README START =====

# 📘 School ERP + Classroom + EdTech Platform (Backend)

A scalable **Django + DRF based backend** designed for:

* School ERP systems
* Classroom & admission management
* Parent–student linking
* Teacher management (school + independent tutors)
* Future-ready edtech marketplace features

This backend is **frontend-friendly**, **modular**, and **production-grade**.

---

## 🧠 High-Level Architecture

```
User (Auth)
 ├── Organization (School)
 │    ├── SchoolAdmin
 │    ├── Teacher
 │    └── Student
 │
 ├── Parent
 │    └── ParentStudentLink (Approval-based)
 │
 └── Independent Teacher (No Organization)
```

---

## 🛠 Tech Stack

* **Backend**: Django, Django REST Framework
* **Auth**: Django Custom User Model
* **Database**: PostgreSQL (recommended)
* **Media**: Django Image/File handling
* **API Style**: REST (JSON)
* **IDs**: UUID-based (API-safe)

---

## 📦 Installed Apps Overview

### 1️⃣ organizations

Handles school / institute level data.

**Key Models**

* `Organization`
* `SchoolAdmin`

**Purpose**

* Multi-school SaaS support
* Permission & role separation
* One platform → many schools

---

### 2️⃣ parents

Manages parents and their relationship with students.

**Key Models**

* `ParentProfile`
* `ParentStudentLink`

**Important Concept**

* Parent cannot directly access student
* School approval required via `ParentStudentLink`

**Frontend Flow**

1. Parent sends request
2. School/Admin approves
3. Parent gains access

---

### 3️⃣ students

Core academic & finance data.

**Key Models**

* `StudentProfile`
* `StudentSession`
* `StudentResult`
* `StudentFee`

**Responsibilities**

* Student identity
* Academic sessions
* Exam results
* Fee tracking

---

### 4️⃣ students_classroom

Most critical **admission & classroom engine**.

**Key Models**

* `Standard` (Class / Grade)
* `ClassroomSession`
* `JoinRequest`
* `SessionEnrollment`

**Key Features**

* Session-based admissions
* Join via `session_code`
* Approval workflow
* Expiry & capacity control
* Atomic transactions (race-condition safe)

**Frontend Flow**

```
Join Session → Send Request → Admin Approval → Enrollment
```

---

### 5️⃣ teachers

Supports **school teachers + independent tutors**.

**Key Model**

* `Teacher`

**Capabilities**

* Organization-linked teachers (ERP)
* Independent freelance tutors (marketplace)
* Verification & moderation
* Subject expertise (JSON-based)
* Online / Offline / Hybrid modes

---

## 🔐 Authentication & Roles

| Role        | Description           |
| ----------- | --------------------- |
| User        | Base auth entity      |
| SchoolAdmin | Manages school data   |
| Teacher     | School or independent |
| Parent      | Linked via approval   |
| Student     | Academic identity     |

⚠️ **Never expose internal IDs directly in frontend logic. Use API responses only.**

---

## 🔗 API Consumption Guide (Frontend Devs)

### 🔹 General Rules

* All APIs return **JSON**
* UUIDs are used as identifiers
* Approval-based workflows are common

### 🔹 Example: Teacher API

```
GET /api/teachers/
POST /api/teachers/
GET /api/teachers/{id}/
```

### 🔹 JSON Fields Handling

Some fields are JSON-based:

* `subject_expertise`
* `languages_spoken`
* `service_areas`

👉 Frontend must treat them as **objects / arrays**, not strings.

---

## 🧩 Adding New Backend Features (Backend Devs)

### Best Practices

* Do NOT modify existing workflows blindly
* Respect approval & verification logic
* Use transactions for admissions
* Extend via new apps or services

### Safe Extension Areas

* Reports
* Analytics
* Notifications
* Payments
* Attendance
* Timetable

---

## ⚙️ Local Setup

```bash
git clone <repo-url>
cd project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

## 📁 Media & Static Files

* Teacher profile pictures stored in:

```
media/teacher_profiles/
```

Make sure frontend handles media URLs correctly.

---

## 🚀 Future Scope

* Online classes
* Payment gateway
* Teacher marketplace
* Parent notifications
* Student analytics dashboard

---

## 📄 License

Proprietary / Internal Use (customize if open-source)

---

## 🤝 Contribution Guidelines

* Follow existing patterns
* Write clean serializers
* Keep APIs backward-compatible

---

**Designed for scale, clarity & long-term maintainability.**

===== README END =====

===== FRONTEND API DOC START =====

## 🎯 Frontend Developer API Guide

This section explains **exactly which APIs frontend must hit**, **in which order**, and **for what purpose**.

Base URL (example):
/api/

---

## 🔐 AUTHENTICATION (COMMON FOR ALL)

### Login

POST /auth/login/

Used by:

* School Admin
* Teacher
* Parent
* Student

Response:

* access token
* refresh token
* user role info

Frontend must:

* Store access token
* Send token in Authorization header for all protected APIs

---

## 🏫 SCHOOL ADMIN FLOW

### 1️⃣ Get Logged-in Admin Profile

GET /organizations/school-admins/me/

Purpose:

* Identify which school admin belongs to
* Load permissions (finance, students, staff)

Used on:

* Admin dashboard load

---

### 2️⃣ School Basic Details

GET /organizations/{organization_id}/

Purpose:

* School name
* Logo
* Address
* Session info

---

## 👨‍🏫 TEACHER APIs (VERY IMPORTANT)

### 1️⃣ List Teachers (School + Independent)

GET /teachers/

Filters frontend can apply:

* organization
* is_verified
* subject
* mode (online/offline)

Used on:

* Teacher listing page
* Search & discovery

---

### 2️⃣ Get Single Teacher Profile

GET /teachers/{teacher_id}/

Used on:

* Teacher detail page
* Admin verification screen

---

### 3️⃣ Create / Update Teacher Profile

POST /teachers/
PUT /teachers/{teacher_id}/

Used by:

* Teacher (self onboarding)
* School Admin (add teacher)

Important Fields:

* qualifications
* experience_years
* subject_expertise (JSON)
* preferred_mode

---

## 👨‍👩‍👧 PARENT APIs

### 1️⃣ Parent Profile (Logged-in)

GET /parents/me/

Purpose:

* Show parent dashboard
* Display linked children

---

### 2️⃣ Send Child Link Request

POST /parents/link-student/

Payload:

* student_id

Purpose:

* Parent requests access to child profile

Status:

* Default = PENDING

---

### 3️⃣ Parent–Student Link Status

GET /parents/student-links/

Shows:

* PENDING
* APPROVED
* REJECTED

Used on:

* Parent dashboard status screen

---

## 🎓 STUDENT APIs (Frontend Heavy)

### 1️⃣ Student Profile (Self)

GET /students/me/

Used by:

* Student dashboard

---

### 2️⃣ Student List (Admin View)

GET /students/

Used by:

* School admin
* Parent (after approval)

---

## 🏫 CLASSROOM & ADMISSION FLOW (CRITICAL)

### 1️⃣ View Available Sessions

GET /classrooms/sessions/

Used by:

* Students
* Parents

---

### 2️⃣ Join Classroom Session

POST /classrooms/join-request/

Payload:

* session_code

Result:

* JoinRequest created (PENDING)

Frontend Message:
"Request sent, waiting for approval"

---

### 3️⃣ Admin View Join Requests

GET /classrooms/join-requests/

Used by:

* School Admin dashboard

---

### 4️⃣ Approve / Reject Join Request

POST /classrooms/join-requests/{id}/approve/
POST /classrooms/join-requests/{id}/reject/

Effect:

* If approved → SessionEnrollment created
* Student officially enrolled

---

## 💰 FEES & RESULTS (READ-ONLY FOR FRONTEND)

### Student Fees

GET /students/{student_id}/fees/

Used by:

* Parent
* Student

---

### Student Results

GET /students/{student_id}/results/

Used by:

* Parent
* Student

---

## 🔎 COMMON FRONTEND RULES

### JSON Fields Handling

These fields come as JSON objects / arrays:

* subject_expertise
* languages_spoken
* service_areas

⚠️ Do NOT treat them as strings.

---

### Approval-Based UI

If status = PENDING:

* Show waiting UI
  If APPROVED:
* Enable full access
  If REJECTED:
* Show retry / contact admin message

---

## 🧠 Frontend Suggested Page → API Mapping

| Page              | APIs                      |
| ----------------- | ------------------------- |
| Login             | /auth/login/              |
| Admin Dashboard   | school-admins/me          |
| Teacher List      | /teachers/                |
| Teacher Profile   | /teachers/{id}/           |
| Parent Dashboard  | /parents/me               |
| Student Dashboard | /students/me              |
| Join Class        | /classrooms/join-request  |
| Approvals         | /classrooms/join-requests |

---

## 🚫 Frontend SHOULD NOT

* Guess permissions
* Hardcode roles
* Bypass approval logic
* Modify financial data directly

---

## ✅ Frontend SHOULD

* Respect API status flags
* Handle empty / pending states
* Handle permission errors (403)

---

===== FRONTEND API DOC END =====

