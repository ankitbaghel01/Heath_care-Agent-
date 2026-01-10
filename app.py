import google.generativeai as genai
import os
import json
import uuid
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from functools import wraps
from fpdf import FPDF
from dotenv import load_dotenv
from database import (
    save_patient, save_appointment, get_available_slots,
    save_chat_session, get_chat_session, get_appointment_details,
    get_all_appointments, get_all_patients, update_appointment,
    delete_appointment, get_appointment_stats
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "healthcare-chatbot-secret-key")

# Admin Credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


# Login Required Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# Gemini Configuration - Optimized for speed
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",  # Latest fast model
    generation_config={
        "temperature": 0.7,
        "max_output_tokens": 2048,  # Further increased to prevent truncation
    }
)

# In-memory session cache for faster access
session_cache = {}

# Required fields for booking
REQUIRED_FIELDS = ["name", "age", "gender", "phone", "email", "problem", "appointment_date", "time_slot"]

# Email Configuration
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_confirmation_email(patient_data):
    """Send appointment confirmation email to patient."""
    try:
        # Email configuration from env
        smtp_email = os.getenv("SMTP_EMAIL")
        smtp_password = os.getenv("SMTP_PASSWORD")

        if not smtp_email or not smtp_password:
            print("Email not configured - skipping email send")
            return False

        patient_email = patient_data.get("email")
        if not patient_email:
            return False

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Appointment Confirmation - {patient_data.get('appointment_date')}"
        msg['From'] = smtp_email
        msg['To'] = patient_email

        # HTML Email content
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #00b4db, #0083b0); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0;">Appointment Confirmed!</h1>
            </div>

            <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px;">
                <p>Dear <strong>{patient_data.get('name')}</strong>,</p>

                <p>Your appointment has been successfully booked. Here are your details:</p>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #0083b0; margin-top: 0;">Patient Information</h3>
                    <p><strong>Name:</strong> {patient_data.get('name')}</p>
                    <p><strong>Age:</strong> {patient_data.get('age')} years</p>
                    <p><strong>Gender:</strong> {patient_data.get('gender')}</p>
                    <p><strong>Phone:</strong> {patient_data.get('phone')}</p>
                </div>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #0083b0; margin-top: 0;">Appointment Details</h3>
                    <p><strong>Doctor:</strong> {patient_data.get('doctor_name')}</p>
                    <p><strong>Specialty:</strong> {patient_data.get('doctor_specialty')}</p>
                    <p><strong>Date:</strong> {patient_data.get('appointment_date')}</p>
                    <p><strong>Time:</strong> {patient_data.get('time_slot')}</p>
                </div>

                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #0083b0; margin-top: 0;">Health Concern</h3>
                    <p>{patient_data.get('problem')}</p>
                </div>

                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Please arrive 10-15 minutes before your scheduled time.</strong></p>
                </div>

                <p>If you need to reschedule or cancel, please contact us as soon as possible.</p>

                <p>Take care and get well soon!</p>

                <p style="color: #666; margin-top: 30px;">
                    Best regards,<br>
                    <strong>Healthcare Team</strong>
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)

        print(f"Confirmation email sent to {patient_email}")
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def get_ai_response(conversation_history, collected_data, available_slots=None):
    """Get dynamic AI response based on conversation context."""

    collected_str = json.dumps(collected_data, indent=2) if collected_data else "{}"
    missing_fields = [f for f in REQUIRED_FIELDS if f not in collected_data or not collected_data.get(f)]

    slots_info = ""
    if available_slots:
        slots_info = f"\nAvailable time slots: {', '.join(available_slots)}"

    system_prompt = f"""You are Care - a friendly, human-like healthcare assistant. Talk naturally like texting a friend, not like a formal bot.

YOUR STYLE:
- Be casual and warm - like chatting with a helpful friend
- Keep it SHORT - 1-2 sentences max, never long paragraphs
- Use everyday language: "Cool!", "Awesome", "No worries", "Gotcha"
- If they ask about you or go off-topic, answer briefly then gently steer back
- Show you care when they mention health problems
- Don't be overly formal or use phrases like "dear" or "if you don't mind"
- Sound natural, not scripted

INFORMATION COLLECTED SO FAR:
{collected_str}

STILL NEEDED: {', '.join(missing_fields) if missing_fields else 'All info collected - ASK FOR CONFIRMATION NOW!'}
{slots_info}

BOOKING FLOW (ask one thing at a time):
name -> age -> gender -> phone -> email -> problem -> appointment_date -> time_slot -> CONFIRM

RULES:
1. Respond naturally to what user said, then ask for next missing info
2. Extract any info they gave into extracted_data
3. For time_slot, only offer from available slots
4. When all info collected, summarize and ask to confirm
5. If they confirm (yes/sure/book it), set is_booking_confirmed: true
6. When they mention health problem, suggest appropriate doctor_specialty and doctor_name

EXTRACTION RULES:
- "my name is X" or "I'm X" = extract name: X
- If user just says "hi/hello", DON'T extract it as name!
- For age: extract numbers
- For gender: male/m = "Male", female/f = "Female"
- For phone: extract 10 digit number
- For email: extract valid email address
- For date: "today" = today's date, "tomorrow" = tomorrow
- "yes/confirm/book it/sure/ok" = is_booking_confirmed: true

RESPOND WITH VALID JSON ONLY (no extra text):
{{"message": "your response", "extracted_data": {{}}, "doctor_specialty": "", "doctor_name": "", "is_booking_confirmed": false, "is_booking_cancelled": false}}

IMPORTANT: Output ONLY the JSON object, nothing else. No markdown, no explanation."""

    # Only last 5 messages for context (reduces tokens)
    conv_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]])
    full_prompt = f"{system_prompt}\n\nCONVERSATION:\n{conv_text}\n\nJSON:"

    try:
        response = model.generate_content(full_prompt)
        text = response.text.strip()
        print(f"[DEBUG] Raw AI response: {text[:200]}...")

        # Extract JSON from various formats
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        # Try to find JSON object in text
        text = text.strip()
        if not text.startswith("{"):
            # Find first { and last }
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                text = text[start:end]

        # Fix common JSON issues
        text = text.replace("'", '"')  # Single to double quotes
        text = re.sub(r',\s*}', '}', text)  # Remove trailing commas
        text = re.sub(r',\s*]', ']', text)  # Remove trailing commas in arrays

        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"AI JSON Error: {e}")
        print(f"Raw response: {response.text if 'response' in dir() else 'N/A'}")

        # Try to extract all fields using regex as fallback
        raw_text = response.text if 'response' in dir() else ""

        result = {
            "message": "Could you say that again?",
            "extracted_data": {},
            "is_booking_confirmed": False,
            "is_booking_cancelled": False
        }

        # Extract message
        msg_match = re.search(r'"message"\s*:\s*"([^"]*)"', raw_text)
        if msg_match:
            result["message"] = msg_match.group(1)

        # Try to extract extracted_data fields
        extracted = {}
        field_patterns = {
            "name": r'"name"\s*:\s*"([^"]*)"',
            "age": r'"age"\s*:\s*(\d+)',
            "gender": r'"gender"\s*:\s*"([^"]*)"',
            "phone": r'"phone"\s*:\s*"?(\d{10})"?',
            "email": r'"email"\s*:\s*"([^"@\s]+@[^"\s]+)"',
            "problem": r'"problem"\s*:\s*"([^"]*)"',
            "appointment_date": r'"appointment_date"\s*:\s*"([^"]*)"',
            "time_slot": r'"time_slot"\s*:\s*"([^"]*)"'
        }

        for field, pattern in field_patterns.items():
            match = re.search(pattern, raw_text)
            if match:
                extracted[field] = match.group(1)

        if extracted:
            result["extracted_data"] = extracted

        # Check for booking confirmation
        if re.search(r'"is_booking_confirmed"\s*:\s*true', raw_text, re.IGNORECASE):
            result["is_booking_confirmed"] = True

        return result
    except Exception as e:
        print(f"AI Error: {e}")
        return {"message": "Sorry, could you say that again?", "extracted_data": {}, "is_booking_confirmed": False, "is_booking_cancelled": False}


