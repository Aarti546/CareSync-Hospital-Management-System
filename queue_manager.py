from collections import deque
from datetime import datetime

class WaitingQueue:
    """
    FIFO (First-In, First-Out) Queue implementation for hospital patient waiting room.
    Uses Python's collections.deque for efficient O(1) enqueue and dequeue operations.
    Handles patient records formatted as structured Python Dictionaries.
    """
    def __init__(self):
        # The internal queue data structure (Deque)
        self._queue = deque()
        self._counter = 100

    def enqueue(self, patient_dict, doctor_dict=None, appointment_id=None, reason=None):
        """
        Add a patient to the end (rear) of the waiting queue.
        Patient data is stored as a Python Dictionary.
        """
        self._counter += 1
        ticket = {
            "token_id": self._counter,
            "appointment_id": appointment_id,
            "patient_id": patient_dict.get("patient_id"),
            "patient_name": patient_dict.get("name"),
            "age": patient_dict.get("age"),
            "blood_group": patient_dict.get("blood_group"),
            "phone": patient_dict.get("phone"),
            "doctor_id": doctor_dict.get("doctor_id") if doctor_dict else None,
            "doctor_name": doctor_dict.get("name") if doctor_dict else "General Duty",
            "department": doctor_dict.get("department") if doctor_dict else "OPD",
            "reason": reason or "Consultation",
            "joined_time": datetime.now().strftime("%I:%M %p"),
            "status": "Waiting"
        }
        self._queue.append(ticket)
        return ticket

    def dequeue(self):
        """
        Remove and return the patient from the front (head) of the queue.
        FIFO: The patient who waited the longest is served first.
        """
        if self.is_empty():
            return None
        served_patient = self._queue.popleft()
        served_patient["status"] = "Serving"
        served_patient["served_time"] = datetime.now().strftime("%I:%M %p")
        return served_patient

    def peek(self):
        """
        Inspect the patient next in line without removing them from the queue.
        """
        if self.is_empty():
            return None
        return self._queue[0]

    def get_all(self):
        """
        Returns a Python List of all waiting patients in chronological order.
        """
        return list(self._queue)

    def size(self):
        """Returns the count of patients currently waiting in the queue."""
        return len(self._queue)

    def is_empty(self):
        """Checks if the waiting queue is empty."""
        return len(self._queue) == 0

    def remove_by_appointment(self, appointment_id):
        """Removes a patient from the queue if their appointment is cancelled or completed."""
        for i, ticket in enumerate(self._queue):
            if ticket.get("appointment_id") == appointment_id:
                del self._queue[i]
                return True
        return False

# Global instance of the waiting queue accessible across the Flask app
patient_queue = WaitingQueue()
