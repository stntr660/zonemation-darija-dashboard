#!/usr/bin/env python3
"""
Darija Transcription Dashboard
Simple dashboard with login, token management, and audio testing
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import secrets
import os
import datetime
import speech_recognition as sr
from functools import wraps
import json
from pydub import AudioSegment

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============== DATABASE MODELS ==============

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    google_api_key = db.Column(db.String(500))  # Encrypted in production
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    tokens = db.relationship('ApiToken', backref='owner', lazy=True)
    transcriptions = db.relationship('Transcription', backref='user', lazy=True)

class ApiToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_used = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    rate_limit = db.Column(db.Integer, default=100)  # requests per hour

class Transcription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token_id = db.Column(db.Integer, db.ForeignKey('api_token.id'))
    audio_filename = db.Column(db.String(255))
    transcription_text = db.Column(db.Text)
    language = db.Column(db.String(10), default='ar-MA')
    duration_seconds = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
# ============== AUTH HELPERS ==============

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-API-Token')
        
        if not token:
            return jsonify({'error': 'Token required'}), 401
        
        api_token = ApiToken.query.filter_by(token=token, is_active=True).first()
        
        if not api_token:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Update usage stats
        api_token.last_used = datetime.datetime.utcnow()
        api_token.usage_count += 1
        db.session.commit()
        
        return f(api_token, *args, **kwargs)
    
    return decorated

# ============== ROUTES ==============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

# Registration is disabled - admin only
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/dashboard'})
            
            return redirect(url_for('dashboard'))
        
        if request.is_json:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        flash('Invalid username or password', 'danger')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_tokens = ApiToken.query.filter_by(user_id=current_user.id).all()
    recent_transcriptions = Transcription.query.filter_by(user_id=current_user.id)\
                                              .order_by(Transcription.created_at.desc())\
                                              .limit(10).all()
    
    # Calculate usage stats
    total_transcriptions = len(current_user.transcriptions)
    total_duration = sum(t.duration_seconds or 0 for t in current_user.transcriptions)
    
    return render_template('dashboard.html',
                         tokens=user_tokens,
                         transcriptions=recent_transcriptions,
                         total_transcriptions=total_transcriptions,
                         total_duration=total_duration)

@app.route('/tokens')
@login_required
def tokens():
    user_tokens = ApiToken.query.filter_by(user_id=current_user.id).all()
    return render_template('tokens.html', tokens=user_tokens)

@app.route('/tokens/create', methods=['POST'])
@login_required
def create_token():
    data = request.get_json()
    name = data.get('name', 'Unnamed Token')
    
    # Generate unique token
    token_value = secrets.token_urlsafe(32)
    
    # Create token record
    api_token = ApiToken(
        token=token_value,
        name=name,
        user_id=current_user.id
    )
    db.session.add(api_token)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'token': {
            'id': api_token.id,
            'token': api_token.token,
            'name': api_token.name,
            'created_at': api_token.created_at.isoformat()
        }
    })

@app.route('/tokens/<int:token_id>/revoke', methods=['POST'])
@login_required
def revoke_token(token_id):
    api_token = ApiToken.query.filter_by(id=token_id, user_id=current_user.id).first()
    
    if not api_token:
        return jsonify({'error': 'Token not found'}), 404
    
    api_token.is_active = False
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/settings/google-api', methods=['POST'])
@login_required
def update_google_api():
    data = request.get_json()
    api_key = data.get('api_key')
    
    # In production, encrypt this!
    current_user.google_api_key = api_key
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Google API key updated'})

@app.route('/test')
@login_required
def test_page():
    return render_template('test.html')

@app.route('/api/docs')
def api_docs():
    return render_template('api_docs.html')

@app.route('/transcribe', methods=['POST'])
@login_required
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400
    
    file = request.files['audio']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Convert to WAV if needed
    wav_filepath = None
    
    try:
        # Check if file needs conversion
        if not filename.lower().endswith('.wav'):
            # Convert to WAV using pydub
            from pydub import AudioSegment
            
            # Load audio file
            if filename.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(filepath)
            elif filename.lower().endswith('.m4a'):
                audio = AudioSegment.from_file(filepath, format='m4a')
            elif filename.lower().endswith('.ogg'):
                audio = AudioSegment.from_ogg(filepath)
            elif filename.lower().endswith('.flac'):
                audio = AudioSegment.from_file(filepath, format='flac')
            else:
                audio = AudioSegment.from_file(filepath)
            
            # Convert to WAV
            wav_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_' + filename.rsplit('.', 1)[0] + '.wav')
            audio = audio.set_frame_rate(16000).set_channels(1)  # 16kHz mono for best compatibility
            audio.export(wav_filepath, format='wav')
            
            # Use converted file
            process_filepath = wav_filepath
        else:
            process_filepath = filepath
        
        # Use Google Speech Recognition
        r = sr.Recognizer()
        
        with sr.AudioFile(process_filepath) as source:
            # Adjust for ambient noise
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.record(source)
        
        # Try multiple languages
        results = {}
        
        # Moroccan Arabic
        try:
            text = r.recognize_google(audio, language="ar-MA")
            results['darija'] = text
        except sr.UnknownValueError:
            results['darija'] = "Could not understand audio"
        except sr.RequestError as e:
            results['darija'] = f"API error: {e}"
        except:
            pass
        
        # Standard Arabic
        try:
            text = r.recognize_google(audio, language="ar")
            results['arabic'] = text
        except:
            pass
        
        # French
        try:
            text = r.recognize_google(audio, language="fr-FR")
            results['french'] = text
        except:
            pass
        
        # Auto-detect if no results
        if not any(results.values()):
            try:
                text = r.recognize_google(audio)
                results['auto'] = text
            except:
                pass
        
        # Save transcription record
        best_result = results.get('darija') or results.get('arabic') or results.get('french') or results.get('auto', '')
        
        if best_result and not best_result.startswith("Could not") and not best_result.startswith("API error"):
            transcription = Transcription(
                user_id=current_user.id,
                audio_filename=filename,
                transcription_text=best_result,
                language='ar-MA'
            )
            db.session.add(transcription)
            db.session.commit()
            transcription_id = transcription.id
        else:
            transcription_id = None
        
        # Clean up
        os.remove(filepath)
        if wav_filepath and os.path.exists(wav_filepath):
            os.remove(wav_filepath)
        
        # Check if we got any results
        if not results or not any(v for v in results.values() if v and not v.startswith("Could not")):
            return jsonify({
                'error': 'Could not transcribe audio. Please ensure the audio is clear and contains speech.'
            }), 400
        
        return jsonify({
            'success': True,
            'results': results,
            'best': best_result,
            'transcription_id': transcription_id
        })
        
    except Exception as e:
        # Clean up files on error
        if os.path.exists(filepath):
            os.remove(filepath)
        if wav_filepath and os.path.exists(wav_filepath):
            os.remove(wav_filepath)
        
        # Provide helpful error message
        error_msg = str(e)
        if "AudioSegment" in error_msg:
            error_msg = "Audio format not supported. Please use MP3, WAV, M4A, or OGG format."
        elif "ffmpeg" in error_msg.lower():
            error_msg = "FFmpeg not installed. Please install FFmpeg to process this audio format."
        
        return jsonify({'error': error_msg}), 500

# ============== API ENDPOINTS ==============

@app.route('/api/v1/transcribe', methods=['POST'])
@token_required
def api_transcribe(api_token):
    """
    API endpoint for transcription with token authentication
    """
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
    
    file = request.files['audio']
    
    # Save and process
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"api_{filename}")
    file.save(filepath)
    
    wav_filepath = None
    
    try:
        # Convert to WAV if needed
        if not filename.lower().endswith('.wav'):
            # Load and convert audio
            if filename.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(filepath)
            elif filename.lower().endswith('.m4a'):
                audio = AudioSegment.from_file(filepath, format='m4a')
            elif filename.lower().endswith('.ogg'):
                audio = AudioSegment.from_ogg(filepath)
            else:
                audio = AudioSegment.from_file(filepath)
            
            # Convert to WAV
            wav_filepath = filepath.rsplit('.', 1)[0] + '_converted.wav'
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(wav_filepath, format='wav')
            process_filepath = wav_filepath
        else:
            process_filepath = filepath
        
        r = sr.Recognizer()
        
        with sr.AudioFile(process_filepath) as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.record(source)
        
        # Transcribe
        text = r.recognize_google(audio, language="ar-MA")
        
        # Save record
        transcription = Transcription(
            user_id=api_token.user_id,
            token_id=api_token.id,
            audio_filename=filename,
            transcription_text=text,
            language='ar-MA'
        )
        db.session.add(transcription)
        db.session.commit()
        
        # Clean up
        os.remove(filepath)
        if wav_filepath and os.path.exists(wav_filepath):
            os.remove(wav_filepath)
        
        return jsonify({
            'success': True,
            'transcription': text,
            'id': transcription.id
        })
        
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        if wav_filepath and os.path.exists(wav_filepath):
            os.remove(wav_filepath)
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/tokens', methods=['GET'])
@login_required
def api_list_tokens():
    """List all tokens for current user"""
    tokens = ApiToken.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'tokens': [{
            'id': t.id,
            'name': t.name,
            'token': t.token[:8] + '...',  # Show only first 8 chars
            'created_at': t.created_at.isoformat(),
            'last_used': t.last_used.isoformat() if t.last_used else None,
            'usage_count': t.usage_count,
            'is_active': t.is_active
        } for t in tokens]
    })

# ============== INITIALIZATION ==============

def init_db():
    """Initialize database with tables"""
    with app.app_context():
        db.create_all()
        
        # Create admin user if none exists
        if not User.query.first():
            admin_user = User(
                username='admin',
                email='admin@darija-asr.com',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created: username='admin', password='admin123'")
            print("⚠️  IMPORTANT: Change the admin password after first login!")

if __name__ == '__main__':
    init_db()
    print("\n" + "="*60)
    print("🚀 Darija Transcription Dashboard - Admin Only")
    print("="*60)
    print("📱 Access at: http://localhost:5001")
    print("🔐 Admin login: admin / admin123")
    print("⚠️  Change password after first login!")
    print("="*60 + "\n")
    app.run(debug=True, port=5001)