def get_doctor_suggestion(problem):
    """Get doctor specialty suggestion from Gemini."""
    prompt = f"""Based on this health issue, suggest the most appropriate doctor specialty.

Health Issue: {problem}

Respond in JSON format only:
{{"specialty": "specialty name", "doctor_name": "Dr. [Indian name]", "reason": "one line reason"}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except:
        return {
            "specialty": "General Physician",
            "doctor_name": "Dr. Sharma",
            "reason": "For initial consultation"
        }


def parse_date(date_str):
    """Parse date from various formats."""
    date_str = date_str.lower().strip()

    if "today" in date_str:
        return datetime.now().strftime("%d-%m-%Y")
    elif "tomorrow" in date_str:
        return (datetime.now() + timedelta(days=1)).strftime("%d-%m-%Y")
    else:
        # Try to extract date pattern
        cleaned = date_str.replace("/", "-").replace(".", "-")
        return cleaned


def process_message(session_id, user_message):
    """Process user message - OPTIMIZED with memory cache."""

    # Use memory cache first (faster), fallback to DB
    if session_id in session_cache:
        conversation_history = session_cache[session_id].get("conversation_history", [])
        collected_data = session_cache[session_id].get("collected_data", {})
    else:
        chat_session = get_chat_session(session_id)
        if chat_session:
            conversation_history = chat_session.get("conversation_history", [])
            collected_data = chat_session.get("collected_data", {})
        else:
            conversation_history = []
            collected_data = {}

    # Handle initial greeting (empty message = start)
    if not user_message and not conversation_history:
        response_msg = "Hey there! I'm Care. I can help you book a doctor's appointment. What's your name?"
        conversation_history.append({"role": "assistant", "content": response_msg})
        save_chat_session(session_id, "chatting", collected_data, conversation_history)
        return {"response": response_msg, "state": "chatting", "collected_data": collected_data}

    # Add user message to history
    if user_message:
        conversation_history.append({"role": "user", "content": user_message})

    # Check for available slots if we have a date but no slot yet
    available_slots = None
    if collected_data.get("appointment_date") and not collected_data.get("time_slot"):
        available_slots = get_available_slots(collected_data["appointment_date"])
        collected_data["available_slots"] = available_slots

    # Get AI response
    ai_result = get_ai_response(conversation_history, collected_data, available_slots)

    # Update collected data with extracted info
    if ai_result.get("extracted_data"):
        for key, value in ai_result["extracted_data"].items():
            if value:  # Only update if value is not empty
                if key == "appointment_date":
                    value = parse_date(str(value))
                collected_data[key] = value

    response_msg = ai_result.get("message", "I'm here to help!")

    # Get doctor info from AI response (no second API call!)
    if ai_result.get("doctor_specialty") and ai_result["doctor_specialty"] != "if problem":
        collected_data["doctor_specialty"] = ai_result["doctor_specialty"]
        collected_data["doctor_name"] = ai_result.get("doctor_name", "Dr. Sharma")

    # Handle booking confirmation
    if ai_result.get("is_booking_confirmed"):
        # Save to database
        patient_id = save_patient(
            collected_data.get("name", "Patient"),
            collected_data.get("age", 0),
            collected_data.get("gender", "Other"),
            collected_data.get("phone", ""),
            collected_data.get("email", "")
        )

        appointment_id = save_appointment(
            patient_id,
            collected_data.get("problem", ""),
            collected_data.get("doctor_specialty", "General"),
            collected_data.get("doctor_name", "Dr. Sharma"),
            collected_data.get("appointment_date", ""),
            collected_data.get("time_slot", "")
        )

        collected_data["patient_id"] = patient_id
        collected_data["appointment_id"] = appointment_id

        # Generate PDF
        try:
            pdf_path = generate_pdf(collected_data)
            collected_data["pdf_path"] = pdf_path
        except Exception as e:
            print(f"PDF error: {e}")

        # Send confirmation email
        email_sent = send_confirmation_email(collected_data)

        response_msg = f"Awesome, you're all set! Here's your booking:\n\n"
        response_msg += f"**Appointment ID:** {appointment_id[:8]}\n"
        response_msg += f"**Patient:** {collected_data.get('name')}\n"
        response_msg += f"**Doctor:** {collected_data.get('doctor_name')} ({collected_data.get('doctor_specialty')})\n"
        response_msg += f"**Date:** {collected_data.get('appointment_date')}\n"
        response_msg += f"**Time:** {collected_data.get('time_slot')}\n"
        response_msg += f"**Problem:** {collected_data.get('problem')}\n\n"

        if email_sent:
            response_msg += f"A confirmation email has been sent to **{collected_data.get('email')}**.\n\n"

        response_msg += "Please arrive 10-15 mins early. Take care and get well soon!"

        # Reset for new booking
        collected_data = {}

    # Handle booking cancellation
    if ai_result.get("is_booking_cancelled"):
        response_msg = "No problem at all! We can start fresh whenever you're ready. Just say hi!"
        collected_data = {}

    # Add assistant response to history
    conversation_history.append({"role": "assistant", "content": response_msg})

    # Save to memory cache (fast)
    session_cache[session_id] = {
        "conversation_history": conversation_history,
        "collected_data": collected_data
    }

    # Save to DB only on booking or every 5 messages (reduces DB calls)
    if ai_result.get("is_booking_confirmed") or len(conversation_history) % 5 == 0:
        save_chat_session(session_id, "chatting", collected_data, conversation_history)

    return {
        "response": response_msg,
        "state": "chatting",
        "collected_data": collected_data
    }


def generate_pdf(data):
    """Generate PDF consultation slip."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    # Header
    pdf.cell(190, 10, "Healthcare Consultation Slip", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", size=12)

    # Patient Details
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, "Patient Information", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 7, f"Name: {data.get('name', 'N/A')}", ln=True)
    pdf.cell(190, 7, f"Age: {data.get('age', 'N/A')}", ln=True)
    pdf.cell(190, 7, f"Gender: {data.get('gender', 'N/A')}", ln=True)
    pdf.cell(190, 7, f"Phone: {data.get('phone', 'N/A')}", ln=True)
    pdf.ln(5)

    # Health Concern
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, "Health Concern", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(190, 7, f"{data.get('problem', 'N/A')}")
    pdf.ln(5)

    # Appointment Details
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 8, "Appointment Details", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(190, 7, f"Doctor: {data.get('doctor_name', 'N/A')}", ln=True)
    pdf.cell(190, 7, f"Specialty: {data.get('doctor_specialty', 'N/A')}", ln=True)
    pdf.cell(190, 7, f"Date: {data.get('appointment_date', 'N/A')}", ln=True)
    pdf.cell(190, 7, f"Time: {data.get('time_slot', 'N/A')}", ln=True)
    pdf.ln(10)

    # Footer
    pdf.set_font("Arial", "I", 10)
    pdf.cell(190, 7, "Please arrive 10 minutes before your scheduled time.", ln=True, align="C")
    pdf.cell(190, 7, f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True, align="C")

    # Save PDF
    filename = f"slips/consultation_{data.get('name', 'patient').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    os.makedirs("slips", exist_ok=True)
    pdf.output(filename)

    return filename


