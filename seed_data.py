from datetime import date
from database import init_db, query_all, execute_query, get_db_type
from queue_manager import patient_queue

def seed():
    init_db()
    
    # Check if doctors already exist
    existing_docs = query_all("SELECT COUNT(*) as count FROM doctors")
    doc_count = existing_docs[0]["count"] if existing_docs else 0

    if doc_count == 0:
        print("Seeding Doctors...")
        doctors = [
            ("Dr. Sharma", "Cardiologist", "Cardiology", "+91 98765 43210", "dr.sharma@hospital.com", "Mon,Tue,Wed,Thu,Fri", "09:00 AM - 05:00 PM"),
            ("Dr. Ananya Rao", "Pediatrician", "Pediatrics", "+91 98765 43211", "dr.ananya@hospital.com", "Mon,Tue,Wed,Thu,Sat", "10:00 AM - 06:00 PM"),
            ("Dr. Rajesh Mehta", "Orthopedic Surgeon", "Orthopedics", "+91 98765 43212", "dr.rajesh@hospital.com", "Mon,Wed,Fri", "09:00 AM - 03:00 PM"),
            ("Dr. Sunita Sen", "Neurologist", "Neurology", "+91 98765 43213", "dr.sunita@hospital.com", "Tue,Thu,Sat", "11:00 AM - 05:00 PM"),
            ("Dr. Vikram Singh", "General Physician", "General Medicine", "+91 98765 43214", "dr.vikram@hospital.com", "Mon,Tue,Wed,Thu,Fri,Sat", "08:00 AM - 04:00 PM"),
            ("Dr. Kavita Nair", "Dermatologist", "Dermatology", "+91 98765 43215", "dr.kavita@hospital.com", "Mon,Tue,Thu,Fri", "10:00 AM - 04:00 PM"),
        ]
        for doc in doctors:
            execute_query(
                "INSERT INTO doctors (name, specialization, department, phone, email, available_days, available_time) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                doc
            )

    # Check if patients already exist
    existing_pts = query_all("SELECT COUNT(*) as count FROM patients")
    pt_count = existing_pts[0]["count"] if existing_pts else 0

    if pt_count == 0:
        print("Seeding Patients...")
        patients = [
            ("Rahul Sharma", 22, "Male", "+91 98111 22334", "rahul.sharma@example.com", "B+", "12 Park Street, Central City"),
            ("Priya Patel", 29, "Female", "+91 98222 33445", "priya.patel@example.com", "O+", "45 Elm Avenue, West End"),
            ("Amit Verma", 45, "Male", "+91 98333 44556", "amit.verma@example.com", "A+", "78 Green Lane, North Hills"),
            ("Sneha Gupta", 34, "Female", "+91 98444 55667", "sneha.gupta@example.com", "AB+", "89 Sunrise Boulevard, Lake District"),
            ("Rohan Das", 58, "Male", "+91 98555 66778", "rohan.das@example.com", "O-", "102 Station Road, Old Market"),
            ("Meera Iyer", 27, "Female", "+91 98666 77889", "meera.iyer@example.com", "B-", "15 Lotus Garden, Uptown"),
        ]
        for pt in patients:
            execute_query(
                "INSERT INTO patients (name, age, gender, phone, email, blood_group, address) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                pt
            )

    # Check appointments
    existing_apps = query_all("SELECT COUNT(*) as count FROM appointments")
    app_count = existing_apps[0]["count"] if existing_apps else 0

    today_str = date.today().strftime("%Y-%m-%d")

    if app_count == 0:
        print("Seeding Initial Appointments...")
        # Bookings illustrating the user's example:
        # Dr. Sharma:
        # 10:00 AM -> Booked
        # 10:30 AM -> Available
        # 11:00 AM -> Booked
        # 11:30 AM -> Available
        appointments = [
            (1, 1, today_str, "10:00 AM", "Routine Heart Checkup & ECG", "Waiting"),
            (2, 2, today_str, "10:30 AM", "Child Vaccination & Checkup", "Confirmed"),
            (3, 1, today_str, "11:00 AM", "Chest Discomfort Follow-up", "Waiting"),
            (4, 3, today_str, "11:30 AM", "Knee & Joint Consultation", "Confirmed"),
            (5, 5, today_str, "09:30 AM", "Fever and Seasonal Flu", "Completed"),
        ]
        for app in appointments:
            app_id = execute_query(
                "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status) VALUES (%s, %s, %s, %s, %s, %s)",
                app
            )

    # Seed the live Waiting Queue with patients whose status is 'Waiting'
    waiting_records = query_all("""
        SELECT a.appointment_id, a.reason, p.patient_id, p.name as patient_name, p.age, p.phone, p.blood_group,
               d.doctor_id, d.name as doctor_name, d.department
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.status = 'Waiting' AND a.appointment_date = %s
        ORDER BY a.appointment_time ASC
    """, (today_str,))

    for rec in waiting_records:
        pt_dict = {
            "patient_id": rec["patient_id"],
            "name": rec["patient_name"],
            "age": rec["age"],
            "blood_group": rec["blood_group"],
            "phone": rec["phone"]
        }
        doc_dict = {
            "doctor_id": rec["doctor_id"],
            "name": rec["doctor_name"],
            "department": rec["department"]
        }
        patient_queue.enqueue(pt_dict, doc_dict, rec["appointment_id"], rec["reason"])

    print(f"Seed completed successfully in {get_db_type()}! Waiting queue size: {patient_queue.size()}")

if __name__ == "__main__":
    seed()
