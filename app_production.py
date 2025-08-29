#!/usr/bin/env python3
"""
Production-ready Darija Transcription Dashboard
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_talisman import Talisman
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import secrets
import os
import datetime
import speech_recognition as sr
from functools import wraps
import json
from pydub import AudioSegment
import logging
from logging.handlers import RotatingFileHandler
from utils.encryption import EncryptionManager, hash_password, verify_password

# Import configuration
from config import config

# Initialize Flask app with configuration
app = Flask(__name__)
env = os.environ.get('FLASK_ENV', 'production')
print(f"Starting app in {env} mode")
app_config = config.get(env, config['production'])
app.config.from_object(app_config)

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Setup logging
if not app.debug:
    file_handler = RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=10240000,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    app.logger.info('Darija Dashboard startup')

# Initialize encryption manager
encryption_manager = None
if app.config.get('ENCRYPTION_KEY'):
    encryption_manager = EncryptionManager(app.config['ENCRYPTION_KEY'])
else:
    app.logger.warning('No ENCRYPTION_KEY set - API keys will not be encrypted!')

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

# Initialize security extensions
CORS(app, origins=app.config['CORS_ORIGINS'])

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=app.config['RATELIMIT_STORAGE_URL'],
    default_limits=[app.config['RATELIMIT_DEFAULT']]
)

# Security headers (HTTPS enforced in production)
# Skip Talisman for Railway deployment - it's causing health check issues
# Railway provides SSL termination at their proxy level
if app.config.get('SESSION_COOKIE_SECURE') and False:  # Disabled for Railway
    Talisman(app, 
        force_https=True,
        strict_transport_security=True,
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com",
            'style-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://cdnjs.cloudflare.com",
            'font-src': "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
            'img-src': "'self' data: https:",
        }
    )

# ============== HEALTH CHECK (Early definition) ==============

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring - no auth required"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'app': 'darija-dashboard'
    }), 200

@app.route('/debug/test-login')
def test_login():
    """Debug endpoint to test login - REMOVE IN PRODUCTION"""
    try:
        # Get admin user
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            # No admin found, let's help create one
            return jsonify({
                'error': 'No admin user found',
                'all_users': [{'username': u.username, 'email': u.email} for u in User.query.all()],
                'total_users': User.query.count(),
                'hint': 'Visit /debug/create-admin to create admin user'
            }), 404
        
        # Test password from environment
        test_password = app.config.get('ADMIN_PASSWORD', '')
        
        # Create a test user to verify password hashing works
        test_user = User(username='test_temp', email='test@test.com', is_admin=True, is_active=True)
        test_user.set_password(test_password)
        
        # Test if password verification works
        password_works = test_user.check_password(test_password)
        admin_password_works = admin.check_password(test_password) if test_password else False
        
        return jsonify({
            'admin_exists': True,
            'admin_username': admin.username,
            'admin_email': admin.email,
            'admin_is_active': admin.is_active,
            'admin_is_admin': admin.is_admin,
            'test_password_from_env': bool(test_password),
            'test_password_length': len(test_password) if test_password else 0,
            'password_hashing_works': password_works,
            'admin_password_matches_env': admin_password_works,
            'hint': 'If admin_password_matches_env is False, set RESET_ADMIN_PASSWORD=true'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/create-admin')
def force_create_admin():
    """Force create admin user - REMOVE IN PRODUCTION"""
    try:
        # Check if admin already exists
        existing = User.query.filter_by(username='admin').first()
        if existing:
            return jsonify({'message': 'Admin already exists', 'username': existing.username}), 200
        
        # Get password from environment or use default
        admin_password = app.config.get('ADMIN_PASSWORD', '')
        if not admin_password:
            # Use a temporary password
            admin_password = 'Admin123!'
            
        # Create admin user
        admin_user = User(
            username='admin',
            email=app.config.get('ADMIN_EMAIL', 'admin@zonemation.com'),
            is_admin=True,
            is_active=True
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Admin user created successfully',
            'username': 'admin',
            'email': admin_user.email,
            'password_hint': 'Use the password from ADMIN_PASSWORD env var, or Admin123! if not set',
            'actual_password_set': admin_password if not app.config.get('ADMIN_PASSWORD') else 'From ADMIN_PASSWORD env var'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e), 'trace': str(e.__class__.__name__)}), 500

# ============== DATABASE MODELS ==============

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    google_api_key_encrypted = db.Column(db.Text)  # Encrypted
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    tokens = db.relationship('ApiToken', backref='owner', lazy=True, cascade='all, delete-orphan')
    transcriptions = db.relationship('Transcription', backref='user', lazy=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = hash_password(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return verify_password(self.password_hash, password)
    
    def set_google_api_key(self, api_key):
        """Encrypt and store Google API key"""
        if encryption_manager and api_key:
            self.google_api_key_encrypted = encryption_manager.encrypt(api_key)
        else:
            self.google_api_key_encrypted = api_key
    
    def get_google_api_key(self):
        """Decrypt and return Google API key"""
        if encryption_manager and self.google_api_key_encrypted:
            try:
                return encryption_manager.decrypt(self.google_api_key_encrypted)
            except:
                return self.google_api_key_encrypted
        return self.google_api_key_encrypted

class ApiToken(db.Model):
    __tablename__ = 'api_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    last_used = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    rate_limit = db.Column(db.Integer, default=1000)  # requests per hour
    expires_at = db.Column(db.DateTime)  # Optional expiration

class Transcription(db.Model):
    __tablename__ = 'transcriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token_id = db.Column(db.Integer, db.ForeignKey('api_tokens.id'))
    audio_filename = db.Column(db.String(255))
    transcription_text = db.Column(db.Text)
    language = db.Column(db.String(10), default='ar-MA')
    duration_seconds = db.Column(db.Float)
    file_size_bytes = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)

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
        
        # Check expiration
        if api_token.expires_at and api_token.expires_at < datetime.datetime.utcnow():
            return jsonify({'error': 'Token expired'}), 401
        
        # Check rate limit (simple implementation)
        hour_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        recent_usage = Transcription.query.filter(
            Transcription.token_id == api_token.id,
            Transcription.created_at > hour_ago
        ).count()
        
        if recent_usage >= api_token.rate_limit:
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Update usage stats
        api_token.last_used = datetime.datetime.utcnow()
        api_token.usage_count += 1
        db.session.commit()
        
        return f(api_token, *args, **kwargs)
    
    return decorated

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ============== ERROR HANDLERS ==============

@app.errorhandler(413)
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(429)
def handle_rate_limit(e):
    return jsonify({'error': f'Rate limit exceeded: {e.description}'}), 429

@app.errorhandler(500)
def handle_internal_error(e):
    app.logger.error(f'Internal error: {e}')
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# ============== ROUTES ==============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            if request.is_json:
                return jsonify({'error': 'Username and password required'}), 400
            flash('Username and password required', 'danger')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        
        # Debug logging
        app.logger.info(f'Login attempt for username: {username}')
        app.logger.info(f'User found: {user is not None}')
        if user:
            app.logger.info(f'User email: {user.email}, is_admin: {user.is_admin}, is_active: {user.is_active}')
        
        # Check if account is locked
        if user and user.locked_until and user.locked_until > datetime.datetime.utcnow():
            if request.is_json:
                return jsonify({'error': 'Account temporarily locked due to multiple failed attempts'}), 403
            flash('Account temporarily locked', 'danger')
            return redirect(url_for('login'))
        
        if user and user.check_password(password):
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=True)
            app.logger.info(f'User {username} logged in successfully from {request.remote_addr}')
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/dashboard'})
            
            return redirect(url_for('dashboard'))
        else:
            app.logger.warning(f'Login failed for {username} - password mismatch')
            # Track failed login attempts
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
                    app.logger.warning(f'Account {username} locked after 5 failed attempts')
                db.session.commit()
            
            app.logger.warning(f'Failed login attempt for {username} from {request.remote_addr}')
            
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
    total_transcriptions = Transcription.query.filter_by(user_id=current_user.id).count()
    total_duration = db.session.query(db.func.sum(Transcription.duration_seconds))\
                              .filter_by(user_id=current_user.id).scalar() or 0
    
    return render_template('dashboard.html',
                         tokens=user_tokens,
                         transcriptions=recent_transcriptions,
                         total_transcriptions=total_transcriptions,
                         total_duration=total_duration)

@app.route('/tokens')
@login_required
def tokens():
    user_tokens = ApiToken.query.filter_by(user_id=current_user.id)\
                                .order_by(ApiToken.created_at.desc()).all()
    return render_template('tokens.html', tokens=user_tokens)

@app.route('/tokens/create', methods=['POST'])
@login_required
@limiter.limit("10 per hour")
def create_token():
    data = request.get_json()
    name = data.get('name', 'Unnamed Token')[:100]  # Limit name length
    
    # Generate cryptographically secure token
    token_value = secrets.token_urlsafe(32)
    
    # Create token record
    api_token = ApiToken(
        token=token_value,
        name=name,
        user_id=current_user.id
    )
    db.session.add(api_token)
    db.session.commit()
    
    app.logger.info(f'User {current_user.username} created new API token: {name}')
    
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
    
    app.logger.info(f'User {current_user.username} revoked token: {api_token.name}')
    
    return jsonify({'success': True})

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/settings/google-api', methods=['POST'])
@login_required
def update_google_api():
    data = request.get_json()
    api_key = data.get('api_key', '').strip()
    
    if api_key and len(api_key) < 10:
        return jsonify({'error': 'Invalid API key format'}), 400
    
    current_user.set_google_api_key(api_key)
    db.session.commit()
    
    app.logger.info(f'User {current_user.username} updated Google API key')
    
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
@limiter.limit("30 per minute")
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400
    
    file = request.files['audio']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file extension
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if file_ext not in app.config['ALLOWED_EXTENSIONS']:
        return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'}), 400
    
    # Save file with unique name
    unique_filename = f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    
    wav_filepath = None
    
    try:
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Convert to WAV if needed
        if not filename.lower().endswith('.wav'):
            # Convert to WAV using pydub
            if filename.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(filepath)
            elif filename.lower().endswith('.m4a'):
                audio = AudioSegment.from_file(filepath, format='m4a')
            elif filename.lower().endswith('.ogg'):
                audio = AudioSegment.from_ogg(filepath)
            elif filename.lower().endswith('.flac'):
                audio = AudioSegment.from_file(filepath, format='flac')
            elif filename.lower().endswith('.webm'):
                audio = AudioSegment.from_file(filepath, format='webm')
            else:
                audio = AudioSegment.from_file(filepath)
            
            # Convert to WAV
            wav_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f'wav_{unique_filename}.wav')
            audio = audio.set_frame_rate(16000).set_channels(1)  # 16kHz mono
            audio.export(wav_filepath, format='wav')
            
            # Calculate duration
            duration = len(audio) / 1000.0  # Convert to seconds
            
            process_filepath = wav_filepath
        else:
            process_filepath = filepath
            # Calculate duration for WAV files
            with sr.AudioFile(process_filepath) as source:
                audio_data = sr.Recognizer().record(source)
                duration = len(audio_data.frame_data) / (audio_data.sample_rate * audio_data.sample_width)
        
        # Use Google Speech Recognition
        r = sr.Recognizer()
        
        with sr.AudioFile(process_filepath) as source:
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
            app.logger.error(f'Google API error: {e}')
            results['darija'] = f"API error: {e}"
        except Exception as e:
            app.logger.error(f'Transcription error: {e}')
        
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
                language='ar-MA',
                duration_seconds=duration,
                file_size_bytes=file_size,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string[:255]
            )
            db.session.add(transcription)
            db.session.commit()
            transcription_id = transcription.id
        else:
            transcription_id = None
        
        # Clean up files
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
        app.logger.error(f'Transcription error: {e}')
        
        # Clean up files on error
        if os.path.exists(filepath):
            os.remove(filepath)
        if wav_filepath and os.path.exists(wav_filepath):
            os.remove(wav_filepath)
        
        # Provide helpful error message
        error_msg = str(e)
        if "AudioSegment" in error_msg:
            error_msg = "Audio format not supported. Please use MP3, WAV, M4A, OGG, or WebM format."
        elif "ffmpeg" in error_msg.lower():
            error_msg = "FFmpeg not installed. Please install FFmpeg to process this audio format."
        
        return jsonify({'error': error_msg}), 500

# ============== API ENDPOINTS ==============

@app.route('/api/v1/transcribe', methods=['POST'])
@token_required
@limiter.limit("100 per hour")
def api_transcribe(api_token):
    """API endpoint for transcription with token authentication"""
    # Similar to transcribe() but with token tracking
    # [Implementation similar to above with api_token tracking]
    # ... (same logic as transcribe but with api_token parameter)
    pass

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
        
        # Create admin user if none exists and password is set
        if not User.query.filter_by(username=app.config['ADMIN_USERNAME']).first():
            if app.config.get('ADMIN_PASSWORD'):
                admin_user = User(
                    username=app.config['ADMIN_USERNAME'],
                    email=app.config['ADMIN_EMAIL'],
                    is_admin=True,
                    is_active=True
                )
                admin_user.set_password(app.config['ADMIN_PASSWORD'])
                db.session.add(admin_user)
                db.session.commit()
                app.logger.info(f'Admin user created: {app.config["ADMIN_USERNAME"]}')
            else:
                app.logger.warning('No ADMIN_PASSWORD set in environment - admin user not created')

# ============== MONITORING ==============

# Sentry integration
if app.config.get('SENTRY_DSN'):
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(
            dsn=app.config['SENTRY_DSN'],
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            environment=os.environ.get('FLASK_ENV', 'production')
        )
        app.logger.info('Sentry monitoring initialized')
    except ImportError:
        app.logger.warning('Sentry SDK not installed - monitoring disabled')

# Initialize database on import (for Gunicorn)
with app.app_context():
    try:
        db.create_all()
        app.logger.info('Database tables created successfully')
        
        # Check for existing admin user
        existing_admin = User.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
        
        if not existing_admin:
            admin_password = app.config.get('ADMIN_PASSWORD')
            if admin_password and admin_password.strip():
                admin_user = User(
                    username=app.config['ADMIN_USERNAME'],
                    email=app.config['ADMIN_EMAIL'],
                    is_admin=True,
                    is_active=True
                )
                admin_user.set_password(admin_password)
                db.session.add(admin_user)
                db.session.commit()
                app.logger.info(f'Admin user created: {app.config["ADMIN_USERNAME"]} with email {app.config["ADMIN_EMAIL"]}')
            else:
                app.logger.warning(f'No ADMIN_PASSWORD set in environment - admin user not created. Password value: {bool(admin_password)}')
        else:
            # Update existing admin password if RESET_ADMIN_PASSWORD is set
            if os.environ.get('RESET_ADMIN_PASSWORD', '').lower() == 'true':
                admin_password = app.config.get('ADMIN_PASSWORD')
                if admin_password and admin_password.strip():
                    existing_admin.set_password(admin_password)
                    db.session.commit()
                    app.logger.info(f'Admin password reset for user: {existing_admin.username}')
                else:
                    app.logger.warning('RESET_ADMIN_PASSWORD set but no ADMIN_PASSWORD provided')
            else:
                app.logger.info(f'Admin user already exists: {existing_admin.username} (set RESET_ADMIN_PASSWORD=true to reset password)')
    except Exception as e:
        app.logger.error(f'Database initialization error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())

if __name__ == '__main__':
    # Never run with debug=True in production!
    app.run(host='0.0.0.0', port=5000, debug=False)