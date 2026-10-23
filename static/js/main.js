// =========================================================
// CareSync Hospital Management System - Master JavaScript
// =========================================================

document.addEventListener('DOMContentLoaded', () => {
    initModals();
    initSlotPicker();
});

// 1. Modal Dialog Management
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';
    }
}

function initModals() {
    // Attach listener for patient edit buttons
    document.querySelectorAll('.edit-pt-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const ds = btn.dataset;
            openEditPatientModal(ds.id, ds.name, ds.age, ds.gender, ds.phone, ds.email, ds.blood, ds.address);
        });
    });

    // Close modal on background click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
                document.body.style.overflow = 'auto';
            }
        });
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(m => {
                m.classList.remove('active');
            });
            document.body.style.overflow = 'auto';
        }
    });
}

// 2. Dynamic Slot Picker & Double Booking Prevention ⭐
function initSlotPicker() {
    const doctorSelect = document.getElementById('bookDoctorSelect');
    const dateInput = document.getElementById('bookDateInput');
    const slotContainer = document.getElementById('slotsContainer');
    const timeHiddenInput = document.getElementById('selectedTimeInput');

    if (!doctorSelect || !dateInput || !slotContainer) return;

    function refreshSlots() {
        const doctorId = doctorSelect.value;
        const dateVal = dateInput.value;

        if (!doctorId || !dateVal) {
            slotContainer.innerHTML = '<p style="font-size:13px; color:#64748b; padding:10px;">Please select both a doctor and date to view time slots.</p>';
            if (timeHiddenInput) timeHiddenInput.value = '';
            return;
        }

        if (timeHiddenInput) timeHiddenInput.value = '';
        slotContainer.innerHTML = '<p style="font-size:13px; color:#0284c7; padding:10px;">⏳ Checking doctor availability & booked appointments...</p>';

        fetch(`/api/doctor-slots?doctor_id=${doctorId}&date=${dateVal}`)
            .then(res => {
                if (!res.ok) {
                    return res.json().then(data => {
                        throw new Error(data.error || 'Unable to load doctor availability.');
                    });
                }
                return res.json();
            })
            .then(data => {
                if (data.slots && data.slots.length > 0) {
                    let html = '<div class="slots-grid">';
                    data.slots.forEach(slot => {
                        if (slot.available) {
                            html += `
                                <div class="slot-btn available" data-time="${slot.time}" onclick="selectTimeSlot(this, '${slot.time}')">
                                    ${slot.time} <span style="font-size:11px; margin-left:4px;">✅</span>
                                </div>
                            `;
                        } else if (slot.status === 'Booked') {
                            html += `
                                <div class="slot-btn booked" title="Conflict: Doctor is already booked for this slot">
                                    ${slot.time} <span style="font-size:11px; margin-left:4px;">❌</span>
                                </div>
                            `;
                        } else {
                            html += `
                                <div class="slot-btn unavailable" title="Doctor is not scheduled for this time">
                                    ${slot.time} <span style="font-size:11px; margin-left:4px;">—</span>
                                </div>
                            `;
                        }
                    });
                    html += '</div>';
                    html += '<div style="margin-top:10px; font-size:11.5px; color:#64748b; display:flex; gap:14px;">' +
                            '<span><b style="color:#16a34a;">✅ Available</b> (Click to pick)</span>' +
                            '<span><b style="color:#dc2626;">❌ Booked</b> (Locked to prevent double booking)</span>' +
                            '<span><b style="color:#64748b;">— Unavailable</b> (Outside doctor schedule)</span>' +
                            '</div>';
                    slotContainer.innerHTML = html;
                } else {
                    slotContainer.innerHTML = '<p style="font-size:13px; color:#ef4444;">No slots configured for this doctor.</p>';
                }
            })
            .catch(err => {
                console.error("Failed to load doctor slots", err);
                slotContainer.innerHTML = `<p style="font-size:13px; color:#ef4444;">${err.message}</p>`;
            });
    }

    doctorSelect.addEventListener('change', refreshSlots);
    dateInput.addEventListener('change', refreshSlots);

    // Initial check if values are preset
    if (doctorSelect.value && dateInput.value) {
        refreshSlots();
    }
}

function selectTimeSlot(el, timeVal) {
    document.querySelectorAll('.slot-btn.available').forEach(btn => {
        btn.classList.remove('selected');
    });
    el.classList.add('selected');

    const hiddenInput = document.getElementById('selectedTimeInput');
    if (hiddenInput) {
        hiddenInput.value = timeVal;
    }
}

// 3. Form Validation for Booking Submission
function validateBookingForm(form) {
    const timeInput = form.querySelector('#selectedTimeInput');
    if (!timeInput || !timeInput.value) {
        alert("Please select an available (green ✅) time slot before booking.");
        return false;
    }
    return true;
}

// 4. Edit Patient Modal Populator
function openEditPatientModal(id, name, age, gender, phone, email, blood, address) {
    const form = document.getElementById('editPatientForm');
    if (!form) return;

    form.action = `/patients/edit/${id}`;
    form.querySelector('#editPtName').value = name;
    form.querySelector('#editPtAge').value = age;
    form.querySelector('#editPtGender').value = gender;
    form.querySelector('#editPtPhone').value = phone;
    form.querySelector('#editPtEmail').value = email || '';
    form.querySelector('#editPtBlood').value = blood || '';
    form.querySelector('#editPtAddress').value = address || '';

    openModal('editPatientModal');
}

// 5. Edit Doctor Modal Populator
function openEditDoctorModal(id, name, spec, dept, phone, email, days, time) {
    const form = document.getElementById('editDoctorForm');
    if (!form) return;

    form.action = `/doctors/edit/${id}`;
    form.querySelector('#editDocName').value = name;
    form.querySelector('#editDocSpec').value = spec;
    form.querySelector('#editDocDept').value = dept;
    form.querySelector('#editDocPhone').value = phone;
    form.querySelector('#editDocEmail').value = email || '';
    form.querySelector('#editDocDays').value = days || '';
    form.querySelector('#editDocTime').value = time || '';

    openModal('editDoctorModal');
}

// 6. Reschedule Appointment Modal Populator
function openRescheduleModal(appointmentId, currentDate, currentTime) {
    const form = document.getElementById('rescheduleForm');
    if (!form) return;

    form.action = `/appointments/reschedule/${appointmentId}`;
    form.querySelector('#rescheduleDate').value = currentDate;
    form.querySelector('#rescheduleTime').value = currentTime;

    openModal('rescheduleModal');
}
