## 🔐 1. Authentication & User APIs
### 😊 Sabse pehle account banana aur login karna.

### A. User Signup
```URL: POST /normal_user/auth/signup/```

### Frontend Payload (Body)
JSON
```
{
  "username": "aman_123",
  "email": "aman@example.com",
  "password": "StrongPassword123",
  "first_name": "Aman",
  "last_name": "Sharma",
  "role": "STUDENT" // Options: STUDENT, TEACHER, PARENT
}
```

### 👍 Backend Response (Success):
```
{
  "message": "User created successfully",
  "user_id": 101
}
```

### B. User Login (JWT)
```URL: POST /normal_user/auth/login/```

### Frontend Payload (Body)
JSON
```
{ 
    "username": "aman_123", 
    "password": "StrongPassword123" 
}
```

### 👍 Backend Response (Success):
```
{
  "refresh": "eyJhbG...",
  "access": "eyJhbG...",
  "user_role": "STUDENT"
}
```

## 🏫 2. Classroom & Joining APIs (The Engine)

### A. Create Classroom Session (By Teacher)
```
URL: POST /api/v1/classroom/sessions/
```
### 😊 Frontend Payload:

JSON
```
{
  "title": "Physics Special Class",
  "target_standard": 2, // ID of the Standard (Class 10th etc.)
  "student_limit": 40,
  "expires_at": "2026-02-01T10:00:00Z"
}
```

### 😍 Backend Response:

JSON
```
{
  "session_code": "CLS-A1B2C3", // Ye code student ko dena hai
  "status": "ACTIVE"
}
```

## B. Send Join Request (By Student)
```
URL: POST /api/v1/classroom/join-requests/
```

### 😊  Frontend Payload:

```
{ "session_code": "CLS-A1B2C3" }
```

### 😍 Backend Response:
JSON
```
{
  "id": 50,
  "status": "PENDING",
  "message": "Request sent successfully"
}
```

## C. Accept/Reject Request (By Teacher)
```
URL: PATCH /api/v1/classroom/join-requests/{id}/
```

### 😊 Frontend Payload:
```
{ "status": "ACCEPTED" } // Or "REJECTED"
```

### 😍 Backend Response:
JSON
```
{
  "status": "ACCEPTED",
  "message": "Student successfully enrolled in Class 10th"
}
```

## 🏢 3. Organizations & Admin APIs
School level control ke liye.

### A. Get My Admin Permissions
```
URL: GET /api/v1/organizations/school-admins/me/
```
#### Frontend Payload: None (Needs JWT Header)

### Backend Response:
json
```
{
  "organization_name": "ABC Public School",
  "permissions": {
    "can_manage_staff": true,
    "can_view_finances": false
  }
}
```
## 👪 4. Parent-Student Linking
Parent apne bache ka data dekh sake uske liye.

### A. Link Child Request
```
URL: POST /api/v1/parents/
```

### Frontend Payload:
```
{
  "student_unique_id": "2026-ABC-1234",
  "relation": "FATHER"
}
```

###  Backend Response:
json
```
{
  "link_status": "PENDING",
  "message": "Linking request sent to student for approval"
}
```

## 🛠️ Global Frontend Checklist:

### Headers: Login ke baad har request mein Authorization: Bearer <access_token> bhejna compulsory hai.

```
Trailing Slash: Har URL ke end mein / lagana (e.g., /sessions/).
```
### Methods: * GET -> Data dekhne ke liye.

#### POST -> Naya data banane ke liye.

#### PATCH/PUT -> Data update karne ke liye.

#### DELETE -> Delete karne ke liye.

## 🏢 1. Organization Detail APIs (School/Branch Info)
### A. Saare Schools ki List Dekhna
### Action: List Organizations
```
URL: GET /api/v1/organizations/
```
### Payload (Frontend kya bhejega): 
```
Kuch nahi (Bas Authorization Token).
```

###  😁  Response (Backend kya dega): Saare registered schools ki ek list (Array).

## B. Kisi Ek School ka Poora Data
```
URL: GET /api/v1/organizations/{id}/
```
### Payload: Kuch nahi.

### Response: Us specific school ka naam, address, logo, aur session ki jankari.

## C. Naya School Register Karna
### Action: Create Organization
```
URL: POST /api/v1/organizations/
```
```
Payload: 
{
    "name": "School Name", 
    "address": "City Name"
}
```

### Response: Naya bna hua school object aur uski unique ID.

## D. School ki Jankari Badalna
### Action: Partial Update (PATCH)
```
URL: PATCH /api/v1/organizations/{id}/
```

Payload: 
```
{
    "address": "New Address"
} 
```

### (Sirf wo bhejo jo badalna hai).

### Response: Updated school data.

## 🛡️ 2. School Admin & Permissions APIs (Authority Layer)


### A. Login Admin ki Details (Sabse Zaroori API)
### Action: My Profile Details

```
URL: GET /api/v1/organizations/admins/me/
```

### Payload: Kuch nahi (Token se user detect hoga).

### Response: Logged-in admin ka naam, uska designation, aur uski saari permissions (jaise can_manage_staff, can_view_finances).

### Note: Frontend isi API se tay karta hai ki dashboard par kaunsa button dikhana hai.

## B. Saare Admins ki List (Admin Management)
### Action: List School Admins
```
URL: GET /api/v1/organizations/admins/
```
### Payload: Kuch nahi.

### Response: Poore platform par jitne bhi admins hain, unki list.

## C. Naya Admin Banana
Action: Add Admin

```
URL: POST /api/v1/organizations/admins/
```

Payload: 

```
{
    "user": 10, "designation": "Vice Principal"
} 
```
### (Yahan user user-account ki ID hai).

### Response: Admin profile create hone ka confirmation.

### D. Admin ki Permissions Badle (Power Control)
Action: Update Permissions

```
URL: PATCH /api/v1/organizations/admins/{id}/
```

Payload: 
```
{
    "can_manage_students": true, "can_view_finances": false
}
```
### Response: Updated permissions ka status.