# ===============================
# Flask Routes
# ===============================

@app.route("/")
def index():
    """Render the chat interface."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle chat messages."""
    data = request.json
    user_message = data.get("message", "")
    session_id = data.get("session_id")

    if not session_id:
        session_id = str(uuid.uuid4())

    # Process the message
    result = process_message(session_id, user_message)

    return jsonify({
        "response": result["response"],
        "session_id": session_id,
        "state": result["state"]
    })


@app.route("/api/start", methods=["POST"])
def start_chat():
    """Start a new chat session."""
    session_id = str(uuid.uuid4())
    result = process_message(session_id, "")

    return jsonify({
        "response": result["response"],
        "session_id": session_id
    })


@app.route("/api/download/<appointment_id>")
def download_slip(appointment_id):
    """Download consultation slip PDF."""
    from flask import send_file
    details = get_appointment_details(appointment_id)
    if details:
        # Generate PDF on-demand if needed
        pass
    return jsonify({"error": "Appointment not found"}), 404


# ===============================
# Admin Authentication Routes
# ===============================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login page."""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid username or password"

    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    """Admin logout."""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))


# ===============================
# Admin Routes (Protected)
# ===============================

@app.route("/admin")
@admin_required
def admin_dashboard():
    """Render the admin dashboard."""
    return render_template("admin.html")


