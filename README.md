# Req data & Response data
### login req : api (post) : "baseUrl/normal_user/auth/login/"
```
{
 "success": true,
 "data": {
   "tokens": {
     "access": "eyJhbGciOiJI...",
     "refresh": "eyJhbGciOiJI..."
   },
   "user": {
     "id": 2,
     "username": "prabhabenipal@gmail.com",
     "first_name": "Prabha",
     "email": "prabhabenipal@gmail.com",
     "mobile": "+919876543210",
     "role": "SCHOOL_ADMIN"
   },
   "organization": {
     "id": "c299effe-64a9-4c65-abb8-b7592f819d46",
     "admin_custom_id": "ADM-PRA-65FA",
     "name": "Prabha International School"
   },
 }
}

```



<!-- --------------------------------------------- -->

### get dashboard Data : api (post) : "baseUrl/admin/dashboard/summary/"

```
response
{
 "success": true,
 "message": "Dashboard data fetched successfully",
 "unread_count": 12,
 "active_sessions": 5,
 "admin_name": "Prabha Benipal",
 "admin_email": "prabhabenipal@gmail.com",
 "organization_name": "Prabha International School",
 "organization_logo": "https://api.yourschool.com/media/logos/prabha_school.png",
 "available_organizations": [
   {
     "id": "c299effe-64a9-4c65-abb8-b7592f819d46",
     "name": "Prabha International School",
     "role": "SCHOOL_ADMIN",
     "location": "Ghaziabad, UP"
   },
   {
     "id": "d155fggt-75b0-5d76-bcc9-c8603g920e57",
     "name": "Vikas High School",
     "role": "TEACHER",
     "location": "Delhi, NCR"
   },
   {
     "id": "e366ghhu-86c1-6e87-cdd0-d9714h031f68",
     "name": "Little Buds Academy",
     "role": "SCHOOL_ADMIN",
     "location": "Noida, Sec-62"
   }
 ]
}


```








<!-- ------------------------------------------------------- -->
### api invite session (post): create sesstion

```
-> req data : {request body}
data : {
         "title": "$role Access Key",
         "purpose": role.toUpperCase(),
         "limit": limit,
         "expires_at": DateTime.now().add(Duration(hours: hours)).toIso8601String(),
       },

```

```
-> expected data  from backend : {response}
data : {
       "session_code": "CLS-${(1000 + limit).toString()}NEW",
       "title": "$role Access Key",
       "purpose": role.toUpperCase(),
       "limit": limit,
       "joined_count": 0,
       "created_by": {"id": "1", "name": "You", "role": "ADMIN"},
       "created_at": DateTime.now().toIso8601String(),
       "expires_at": DateTime.now()
           .add(Duration(hours: hours))
           .toIso8601String(),
     };

```

#

### get all session req (get) : get all session
```
-> expected data  from backend : {response}
data :  [
      {
         "session_code": "CLS-737DD0",
         "title": "Staff Hiring - Phase 1",
         "purpose": role.toUpperCase(),
         "limit": 50,
         "joined_count": 12,
         "created_by": {"id": "1", "name": "Admin Vikas", "role": "ADMIN"},
         "created_at": "2026-01-20T10:00:00Z",
         "expires_at": "2026-12-31T23:59:59Z",
       },
      {
         "session_code": "STU-123ABC",
         "title": "Exam Prep Batch",
         "purpose": role.toUpperCase(),
         "limit": 30,
         "joined_count": 30,
         "created_by": {"id": "1", "name": "Admin Vikas", "role": "ADMIN"},
         "created_at": "2026-01-25T14:30:00Z",
         "expires_at": "2026-01-26T14:30:00Z", // Expired test case
       },
     ];

```
#
### get admin dashboard data req (get) : getadminDashbaordData
```
-> expected data  from backend : {response}
data :  {
       "unread_count": 9, // Top bar pe chamkega
       "active_sessions": 4,
       "organization_name": "Vikas High School",
       "organization_logo":
           "https://img.freepik.com/free-vector/school-building-illustration_1284-52311.jpg",
     };

```
#
### login success data (post) : login success hone pe data
```
-> body data request.body
body: {
         'user_name': emailOrMobile,
         'password': password,
       },

```

```
-> expected data  from backend : {response}
response : {
       "success": true,
       "message": "Login successful! (Fake)",
       "data": {
         "tokens": {
           "refresh": "fake_refresh_token_12345",
           "access": "fake_access_token_12345",
         },
         "user": {
           "id": 2,
           "username": emailOrMobile, // Jo aapne UI mein dala
           "first_name": "Vikas Admin",
           "email": "admin@vikas.com",
           "mobile": "+919876543210",
         },
       },
     };

```


## 📊 6. ADMIN DASHBOARD – SUMMARY DATA

### Endpoint

```
GET /api/v1/admin/dashboard-summary/
```

### Success Response (200)

```json
{
 "unread_count": 9,
 "active_sessions": 4,
 "organization_name": "Vikas High School",
 "organization_logo": "https://img.freepik.com/free-vector/school-building-illustration_1284-52311.jpg"
}
```

---

## 🚨 Common Error Response Format (IMPORTANT)

Backend **har error isi format me bheje** 👇

```json
{
 "message": "Session Expired. Please login again."
}
```

(kyunki tumhara `ApiClient` yahi read karta hai)

---

## ✅ FINAL CONFIRMATION

✔ Tumhara **ApiClient perfectly designed hai**
✔ Token refresh logic correct hai
✔ Models & RemoteDataSource aligned hai
✔ Backend ko dene ke liye ye document **production-ready** hai

---

### Next bol:

* Class Schedule API contract?
* Transport / Bus route API?
* Admission workflow API?
* TimeTable save/load API?

Tu bol 🔥
Ab frontend–backend integration bilkul smooth jayega 💪




#
#
#
#
#
#


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

