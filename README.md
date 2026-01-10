# Healthcare Chatbot - AI-Powered Appointment Booking System

A conversational AI chatbot that helps patients book doctor appointments through natural language conversation. Built with Flask, Google Gemini AI, and MongoDB.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [How It Works](#how-it-works)
- [Admin Panel](#admin-panel)

---

## Overview

This project is an AI-powered healthcare assistant named **"Care"** that guides patients through the appointment booking process using natural conversation. The chatbot collects patient information step-by-step, suggests appropriate doctors based on symptoms, and confirms bookings with email notifications.

### Key Highlights

- **Conversational AI**: Uses Google Gemini 2.0 Flash for natural, human-like responses
- **Smart Data Extraction**: Automatically extracts patient details from conversation
- **Real-time Slot Management**: Shows only available time slots
- **Email Confirmations**: Sends HTML email receipts to patients
- **PDF Generation**: Creates downloadable consultation slips
- **Admin Dashboard**: Full management interface for appointments

---

## Features

### Patient Features
- Natural language conversation for booking
- Automatic doctor specialty suggestion based on symptoms
- Real-time availability checking
- Email confirmation with appointment details
- PDF consultation slip generation

### Admin Features
- Secure login authentication
- Dashboard with statistics (total appointments, scheduled, completed, cancelled)
- View all appointments and patients
- Edit appointment status, date, time
- Delete appointments
- Filter appointments by status

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Flask 3.0.0 | Python web framework for API and routing |
| **AI Model** | Google Gemini 2.0 Flash | Natural language understanding and response generation |
| **Database** | MongoDB Atlas | Cloud NoSQL database for storing patients, appointments, sessions |
| **PDF Generation** | FPDF 1.7.2 | Creating consultation slip PDFs |
| **Email** | SMTP (Gmail) | Sending confirmation emails |
| **Frontend** | HTML/CSS/JavaScript | Chat interface and admin dashboard |
| **Environment** | python-dotenv | Managing environment variables |

---

## Project Structure

```
Healthcare Chatbot/
├── app.py                 # Main Flask application
├── database.py            # MongoDB database operations
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (API keys, credentials)
├── templates/
│   ├── index.html         # Chat interface
│   ├── admin.html         # Admin dashboard
│   └── admin_login.html   # Admin login page
├── slips/                 # Generated PDF consultation slips
└── venv/                  # Python virtual environment
```

---

## Dependencies

### requirements.txt

```
flask==3.0.0
google-generativeai==0.8.0
pymongo==4.6.1
fpdf==1.7.2
python-dotenv==1.0.0
```

### Dependency Breakdown

| Package | Version | Why It's Used |
|---------|---------|---------------|
| **flask** | 3.0.0 | Lightweight web framework for building the REST API, serving templates, handling sessions |
| **google-generativeai** | 0.8.0 | Official Google SDK for accessing Gemini AI models for natural language processing |
| **pymongo** | 4.6.1 | MongoDB driver for Python - connects to MongoDB Atlas for data persistence |
| **fpdf** | 1.7.2 | Simple PDF generation library for creating consultation slips |
| **python-dotenv** | 1.0.0 | Loads environment variables from .env file for secure credential management |

### Built-in Libraries Used

| Library | Purpose |
|---------|---------|
| `smtplib` | Sending emails via Gmail SMTP |
| `email.mime` | Creating HTML email messages |
| `json` | Parsing AI responses and API data |
| `uuid` | Generating unique session IDs |
| `re` | Regex for extracting data from AI responses |
| `datetime` | Date/time handling for appointments |
| `functools` | Decorator for admin authentication |
| `os` | Environment variables and file operations |

---

## Installation

### Prerequisites

- Python 3.8+
- MongoDB Atlas account (or local MongoDB)
- Google Cloud account with Gemini API access
- Gmail account with App Password enabled

### Steps

1. **Clone/Download the project**

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables** (see Configuration section)

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   - Chat: http://localhost:5000
   - Admin: http://localhost:5000/admin

---

## Configuration

Create a `.env` file in the project root:

```env
# Google Gemini AI
GEMINI_API_KEY="your-gemini-api-key"

# MongoDB Atlas
MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/"

# Flask Secret Key
SECRET_KEY="your-secret-key"

# Admin Credentials
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin123"

# Email (Gmail SMTP)
SMTP_EMAIL="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
```

### Getting API Keys

1. **Gemini API Key**:
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key

2. **MongoDB URI**:
   - Create a free cluster at [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Get connection string from Database > Connect

3. **Gmail App Password**:
   - Enable 2FA on your Google account
   - Go to Security > App Passwords
   - Generate a new app password for "Mail"

---

## Usage

### Chat Flow

The chatbot follows this conversation flow:

```
1. Greeting → Ask for Name
2. Name → Ask for Age
3. Age → Ask for Gender
4. Gender → Ask for Phone
5. Phone → Ask for Email
6. Email → Ask for Health Problem
7. Problem → Suggest Doctor + Ask for Date
8. Date → Show Available Slots
9. Time Slot → Show Summary + Confirm
10. Confirmation → Book Appointment + Send Email
```

### Example Conversation

```
Bot: Hey there! I'm Care. I can help you book a doctor's appointment. What's your name?
User: My name is Ankit
Bot: Hey Ankit, nice to meet you! How old are you?
User: 21
Bot: Awesome! What's your gender?
User: male
Bot: Gotcha. What's your phone number?
User: 9301961290
Bot: Cool, thanks! What's your email address?
User: ankit@gmail.com
Bot: And what's the problem you're experiencing?
User: I have headache and fever
Bot: Oh no, that sounds rough! Which date would you like to book?
User: tomorrow
Bot: What time slot would you like? Available: 09:00 AM, 10:00 AM...
User: 10:00 AM
Bot: Perfect! Here's your booking summary... Does that look correct?
User: yes
Bot: Awesome, you're all set! [Booking details + Email sent]
```

---

## API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Chat interface |
| POST | `/api/start` | Start new chat session |
| POST | `/api/chat` | Send message to chatbot |

### Admin Endpoints (Protected)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/admin/login` | Admin login |
| GET | `/admin/logout` | Admin logout |
| GET | `/admin` | Admin dashboard |
| GET | `/api/admin/stats` | Get statistics |
| GET | `/api/admin/appointments` | Get all appointments |
| PUT | `/api/admin/appointments/:id` | Update appointment |
| DELETE | `/api/admin/appointments/:id` | Delete appointment |
| GET | `/api/admin/patients` | Get all patients |

### Request/Response Examples

**Start Chat**
```bash
POST /api/start
Response: {
  "response": "Hey there! I'm Care...",
  "session_id": "uuid-here"
}
```

**Send Message**
```bash
POST /api/chat
Body: {
  "message": "My name is Ankit",
  "session_id": "uuid-here"
}
Response: {
  "response": "Hey Ankit, nice to meet you!",
  "session_id": "uuid-here",
  "state": "chatting"
}
```

---

## Database Schema

### MongoDB Collections

#### patients
```json
{
  "_id": "ObjectId",
  "name": "string",
  "age": "number",
  "gender": "string",
  "phone": "string",
  "email": "string",
  "created_at": "datetime"
}
```

#### appointments
```json
{
  "_id": "ObjectId",
  "patient_id": "string",
  "problem": "string",
  "doctor_specialty": "string",
  "doctor_name": "string",
  "appointment_date": "string (DD-MM-YYYY)",
  "time_slot": "string",
  "status": "scheduled | completed | cancelled",
  "created_at": "datetime"
}
```

#### chat_sessions
```json
{
  "_id": "ObjectId",
  "session_id": "string (UUID)",
  "state": "string",
  "collected_data": "object",
  "conversation_history": "array",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## How It Works

### AI Response Generation

1. **System Prompt**: Defines the chatbot personality ("Care" - friendly healthcare assistant)
2. **Context Injection**: Passes collected data and missing fields to AI
3. **JSON Response**: AI responds with structured JSON containing:
   - `message`: Response text to show user
   - `extracted_data`: Any information extracted from user message
   - `doctor_specialty`: Suggested doctor type
   - `is_booking_confirmed`: Boolean for booking confirmation

### Data Extraction Flow

```
User says: "My name is Ankit and I'm 21"
           ↓
AI extracts: {"name": "Ankit", "age": 21}
           ↓
Merged into collected_data
           ↓
Next question asked for missing field
```

### Session Management

- **In-Memory Cache**: Fast access for active conversations
- **MongoDB Persistence**: Sessions saved every 5 messages or on booking
- **UUID Session IDs**: Unique identifier for each conversation

### Available Time Slots

Default slots: `09:00 AM, 10:00 AM, 11:00 AM, 12:00 PM, 02:00 PM, 03:00 PM, 04:00 PM, 05:00 PM`

Booked slots are automatically filtered out based on date.

---

## Admin Panel

### Access
- URL: http://localhost:5000/admin
- Default credentials: `admin` / `admin123`

### Dashboard Features

1. **Statistics Cards**
   - Total Appointments
   - Scheduled/Completed/Cancelled counts
   - Total Patients
   - Today's Appointments

2. **Appointments Table**
   - Patient details (name, phone, age, gender)
   - Doctor and specialty
   - Date and time
   - Health problem
   - Status with color badges
   - Edit/Delete actions

3. **Patients Table**
   - All registered patients
   - Appointment count per patient
   - Registration date

4. **Filters**
   - All / Scheduled / Completed / Cancelled

---

## Gemini AI Configuration

```python
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",  # Fast, efficient model
    generation_config={
        "temperature": 0.7,          # Balanced creativity
        "max_output_tokens": 2048,   # Prevent response truncation
    }
)
```

### Why Gemini 2.0 Flash?
- Fast response times (~1-2 seconds)
- Good at following structured output (JSON)
- Cost-effective for conversational applications
- Excellent natural language understanding

---

## Error Handling

### JSON Parsing Fallback
If AI returns malformed JSON, the system uses regex to extract:
- Message content
- Individual data fields (name, age, phone, email, etc.)
- Booking confirmation status

### Email Failures
- Gracefully handled - booking still completes
- Error logged to console
- User informed if email fails

---

## Security Considerations

1. **Environment Variables**: Sensitive data stored in `.env` (not committed)
2. **Session-Based Auth**: Flask sessions for admin authentication
3. **Protected Routes**: `@admin_required` decorator on admin endpoints
4. **Input Validation**: Basic validation on all user inputs

---

## Future Improvements

- [ ] Multiple doctor management
- [ ] Patient login/registration
- [ ] Appointment rescheduling via chat
- [ ] SMS notifications
- [ ] Payment integration
- [ ] Multi-language support
- [ ] Voice input support

---

## License

This project is for educational purposes.

---

## Author

Built with Google Gemini AI, Flask, and MongoDB.