@app.route("/api/admin/stats")
@admin_required
def admin_stats():
    """Get dashboard statistics."""
    stats = get_appointment_stats()
    return jsonify(stats)


@app.route("/api/admin/appointments")
@admin_required
def admin_appointments():
    """Get all appointments."""
    status = request.args.get("status")
    limit = int(request.args.get("limit", 100))
    skip = int(request.args.get("skip", 0))

    appointments_list = get_all_appointments(limit=limit, skip=skip, status_filter=status)
    return jsonify(appointments_list)


@app.route("/api/admin/appointments/<appointment_id>", methods=["PUT"])
@admin_required
def admin_update_appointment(appointment_id):
    """Update an appointment."""
    data = request.json
    success = update_appointment(appointment_id, data)
    if success:
        return jsonify({"success": True, "message": "Appointment updated"})
    return jsonify({"success": False, "message": "Update failed"}), 400


@app.route("/api/admin/appointments/<appointment_id>", methods=["DELETE"])
@admin_required
def admin_delete_appointment(appointment_id):
    """Delete an appointment."""
    success = delete_appointment(appointment_id)
    if success:
        return jsonify({"success": True, "message": "Appointment deleted"})
    return jsonify({"success": False, "message": "Delete failed"}), 400


@app.route("/api/admin/patients")
@admin_required
def admin_patients():
    """Get all patients."""
    limit = int(request.args.get("limit", 100))
    skip = int(request.args.get("skip", 0))

    patients_list = get_all_patients(limit=limit, skip=skip)
    return jsonify(patients_list)


if __name__ == "__main__":
    os.makedirs("slips", exist_ok=True)
    os.makedirs("templates", exist_ok=True)

    print("=" * 50)
    print("  Healthcare Chatbot Server")
    print("=" * 50)
    print("  Web: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000, use_reloader=False)
