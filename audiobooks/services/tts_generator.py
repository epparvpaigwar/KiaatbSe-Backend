"""
Text-to-Speech Generation Service
Uses Microsoft Edge TTS for natural Hindi audio generation
"""
import edge_tts
import asyncio
import logging
import os
import subprocess

# pydub is not compatible with Python 3.13, using alternative method for audio info
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PYDUB_AVAILABLE = False

logger = logging.getLogger(__name__)


class TTSGenerator:
    """
    Service class for generating audio from text using Edge TTS
    """

    # Voice options for different languages
    VOICE_OPTIONS = {
        'hindi': {
            'female': 'hi-IN-SwaraNeural',  # Natural, expressive female voice
            'male': 'hi-IN-MadhurNeural'    # Natural, expressive male voice
        },
        'english': {
            'female': 'en-IN-NeerjaNeural',
            'male': 'en-IN-PrabhatNeural'
        },
        'urdu': {
            'female': 'ur-PK-UzmaNeural',
            'male': 'ur-PK-AsadNeural'
        },
        'bengali': {
            'female': 'bn-IN-TanishaaNeural',
            'male': 'bn-IN-BashkarNeural'
        },
        'tamil': {
            'female': 'ta-IN-PallaviNeural',
            'male': 'ta-IN-ValluvarNeural'
        },
        'telugu': {
            'female': 'te-IN-ShrutiNeural',
            'male': 'te-IN-MohanNeural'
        },
        'marathi': {
            'female': 'mr-IN-AarohiNeural',
            'male': 'mr-IN-ManoharNeural'
        },
        'gujarati': {
            'female': 'gu-IN-DhwaniNeural',
            'male': 'gu-IN-NiranjanNeural'
        }
    }

    @staticmethod
    def get_voice(language='hindi', gender='female'):
        """
        Get voice ID for specified language and gender

        Args:
            language: Language code (hindi, english, etc.)
            gender: 'male' or 'female'

        Returns:
            str: Voice ID
        """
        language = language.lower()
        gender = gender.lower()

        if language in TTSGenerator.VOICE_OPTIONS:
            return TTSGenerator.VOICE_OPTIONS[language].get(
                gender,
                TTSGenerator.VOICE_OPTIONS[language]['female']
            )

        # Default to Hindi female if language not found
        return TTSGenerator.VOICE_OPTIONS['hindi']['female']

    @staticmethod
    async def generate_audio_async(text, output_path, language='hindi', gender='female', rate='+0%', volume='+0%'):
        """
        Generate audio from text asynchronously

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            language: Language code
            gender: Voice gender
            rate: Speech rate (e.g., '+0%', '+10%', '-10%')
            volume: Volume level (e.g., '+0%', '+10%', '-10%')

        Returns:
            dict: {
                'success': bool,
                'output_path': str,
                'duration': int (seconds),
                'error': str (if any)
            }
        """
        try:
            # Check if text is empty
            if not text or text.strip() == "":
                logger.warning("Empty text provided for TTS generation")
                return {
                    'success': False,
                    'output_path': None,
                    'duration': 0,
                    'error': 'No text content to convert'
                }

            # Get appropriate voice
            voice = TTSGenerator.get_voice(language, gender)

            logger.info(f"Generating audio with voice: {voice}")

            # Create TTS communication object
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                volume=volume
            )

            # Generate and save audio
            await communicate.save(output_path)

            # Get audio duration
            duration = TTSGenerator._get_audio_duration(output_path)

            logger.info(f"Audio generated successfully: {output_path} ({duration}s)")

            return {
                'success': True,
                'output_path': output_path,
                'duration': duration,
                'error': None
            }

        except Exception as e:
            logger.error(f"TTS generation failed: {str(e)}")
            return {
                'success': False,
                'output_path': None,
                'duration': 0,
                'error': str(e)
            }

    @staticmethod
    def generate_audio(text, output_path, language='hindi', gender='female', rate='+0%', volume='+0%'):
        """
        Synchronous wrapper for audio generation

        Args:
            Same as generate_audio_async

        Returns:
            dict: Same as generate_audio_async
        """
        return asyncio.run(
            TTSGenerator.generate_audio_async(
                text, output_path, language, gender, rate, volume
            )
        )

    @staticmethod
    def _get_audio_duration(audio_path):
        """
        Get duration of audio file in seconds

        Args:
            audio_path: Path to audio file

        Returns:
            int: Duration in seconds
        """
        try:
            # Try pydub first if available
            if PYDUB_AVAILABLE:
                audio = AudioSegment.from_file(audio_path)
                return int(audio.duration_seconds)

            # Fallback to ffprobe (works on all Python versions)
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(float(result.stdout.strip()))

            # If ffprobe not available, estimate from file size (rough approximation)
            # MP3 bitrate ~128kbps = 16KB/s, so duration ~= file_size / 16000
            file_size = os.path.getsize(audio_path)
            estimated_duration = max(1, file_size // 16000)
            logger.warning(f"Using estimated duration: {estimated_duration}s")
            return estimated_duration

        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return 0

    @staticmethod
    async def list_available_voices():
        """
        List all available voices from Edge TTS

        Returns:
            list: Available voices
        """
        try:
            voices = await edge_tts.list_voices()
            return voices
        except Exception as e:
            logger.error(f"Error listing voices: {str(e)}")
            return []

    @staticmethod
    def get_supported_languages():
        """
        Get list of supported languages

        Returns:
            list: Supported language codes
        """
        return list(TTSGenerator.VOICE_OPTIONS.keys())

    @staticmethod
    async def generate_with_emotions_async(text, output_path, language='hindi', gender='female', emotion='neutral'):
        """
        Generate audio with emotional expression using SSML

        Args:
            text: Text to convert
            output_path: Output file path
            language: Language code
            gender: Voice gender
            emotion: Emotion type (happy, sad, excited, calm, neutral)

        Returns:
            dict: Generation result
        """
        # SSML mapping for emotions
        emotion_ssml = {
            'happy': '<prosody rate="fast" pitch="+5%">{}</prosody>',
            'sad': '<prosody rate="slow" pitch="-5%">{}</prosody>',
            'excited': '<prosody rate="fast" pitch="+10%" volume="+5%">{}</prosody>',
            'calm': '<prosody rate="slow" pitch="-2%">{}</prosody>',
            'neutral': '{}'
        }

        # Wrap text in SSML if emotion specified
        if emotion in emotion_ssml:
            ssml_text = f'<speak>{emotion_ssml[emotion].format(text)}</speak>'
        else:
            ssml_text = text

        return await TTSGenerator.generate_audio_async(
            ssml_text, output_path, language, gender
        )

    @staticmethod
    def test_tts(text="यह एक परीक्षण है", language='hindi'):
        """
        Test TTS generation with sample text

        Args:
            text: Test text
            language: Language to test

        Returns:
            bool: Success status
        """
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)

        try:
            result = TTSGenerator.generate_audio(
                text=text,
                output_path=temp_file.name,
                language=language
            )

            if result['success']:
                logger.info(f"TTS test successful! Duration: {result['duration']}s")
                return True
            else:
                logger.error(f"TTS test failed: {result['error']}")
                return False

        except Exception as e:
            logger.error(f"TTS test exception: {str(e)}")
            return False
        finally:
            # Clean up temp file
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
