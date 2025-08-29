# 🚀 Darija Transcription Dashboard

A clean, simple dashboard for Moroccan Arabic (Darija) speech transcription with token management and Google API integration.

## ✨ Features

- **🔐 Admin Authentication**: Admin-only access (no public registration)
- **🔑 API Token Management**: Generate and manage API tokens for application integration
- **🎤 Audio Transcription**: Test audio files and get transcriptions in Darija, Arabic, and French
- **⚙️ Google API Integration**: Configure your Google Cloud Speech-to-Text API key
- **📊 Usage Statistics**: Track transcriptions and API usage
- **🌐 RESTful API**: Integrate transcription into your applications

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd dashboard
pip3 install -r requirements.txt
```

### 2. Run the Application
```bash
python3 app.py
```

### 3. Access Dashboard
Open your browser and go to: **http://localhost:5001**

### 4. Admin Login
- **Username**: admin
- **Password**: admin123
- **⚠️ Important**: Change the admin password after first login

## 📁 Project Structure

```
dashboard/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── dashboard.db          # SQLite database (auto-created)
├── uploads/              # Temporary audio file storage
├── templates/            # HTML templates
│   ├── base.html        # Base template with navigation
│   ├── landing.html     # Homepage
│   ├── login.html       # Login page
│   ├── register.html    # Registration page
│   ├── dashboard.html   # Main dashboard
│   ├── tokens.html      # API token management
│   ├── test.html        # Audio testing page
│   └── settings.html    # Settings & Google API config
└── README.md            # This file
```

## 🔑 API Usage

### Authentication
Include your API token in the request header:
```bash
X-API-Token: YOUR_TOKEN_HERE
```

### Transcribe Audio
```bash
curl -X POST http://localhost:5001/api/v1/transcribe \
  -H "X-API-Token: YOUR_TOKEN" \
  -F "audio=@audio.wav"
```

### Response
```json
{
  "success": true,
  "transcription": "شحال باقي فالصنداله",
  "id": 123
}
```

## ⚙️ Google API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable "Cloud Speech-to-Text API"
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy the API key
6. Go to Settings in the dashboard and paste your API key

## 💰 Pricing

- **Free Tier**: 60 minutes/month free with Google API
- **After Free Tier**: $0.024 per minute

## 🔒 Security Notes

- **Admin-only access**: No public registration allowed
- **Default credentials**: Must be changed after first login
- Passwords are hashed using Werkzeug's security functions
- API tokens are randomly generated using Python's secrets module
- In production, use HTTPS and encrypt sensitive data
- Use environment variables for secret keys

## 📊 Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: User email
- `password_hash`: Hashed password
- `google_api_key`: Google Cloud API key (encrypt in production)
- `created_at`: Registration date

### ApiToken Table
- `id`: Primary key
- `token`: Unique API token
- `name`: Token description
- `user_id`: Owner user ID
- `created_at`: Creation date
- `last_used`: Last usage timestamp
- `usage_count`: Number of API calls
- `is_active`: Token status
- `rate_limit`: Max requests per hour

### Transcription Table
- `id`: Primary key
- `user_id`: User who made transcription
- `token_id`: API token used (if via API)
- `audio_filename`: Original audio file name
- `transcription_text`: Transcribed text
- `language`: Language code (ar-MA, ar, fr)
- `duration_seconds`: Audio duration
- `created_at`: Transcription date

## 🚧 Production Deployment

For production deployment:

1. **Use PostgreSQL** instead of SQLite
2. **Set secure secret key**: 
   ```python
   app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
   ```
3. **Use HTTPS** with SSL certificates
4. **Encrypt sensitive data** (API keys, tokens)
5. **Use Gunicorn** or uWSGI instead of Flask dev server
6. **Add rate limiting** and DDoS protection
7. **Implement logging** and monitoring

## 🛠️ Customization

### Add Custom Vocabulary
Edit the Google API integration to add domain-specific vocabulary:
```python
custom_words = [
    {"value": "صنداله", "boost": 20},
    {"value": "ستوك", "boost": 15}
]
```

### Change Languages
Modify the transcription languages in `app.py`:
```python
languages = [
    ("ar-MA", "Moroccan Arabic"),
    ("ar", "Standard Arabic"),
    ("fr-FR", "French"),
    ("en", "English")  # Add more languages
]
```

## 📞 Support

For issues or questions, please create an issue in the repository.

## 📄 License

This project is for educational purposes. Please ensure you comply with Google Cloud's terms of service when using their API.

---

**Built with ❤️ for Moroccan Darija transcription**