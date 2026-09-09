# CarePulse - Hospital Management System (HMS)

A complete, full-stack Hospital Management System website developed with **Python, Flask, MySQL, SQL, HTML5, CSS3, and JavaScript**, incorporating fundamental **Data Structures (FIFO Queue, Dictionaries, Lists)**.

---

## 💻 Tech Stack & Architecture

- **Backend**: Python 3 + Flask
- **Database**: MySQL (via PyMySQL) with direct SQL queries and relational integrity (`patients`, `doctors`, `appointments`). Seamless fallback to SQLite (`hospital.db`) so the application can run immediately even without a local MySQL server running.
- **Frontend**: Responsive HTML5, Vanilla CSS with modern clinical aesthetic (glassmorphism, subtle micro-animations, Outfit & Plus Jakarta Sans typography), and JavaScript (live dynamic slot booking, search filtering, modals).
- **Data Structures (DSA)**:
  - **Queue (FIFO)**: `WaitingQueue` class built with Python's `collections.deque` for O(1) time complexity to manage patients waiting for their turn (*Patient A &rarr; Patient B &rarr; Patient C &rarr; Patient D*).
  - **Dictionaries**: Structured handling of patient and doctor records (e.g. `{"id": 101, "name": "Rahul", "age": 22, "blood_group": "B+"}`).
  - **Lists**: Dynamic slot generation, search filtering, and department categorization.

---

## 🚀 Key Features

### 🏠 1. Home Dashboard
- **Key Stats**: Total Patients, Total Doctors, Today's Appointments, Available Doctors.
- **Live Waiting Queue**: Real-time display of patients in FIFO waiting sequence with queue numbers and a **"Call Next Patient"** action button.
- **Quick-Action Buttons**:
  - ➕ Add Patient
  - 👨‍⚕️ Add Doctor
  - 📅 Book Appointment
  - 🔍 Search Patient
- **Today's Appointments Roster**: Real-time appointment schedule with status tags (`Confirmed`, `Waiting`, `Completed`, `Cancelled`).
- **Doctor Availability Board**: Department-wise specialist status.
- **Recent Registrations**: Latest patient admissions.

### 👤 2. Patient Management
- Register new patients with full details (Name, Age, Gender, Phone, Email, Blood Group, Residential Address).
- Search patients instantly by **Patient ID, Name, or Phone Number**.
- Edit and update patient information.
- Delete patient records with cascade constraints.

### 👨‍⚕️ 3. Doctor Management
- Add doctors with details (Name, Specialization, Department, Phone, Email, Available Days, Hours).
- Filter doctors by **Department** (Cardiology, Pediatrics, Orthopedics, Neurology, General Medicine, Dermatology).
- Search doctors by name or specialization.
- Edit doctor profiles and view availability.

### 📅 4. Appointment Management & Double-Booking Protection ⭐
- **Step-by-Step Booking Flow**:
  1. Select Patient
  2. Select Doctor & Date
  3. **Live Time Slot Selector**:
     - 10:00 AM &rarr; Booked ❌ *(Locked to prevent duplicate booking)*
     - 10:30 AM &rarr; Available ✅ *(Clickable)*
     - 11:00 AM &rarr; Booked ❌
     - 11:30 AM &rarr; Available ✅
  4. Reason for Visit & Initial Status (`Confirmed` or `Waiting`).
- **Strict Verification**: Python and SQL verify active bookings for the selected doctor, date, and slot to guarantee no overlapping consultations can occur.
- **Reschedule & Cancel**: Reschedule appointments to a different date/slot or cancel them to immediately free up the doctor's time slot for other patients.

### 🧠 5. Patient Waiting Room (FIFO Queue)
- Dedicated waiting room board (`/queue`).
- Patients marked as **Waiting** automatically join the FIFO queue.
- Clinic reception or doctor clicks **"Call Next Patient"** (`dequeue()`), calling the next patient in line and updating their status.

---

## 🛠️ How to Run Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure MySQL
If you have MySQL running locally, create the database or set environment variables:
```bash
# Optional: Set environment variables (defaults to localhost:3306, user: root, password: "")
set MYSQL_HOST=localhost
set MYSQL_USER=root
set MYSQL_PASSWORD=your_password
set MYSQL_DB=hospital_db
```
*Note: If MySQL is not running or credentials are not configured, the system automatically runs with the included SQLite database (`hospital.db`) so you can test immediately with zero configuration!*

### 3. Initialize & Seed Initial Data
```bash
python seed_data.py
```

### 4. Start the Flask Server
```bash
python app.py
```
Open your browser and visit: **http://127.0.0.1:5000**
