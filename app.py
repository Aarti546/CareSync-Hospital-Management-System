from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date, timedelta
import os

from database import query_all, query_one, execute_query, get_db_type, init_db
from queue_manager import patient_queue

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "carepulse_hospital_secret_key_2026")

# Ensure DB is initialized
init_db()

# Synchronize FIFO Waiting Queue on startup
def sync_waiting_queue():
    today_str = date.today().strftime("%Y-%m-%d")
    waiting_records = query_all("""
        SELECT a.appointment_id, a.reason, p.patient_id, p.name as patient_name, p.age, p.phone, p.blood_group,
               d.doctor_id, d.name as doctor_name, d.department
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.status = 'Waiting' AND a.appointment_date = %s
        ORDER BY a.appointment_time ASC
    """, (today_str,))
    
    # If queue is empty, repopulate from active 'Waiting' appointments
    if patient_queue.is_empty():
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

sync_waiting_queue()

# Time slots generator helper
STANDARD_SLOTS = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM"
]

# ----------------------------------------------------
# 🏠 1. HOME DASHBOARD
# ----------------------------------------------------
@app.route("/")
def dashboard():
    today_str = date.today().strftime("%Y-%m-%d")

    # Metrics
    total_patients_res = query_one("SELECT COUNT(*) as count FROM patients")
    total_patients = total_patients_res["count"] if total_patients_res else 0

    total_doctors_res = query_one("SELECT COUNT(*) as count FROM doctors")
    total_doctors = total_doctors_res["count"] if total_doctors_res else 0

    today_apps_res = query_one("SELECT COUNT(*) as count FROM appointments WHERE appointment_date = %s", (today_str,))
    today_appointments = today_apps_res["count"] if today_apps_res else 0

    # Doctors list & departments
    doctors = query_all("SELECT * FROM doctors ORDER BY name ASC")
    departments = sorted(list(set(d["department"] for d in doctors)))

    # Today's appointments with joined patient and doctor details
    appointments = query_all("""
        SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.blood_group,
               d.name as doctor_name, d.department, d.specialization
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.appointment_date = %s
        ORDER BY a.appointment_time ASC
    """, (today_str,))

    # Upcoming appointments (future dates)
    upcoming_appointments = query_all("""
        SELECT a.*, p.name as patient_name, d.name as doctor_name, d.department
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE a.appointment_date > %s AND a.status != 'Cancelled'
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
        LIMIT 5
    """, (today_str,))

    # Recent patient registrations
    recent_patients = query_all("SELECT * FROM patients ORDER BY patient_id DESC LIMIT 5")

    # Live Waiting Queue
    waiting_list = patient_queue.get_all()
    queue_size = patient_queue.size()

    return render_template(
        "index.html",
        total_patients=total_patients,
        total_doctors=total_doctors,
        today_appointments=today_appointments,
        available_doctors_count=max(total_doctors - 2, 0),
        doctors=doctors,
        departments=departments,
        appointments=appointments,
        upcoming_appointments=upcoming_appointments,
        recent_patients=recent_patients,
        waiting_list=waiting_list,
        queue_size=queue_size,
        today_str=today_str,
        today_formatted=date.today().strftime("%A, %b %d, %Y"),
        db_type=get_db_type()
    )


# ----------------------------------------------------
# 👤 2. PATIENT MANAGEMENT
# ----------------------------------------------------
@app.route("/patients")
def patients_list():
    search_query = request.args.get("search", "").strip()
    
    if search_query:
        # Search by Patient ID, Name, or Phone
        if search_query.isdigit():
            patients = query_all("""
                SELECT * FROM patients 
                WHERE patient_id = %s OR phone LIKE %s OR name LIKE %s
                ORDER BY patient_id DESC
            """, (int(search_query), f"%{search_query}%", f"%{search_query}%"))
        else:
            patients = query_all("""
                SELECT * FROM patients 
                WHERE name LIKE %s OR phone LIKE %s
                ORDER BY patient_id DESC
            """, (f"%{search_query}%", f"%{search_query}%"))
    else:
        patients = query_all("SELECT * FROM patients ORDER BY patient_id DESC")

    return render_template("patients.html", patients=patients, search_query=search_query)

@app.route("/patients/add", methods=["POST"])
def add_patient():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    blood_group = request.form.get("blood_group", "").strip()
    address = request.form.get("address", "").strip()

    if not name or not age or not phone:
        flash("Name, Age, and Phone are required fields.", "error")
        return redirect(url_for("patients_list"))

    try:
        new_id = execute_query(
            "INSERT INTO patients (name, age, gender, phone, email, blood_group, address) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (name, int(age), gender, phone, email, blood_group, address)
        )
        flash(f"Patient '{name}' (ID: #{new_id}) registered successfully!", "success")
    except Exception as e:
        flash(f"Error registering patient: {str(e)}", "error")

    return redirect(url_for("patients_list"))

