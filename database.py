from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI", "")
client = MongoClient(MONGO_URI)
db = client["healthcare_chatbot"]

# Collections
patients = db["patients"]
appointments = db["appointments"]
chat_sessions = db["chat_sessions"]


def save_patient(name, age, gender, phone, email=None):
    """Save a new patient to MongoDB."""
    patient = {
        "name": name,
        "age": age,
        "gender": gender,
        "phone": phone,
        "email": email,
        "created_at": datetime.now()
    }
    result = patients.insert_one(patient)
    return str(result.inserted_id)


def get_patient_by_phone(phone):
    """Find patient by phone number."""
    return patients.find_one({"phone": phone})


def save_appointment(patient_id, problem, doctor_specialty, doctor_name, appointment_date, time_slot):
    """Save a new appointment."""
    appointment = {
        "patient_id": patient_id,
        "problem": problem,
        "doctor_specialty": doctor_specialty,
        "doctor_name": doctor_name,
        "appointment_date": appointment_date,
        "time_slot": time_slot,
        "status": "scheduled",
        "created_at": datetime.now()
    }
    result = appointments.insert_one(appointment)
    return str(result.inserted_id)


def get_available_slots(date):
    """Get available time slots for a given date."""
    all_slots = [
        "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
        "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
    ]

    # Find booked slots for the date
    booked = appointments.find({
        "appointment_date": date,
        "status": "scheduled"
    })
    booked_slots = [apt["time_slot"] for apt in booked]

    return [slot for slot in all_slots if slot not in booked_slots]


def get_appointment_details(appointment_id):
    """Get full appointment details with patient info."""
    appointment = appointments.find_one({"_id": ObjectId(appointment_id)})
    if appointment:
        patient = patients.find_one({"_id": ObjectId(appointment["patient_id"])})
        return {
            "appointment": appointment,
            "patient": patient
        }
    return None


def save_chat_session(session_id, state="greeting", collected_data=None, conversation_history=None):
    """Save or update chat session."""
    chat_sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "state": state,
                "collected_data": collected_data or {},
                "conversation_history": conversation_history or [],
                "updated_at": datetime.now()
            },
            "$setOnInsert": {
                "created_at": datetime.now()
            }
        },
        upsert=True
    )


def get_chat_session(session_id):
    """Get chat session by ID."""
    return chat_sessions.find_one({"session_id": session_id})


def get_patient_appointments(patient_id):
    """Get all appointments for a patient."""
    return list(appointments.find({"patient_id": patient_id}).sort("created_at", -1))


# ===============================
# Admin Functions
# ===============================

def get_all_appointments(limit=100, skip=0, status_filter=None):
    """Get all appointments with optional filtering."""
    query = {}
    if status_filter:
        query["status"] = status_filter

    appointment_list = list(
        appointments.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    # Enrich with patient details
    for apt in appointment_list:
        apt["_id"] = str(apt["_id"])
        patient = patients.find_one({"_id": ObjectId(apt["patient_id"])})
        if patient:
            apt["patient_name"] = patient.get("name", "Unknown")
            apt["patient_phone"] = patient.get("phone", "N/A")
            apt["patient_age"] = patient.get("age", "N/A")
            apt["patient_gender"] = patient.get("gender", "N/A")

    return appointment_list


def get_all_patients(limit=100, skip=0):
    """Get all patients."""
    patient_list = list(
        patients.find()
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )

    for patient in patient_list:
        patient["_id"] = str(patient["_id"])
        # Count appointments for each patient
        patient["appointment_count"] = appointments.count_documents({"patient_id": patient["_id"]})

    return patient_list


def update_appointment(appointment_id, update_data):
    """Update appointment details."""
    allowed_fields = ["status", "appointment_date", "time_slot", "doctor_name", "doctor_specialty", "notes"]
    filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    filtered_data["updated_at"] = datetime.now()

    result = appointments.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": filtered_data}
    )
    return result.modified_count > 0


def delete_appointment(appointment_id):
    """Delete an appointment."""
    result = appointments.delete_one({"_id": ObjectId(appointment_id)})
    return result.deleted_count > 0


def get_appointment_stats():
    """Get appointment statistics for dashboard."""
    total = appointments.count_documents({})
    scheduled = appointments.count_documents({"status": "scheduled"})
    completed = appointments.count_documents({"status": "completed"})
    cancelled = appointments.count_documents({"status": "cancelled"})
    total_patients = patients.count_documents({})

    # Today's appointments
    today = datetime.now().strftime("%d-%m-%Y")
    today_count = appointments.count_documents({"appointment_date": today})

    return {
        "total_appointments": total,
        "scheduled": scheduled,
        "completed": completed,
        "cancelled": cancelled,
        "total_patients": total_patients,
        "today_appointments": today_count
    }
