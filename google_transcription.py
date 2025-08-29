"""
Google Cloud Speech-to-Text API integration
Proper implementation with API key support
"""

import os
import io
from google.cloud import speech
from google.oauth2 import service_account
import speech_recognition as sr

class GoogleTranscriptionService:
    """Handle transcription with proper Google Cloud API"""
    
    def __init__(self, api_key=None, credentials_path=None):
        """
        Initialize with either API key or service account
        
        Args:
            api_key: Google Cloud API key (simpler but less secure)
            credentials_path: Path to service account JSON (more secure)
        """
        self.api_key = api_key or os.environ.get('GOOGLE_API_KEY')
        self.credentials_path = credentials_path or os.environ.get('GOOGLE_CREDENTIALS_PATH')
        self.client = None
        
        # Initialize based on available credentials
        if self.credentials_path and os.path.exists(self.credentials_path):
            # Use service account (recommended for production)
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path
            )
            self.client = speech.SpeechClient(credentials=credentials)
            self.use_cloud_api = True
        elif self.api_key:
            # Use API key (simpler setup)
            # Note: google-cloud-speech doesn't directly support API keys
            # We'll use the speech_recognition library with key
            self.use_cloud_api = False
        else:
            # Fallback to free tier (very limited)
            self.use_cloud_api = False
            print("WARNING: No Google API credentials found. Using free tier (limited to ~50 requests/day)")
    
    def transcribe_audio(self, audio_file_path, language="ar-MA", enable_punctuation=True):
        """
        Transcribe audio file using Google Speech API
        
        Args:
            audio_file_path: Path to audio file (WAV format preferred)
            language: Language code (ar-MA for Moroccan Arabic)
            enable_punctuation: Add punctuation to transcript
            
        Returns:
            dict: Transcription results with text and confidence
        """
        
        if self.use_cloud_api and self.client:
            # Use official Google Cloud Speech-to-Text API
            return self._transcribe_with_cloud_api(audio_file_path, language, enable_punctuation)
        else:
            # Use speech_recognition library (with or without API key)
            return self._transcribe_with_sr_library(audio_file_path, language)
    
    def _transcribe_with_cloud_api(self, audio_file_path, language, enable_punctuation):
        """Use official Google Cloud Speech-to-Text API"""
        
        # Read audio file
        with io.open(audio_file_path, "rb") as audio_file:
            content = audio_file.read()
        
        # Configure audio
        audio = speech.RecognitionAudio(content=content)
        
        # Configure recognition
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language,
            enable_automatic_punctuation=enable_punctuation,
            # Add custom vocabulary for Darija terms
            speech_contexts=[
                speech.SpeechContext(
                    phrases=[
                        "صباح الخير",
                        "كيداير",
                        "مزيان",
                        "شحال",
                        "باقي",
                        "صنداله",
                        "واش",
                        "فين",
                        "علاش",
                    ],
                    boost=20,  # Boost recognition of these phrases
                )
            ],
            # Alternative languages to try
            alternative_language_codes=["ar", "fr-FR"],
            max_alternatives=3,
        )
        
        # Perform transcription
        try:
            response = self.client.recognize(config=config, audio=audio)
            
            results = []
            for result in response.results:
                # Get best alternative
                best_alternative = result.alternatives[0]
                results.append({
                    'transcript': best_alternative.transcript,
                    'confidence': best_alternative.confidence,
                    'alternatives': [
                        {'transcript': alt.transcript, 'confidence': alt.confidence}
                        for alt in result.alternatives[1:]
                    ]
                })
            
            # Combine all results
            full_transcript = ' '.join([r['transcript'] for r in results])
            avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0
            
            return {
                'success': True,
                'transcript': full_transcript,
                'confidence': avg_confidence,
                'results': results,
                'api_used': 'google-cloud-speech'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'api_used': 'google-cloud-speech'
            }
    
    def _transcribe_with_sr_library(self, audio_file_path, language):
        """Use speech_recognition library (free or with API key)"""
        
        r = sr.Recognizer()
        
        try:
            with sr.AudioFile(audio_file_path) as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.record(source)
            
            # Use API key if available
            if self.api_key:
                # With API key (higher limits)
                text = r.recognize_google(
                    audio, 
                    key=self.api_key,
                    language=language
                )
                api_type = 'google-web-api-with-key'
            else:
                # Free tier (very limited)
                text = r.recognize_google(audio, language=language)
                api_type = 'google-web-api-free'
            
            return {
                'success': True,
                'transcript': text,
                'confidence': None,  # Not provided by web API
                'api_used': api_type
            }
            
        except sr.UnknownValueError:
            return {
                'success': False,
                'error': 'Could not understand audio',
                'api_used': 'speech_recognition'
            }
        except sr.RequestError as e:
            return {
                'success': False,
                'error': f'API request failed: {str(e)}',
                'api_used': 'speech_recognition'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'api_used': 'speech_recognition'
            }
    
    def get_usage_info(self):
        """Get information about API usage and limits"""
        
        if self.use_cloud_api:
            return {
                'api_type': 'Google Cloud Speech-to-Text',
                'pricing': '$0.006 per 15 seconds',
                'free_tier': '60 minutes/month free',
                'features': [
                    'High accuracy',
                    'Custom vocabulary',
                    'Multiple languages',
                    'Punctuation',
                    'Speaker diarization',
                    'Profanity filter'
                ]
            }
        elif self.api_key:
            return {
                'api_type': 'Google Web Speech API (with key)',
                'pricing': 'Free up to limits',
                'free_tier': '1000 requests/day',
                'features': [
                    'Basic transcription',
                    'Multiple languages'
                ]
            }
        else:
            return {
                'api_type': 'Google Web Speech API (free)',
                'pricing': 'Free',
                'free_tier': '~50 requests/day',
                'features': [
                    'Basic transcription',
                    'Very limited'
                ]
            }


# Usage tracking for your Zonemation tokens
class UsageTracker:
    """Track API usage per Zonemation token"""
    
    @staticmethod
    def calculate_cost(duration_seconds, api_type='cloud'):
        """
        Calculate cost based on duration and API type
        
        Google Cloud Speech pricing:
        - First 60 minutes/month: Free
        - After that: $0.006 per 15 seconds
        """
        if api_type != 'cloud':
            return 0  # Free tier
        
        # Assuming we track monthly usage elsewhere
        # This is simplified calculation
        billable_seconds = max(0, duration_seconds)
        cost = (billable_seconds / 15) * 0.006
        
        return {
            'duration_seconds': duration_seconds,
            'cost_usd': round(cost, 4),
            'cost_mad': round(cost * 10, 2),  # Approximate MAD conversion
        }