@app.route("/patients/edit/<int:patient_id>", methods=["POST"])
def edit_patient(patient_id):
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    blood_group = request.form.get("blood_group", "").strip()
    address = request.form.get("address", "").strip()

    try:
        execute_query("""
            UPDATE patients 
            SET name = %s, age = %s, gender = %s, phone = %s, email = %s, blood_group = %s, address = %s
            WHERE patient_id = %s
        """, (name, int(age), gender, phone, email, blood_group, address, patient_id))
        flash(f"Patient #{patient_id} updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating patient: {str(e)}", "error")

    return redirect(url_for("patients_list"))

@app.route("/patients/delete/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    try:
        execute_query("DELETE FROM patients WHERE patient_id = %s", (patient_id,))
        flash(f"Patient #{patient_id} deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting patient: {str(e)}", "error")
    return redirect(url_for("patients_list"))


# ----------------------------------------------------
# 👨‍⚕️ 3. DOCTOR MANAGEMENT
# ----------------------------------------------------
@app.route("/doctors")
def doctors_list():
    dept_filter = request.args.get("department", "").strip()
    search_query = request.args.get("search", "").strip()

    sql = "SELECT * FROM doctors WHERE 1=1"
    params = []

    if dept_filter:
        sql += " AND department = %s"
        params.append(dept_filter)

    if search_query:
        sql += " AND (name LIKE %s OR specialization LIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    sql += " ORDER BY name ASC"
    doctors = query_all(sql, tuple(params))

    all_docs = query_all("SELECT DISTINCT department FROM doctors ORDER BY department ASC")
    departments = [d["department"] for d in all_docs]

    return render_template(
        "doctors.html",
        doctors=doctors,
        departments=departments,
        selected_dept=dept_filter,
        search_query=search_query
    )

@app.route("/doctors/add", methods=["POST"])
def add_doctor():
    name = request.form.get("name", "").strip()
    specialization = request.form.get("specialization", "").strip()
    department = request.form.get("department", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    available_days = request.form.get("available_days", "Mon,Tue,Wed,Thu,Fri").strip()
    available_time = request.form.get("available_time", "09:00 AM - 05:00 PM").strip()

    if not name or not department or not specialization:
        flash("Doctor Name, Department, and Specialization are required.", "error")
        return redirect(url_for("doctors_list"))

    try:
        new_id = execute_query(
            "INSERT INTO doctors (name, specialization, department, phone, email, available_days, available_time) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (name, specialization, department, phone, email, available_days, available_time)
        )
        flash(f"Doctor '{name}' (ID: #{new_id}) added successfully!", "success")
    except Exception as e:
        flash(f"Error adding doctor: {str(e)}", "error")

    return redirect(url_for("doctors_list"))

@app.route("/doctors/edit/<int:doctor_id>", methods=["POST"])
def edit_doctor(doctor_id):
    name = request.form.get("name", "").strip()
    specialization = request.form.get("specialization", "").strip()
    department = request.form.get("department", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    available_days = request.form.get("available_days", "").strip()
    available_time = request.form.get("available_time", "").strip()

    try:
        execute_query("""
            UPDATE doctors 
            SET name = %s, specialization = %s, department = %s, phone = %s, email = %s, available_days = %s, available_time = %s
            WHERE doctor_id = %s
        """, (name, specialization, department, phone, email, available_days, available_time, doctor_id))
        flash(f"Doctor #{doctor_id} updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating doctor: {str(e)}", "error")

    return redirect(url_for("doctors_list"))

@app.route("/doctors/delete/<int:doctor_id>", methods=["POST"])
def delete_doctor(doctor_id):
    try:
        execute_query("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
        flash(f"Doctor #{doctor_id} removed successfully.", "success")
    except Exception as e:
        flash(f"Error deleting doctor: {str(e)}", "error")
    return redirect(url_for("doctors_list"))


# ----------------------------------------------------
# 📅 4. APPOINTMENT MANAGEMENT & DOUBLE-BOOKING LOGIC ⭐
# ----------------------------------------------------
@app.route("/appointments")
def appointments_list():
    date_filter = request.args.get("date", "").strip()
    status_filter = request.args.get("status", "").strip()
    search_query = request.args.get("search", "").strip()

    sql = """
        SELECT a.*, p.name as patient_name, p.phone as patient_phone, p.blood_group,
               d.name as doctor_name, d.department, d.specialization
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN doctors d ON a.doctor_id = d.doctor_id
        WHERE 1=1
    """
    params = []

    if date_filter:
        sql += " AND a.appointment_date = %s"
        params.append(date_filter)

    if status_filter:
        sql += " AND a.status = %s"
        params.append(status_filter)

    if search_query:
        sql += " AND (p.name LIKE %s OR d.name LIKE %s OR a.reason LIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

    sql += " ORDER BY a.appointment_date DESC, a.appointment_time ASC"
    appointments = query_all(sql, tuple(params))

    # Data needed for booking modal
    all_patients = query_all("SELECT patient_id, name, phone, age FROM patients ORDER BY name ASC")
    all_doctors = query_all("SELECT doctor_id, name, specialization, department FROM doctors ORDER BY department ASC, name ASC")
    departments = sorted(list(set(d["department"] for d in all_doctors)))

    return render_template(
        "appointments.html",
        appointments=appointments,
        patients=all_patients,
        doctors=all_doctors,
        departments=departments,
        date_filter=date_filter,
        status_filter=status_filter,
        search_query=search_query,
        today_str=date.today().strftime("%Y-%m-%d")
    )

@app.route("/api/doctor-slots")
def get_doctor_slots():
    """
    API endpoint: Prevents double booking!
    Given a doctor_id and appointment_date, calculates available and booked slots.
    Returns:
    [
        {"time": "10:00 AM", "status": "Booked", "available": False},
        {"time": "10:30 AM", "status": "Available", "available": True},
        ...
    ]
    """
    doctor_id = request.args.get("doctor_id")
    date_val = request.args.get("date")

    if not doctor_id or not date_val:
        return jsonify({"error": "doctor_id and date parameters are required"}), 400

    # Query existing active appointments for this doctor on this date
    booked_records = query_all("""
        SELECT appointment_time FROM appointments 
        WHERE doctor_id = %s AND appointment_date = %s AND status != 'Cancelled'
    """, (doctor_id, date_val))

    booked_times = set(r["appointment_time"].strip().upper() for r in booked_records)

    slot_data = []
    for slot in STANDARD_SLOTS:
        is_booked = slot.strip().upper() in booked_times
        slot_data.append({
            "time": slot,
            "status": "Booked" if is_booked else "Available",
            "available": not is_booked
        })

    return jsonify({"doctor_id": doctor_id, "date": date_val, "slots": slot_data})

@app.route("/appointments/book", methods=["POST"])
def book_appointment():
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    appointment_date = request.form.get("appointment_date")
    appointment_time = request.form.get("appointment_time")
    reason = request.form.get("reason", "").strip() or "General Checkup"
    status = request.form.get("status", "Confirmed")

    if not (patient_id and doctor_id and appointment_date and appointment_time):
        flash("All fields (Patient, Doctor, Date, and Time Slot) are required.", "error")
        return redirect(url_for("appointments_list"))

    # Strict double-booking check in Python + SQL
    conflict = query_one("""
        SELECT appointment_id FROM appointments 
        WHERE doctor_id = %s AND appointment_date = %s AND appointment_time = %s AND status != 'Cancelled'
    """, (doctor_id, appointment_date, appointment_time))

    if conflict:
        flash(f"Double-booking conflict! That doctor already has a booked appointment at {appointment_time} on {appointment_date}.", "error")
        return redirect(url_for("appointments_list"))

    try:
        app_id = execute_query("""
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (patient_id, doctor_id, appointment_date, appointment_time, reason, status))

        # If status is set to 'Waiting', automatically enqueue patient into FIFO queue!
        if status == "Waiting":
            pt = query_one("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
            doc = query_one("SELECT * FROM doctors WHERE doctor_id = %s", (doctor_id,))
            patient_queue.enqueue(pt, doc, app_id, reason)
            flash(f"Appointment #{app_id} booked & patient added to Waiting Queue (Token #{patient_queue.size()})!", "success")
        else:
            flash(f"Appointment #{app_id} successfully confirmed for {appointment_date} at {appointment_time}!", "success")

    except Exception as e:
        flash(f"Could not book appointment: {str(e)}", "error")

    return redirect(url_for("appointments_list"))

@app.route("/appointments/status/<int:appointment_id>", methods=["POST"])
def update_appointment_status(appointment_id):
    new_status = request.form.get("status")
    if new_status not in ["Confirmed", "Waiting", "Completed", "Cancelled"]:
        flash("Invalid appointment status.", "error")
        return redirect(url_for("appointments_list"))

    try:
        execute_query("UPDATE appointments SET status = %s WHERE appointment_id = %s", (new_status, appointment_id))
        
        # If changed to Waiting, enqueue into FIFO queue
        if new_status == "Waiting":
            app_rec = query_one("""
                SELECT a.*, p.name as patient_name, p.age, p.phone, p.blood_group,
                       d.name as doctor_name, d.department
                FROM appointments a
                JOIN patients p ON a.patient_id = p.patient_id
                JOIN doctors d ON a.doctor_id = d.doctor_id
                WHERE a.appointment_id = %s
            """, (appointment_id,))
            if app_rec:
                pt_dict = {"patient_id": app_rec["patient_id"], "name": app_rec["patient_name"], "age": app_rec["age"], "blood_group": app_rec["blood_group"], "phone": app_rec["phone"]}
                doc_dict = {"doctor_id": app_rec["doctor_id"], "name": app_rec["doctor_name"], "department": app_rec["department"]}
                ticket = patient_queue.enqueue(pt_dict, doc_dict, appointment_id, app_rec["reason"])
                flash(f"Appointment #{appointment_id} status updated to 'Waiting'. Assigned Queue Token #{ticket['token_id']}.", "success")
        elif new_status in ["Completed", "Cancelled"]:
            patient_queue.remove_by_appointment(appointment_id)
            flash(f"Appointment #{appointment_id} marked as {new_status}.", "success")
        else:
            flash(f"Appointment #{appointment_id} status updated to {new_status}.", "success")

    except Exception as e:
        flash(f"Error updating appointment: {str(e)}", "error")

    return redirect(request.referrer or url_for("appointments_list"))

@app.route("/appointments/cancel/<int:appointment_id>", methods=["POST"])
def cancel_appointment(appointment_id):
    try:
        execute_query("UPDATE appointments SET status = 'Cancelled' WHERE appointment_id = %s", (appointment_id,))
        patient_queue.remove_by_appointment(appointment_id)
        flash(f"Appointment #{appointment_id} cancelled. Time slot is now freed up for other patients.", "success")
    except Exception as e:
        flash(f"Error cancelling appointment: {str(e)}", "error")
    return redirect(request.referrer or url_for("appointments_list"))

@app.route("/appointments/reschedule/<int:appointment_id>", methods=["POST"])
def reschedule_appointment(appointment_id):
    new_date = request.form.get("reschedule_date")
    new_time = request.form.get("reschedule_time")

    app_rec = query_one("SELECT doctor_id FROM appointments WHERE appointment_id = %s", (appointment_id,))
    if not app_rec:
        flash("Appointment not found.", "error")
        return redirect(url_for("appointments_list"))

    doctor_id = app_rec["doctor_id"]

    # Check conflict
    conflict = query_one("""
        SELECT appointment_id FROM appointments 
        WHERE doctor_id = %s AND appointment_date = %s AND appointment_time = %s AND appointment_id != %s AND status != 'Cancelled'
    """, (doctor_id, new_date, new_time, appointment_id))

    if conflict:
        flash(f"Conflict: Selected slot {new_time} on {new_date} is already booked for this doctor.", "error")
        return redirect(url_for("appointments_list"))

    try:
        execute_query("""
            UPDATE appointments 
            SET appointment_date = %s, appointment_time = %s, status = 'Confirmed'
            WHERE appointment_id = %s
        """, (new_date, new_time, appointment_id))
        flash(f"Appointment #{appointment_id} rescheduled to {new_date} at {new_time}.", "success")
    except Exception as e:
        flash(f"Error rescheduling: {str(e)}", "error")

    return redirect(url_for("appointments_list"))


# ----------------------------------------------------
# 🧠 5. WAITING QUEUE (FIFO) DEDICATED ROOM
# ----------------------------------------------------
@app.route("/queue")
def queue_view():
    waiting_list = patient_queue.get_all()
    next_patient = patient_queue.peek()
    return render_template("queue.html", waiting_list=waiting_list, next_patient=next_patient, total_waiting=patient_queue.size())

@app.route("/queue/call-next", methods=["POST"])
def call_next():
    served = patient_queue.dequeue()
    if served:
        # Update corresponding appointment status to Completed in DB
        if served.get("appointment_id"):
            execute_query("UPDATE appointments SET status = 'Completed' WHERE appointment_id = %s", (served["appointment_id"],))
        flash(f"Now Calling Token #{served['token_id']} - Patient: {served['patient_name']} (Doctor: {served['doctor_name']})", "success")
    else:
        flash("Waiting queue is currently empty. No patients waiting.", "info")
    return redirect(request.referrer or url_for("queue_view"))

@app.route("/api/queue")
def api_queue():
    return jsonify({
        "size": patient_queue.size(),
        "next": patient_queue.peek(),
        "queue": patient_queue.get_all()
    })

if __name__ == "__main__":
    print(f"CarePulse Hospital Management System running with {get_db_type()}")
    app.run(debug=True, host="127.0.0.1", port=5000)
