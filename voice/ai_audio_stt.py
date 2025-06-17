import os, sys
import queue
import yaml
import io
import numpy as np
from scipy.io import wavfile
from pydub import AudioSegment
import tempfile
import wave
import pywav
# add whisper
sys.path.append("/home/gangchen/Downloads/project/generative_model/whisper")
import whisper
from whisper.tokenizer import get_tokenizer

class StreamConfig:
    def __init__(self, version, language, stt_model, model_name, stream_rate, twilio_rate, stream_sid, settings):
        self.version = version
        self.language = language
        self.stt_model = stt_model
        self.model_name = model_name
        self.stream_rate = stream_rate
        self.twilio_rate = twilio_rate
        self.stream_sid = stream_sid
        self.settings = Settings(**settings)

    def update_stream_sid(self, new_value):
        self.stream_sid = new_value

class Settings:
        def __init__(self, debug, api_key):
            self.debug = debug
            self.api_key = api_key


def load_config(filepath):
    with open(filepath, 'r') as file:
        data = yaml.safe_load(file)
    return StreamConfig(**data)


class SpeechClientBridge:
    def __init__(self, stream_config, on_response):
        self.on_response = on_response
        self.queue = queue.Queue()
        self.stream_config = stream_config
        self.language = self.stream_config.language #"english" if language is None else language
        self.audio_model = whisper.load_model(self.stream_config.model_name) if self.stream_config.stt_model == "whisper" else None #("medium") #whisper.load_model("base.en")
        self.ended = False


    def start(self):

        audio_stream = self.generator()
        responses = []
        responses = self.transcribe_audio(audio_stream)
        self.process_responses_loop(responses)


    def terminate(self):
        self.ended = True

    def add_request(self, buffer):
        self.queue.put(bytes(buffer), block=False)

    def transcribe_audio(self, audio_stream):
        for content in audio_stream:
            responses = []
            print("Waiting for twilio caller...")
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = os.path.join(tmp, "mic.wav")
                wave_write = pywav.WavWrite(tmp_path, 1, 8000, 8, 7)  # 1 stands for mono channel, 8000 sample rate, 8 bit, 7 stands for MULAW encoding
                wave_write.write(content)
                wave_write.close()

                # audio_data, rate = convert_bytes_to_numpy(content)
                a2text = self.audio_model.transcribe(tmp_path, language=self.language, fp16=False)
                responses.append(a2text)
                if os.path.exists(tmp_path):
                    #os.remove(tmp_path)
                    print(f"remove the temp wav: {tmp_path}")
                yield responses

    def process_responses_loop(self, responses):
        for response in responses:
            self.on_response(response)

            if self.ended:
                break

    def generator(self):
        while not self.ended:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self.queue.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self.queue.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)



def convert_audio_bytes_to_numpy(audio_bytes, sample_rate=8000, sample_width=2):
    """
    Converts audio bytes to a numpy array.

    Args:
        audio_bytes: The audio bytes data.
        sample_rate: The sample rate of the audio data.
        sample_width: The sample width of the audio data in bytes.

    Returns:
        A numpy array representing the audio data, or None if an error occurs.
    """
    try:
        # Use io.BytesIO to treat the byte string as a file-like object
        byte_io = io.BytesIO(audio_bytes)
        
        # Use wave to read the audio data
        with wave.open(byte_io, 'rb') as wf:
            num_channels = wf.getnchannels()
            frame_rate = wf.getframerate()
            num_frames = wf.getnframes()
            
            # Read all frames
            audio_data = wf.readframes(num_frames)

        # Convert the byte data to a NumPy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # If there are multiple channels, reshape the array
        if num_channels > 1:
            audio_array = audio_array.reshape(-1, num_channels)

        return audio_array
    except Exception as e:
        print(f"Error converting audio bytes to numpy array: {e}")
        return None


def convert_bytes_to_numpy(audio_bytes, sample_rate=16000):
    """Converts audio bytes to a NumPy array."""
    try:
        # Attempt to read as WAV directly
        rate, data = wavfile.read(io.BytesIO(audio_bytes))
        return data.astype(np.float32) / np.iinfo(data.dtype).max, rate
    except Exception as e:
        # If WAV read fails, try converting from other formats using pydub
        try:
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
            audio_segment = audio_segment.set_frame_rate(sample_rate)
            
            # Export to a BytesIO object in WAV format
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            rate, data = wavfile.read(wav_buffer)
            return data.astype(np.float32) / np.iinfo(data.dtype).max, rate

        except Exception as e2:
             raise ValueError(f"Could not convert audio bytes to numpy array: {e2}") from e