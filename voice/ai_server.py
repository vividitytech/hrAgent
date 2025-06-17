import sys,os
import time
import base64
import json
import logging
from flask import Flask, request, Response, jsonify
from flask_sock import Sock, ConnectionClosed
import scipy.signal
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from twilio.rest import Client
#from gevent.pywsgi import WSGIServer

import numpy as np
import audioop
import scipy
import threading
import asyncio
from scipy.io.wavfile import write
from ai_audio_stt import SpeechClientBridge, load_config
from ai_assistant import AIChat

VITS_PATH = os.environ.get("VITS_PATH")
sys.path.append(VITS_PATH)
from inference import VITS
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#from gevent import monkey
#monkey.patch_all()

yaml_path = "stream_config.yaml"
stream_config = load_config(yaml_path)

processing_flag = False
lock = threading.Lock()

class TwilioAIAssistant:
    def __init__(self, remote_host: str, port: int,):
        self.app = Flask(__name__)
        self.sock = Sock(self.app)
        self.remote_host = remote_host
        self.port = port
        self.server_thread = threading.Thread(target=self._start)
        account_sid = os.environ["TWILIO_ACCOUNT_SID"]
        auth_token = os.environ["TWILIO_AUTH_TOKEN"]
        self.from_phone = os.environ["TWILIO_PHONE_NUMBER"]
        self.client = Client(account_sid, auth_token)

        self.hr = AIChat() # hr assistant 
        self.hr.set_system_content("you are hr assistant, and please answer any question at most 2-3 sentences. if you do not know, please reply you will check and answer later.")

        # text to speech 
        self.tts_client = VITS(os.path.join(VITS_PATH, "logs/pretrained_ljs.pth"), os.path.join(VITS_PATH,"configs/ljs_base.json"))

        # Twilio voice webhook
        @self.app.route("/incoming-voice", methods=['GET', 'POST'])
        def voice():
            """Handles incoming Twilio calls."""
            response = VoiceResponse()
            connect = Connect()
            #stream = Stream(url=f"wss://{request.host}/stream")  # Use request.host for dynamic URL
            stream = Stream(url=f"wss://{self.remote_host}/stream")
            connect.append(stream)
            response.append(connect)
            response.say("Please wait while I connect you to the AI assistant.")  # Initial message
            return str(response), 200, {'Content-Type': 'application/xml'}


        # WebSocket endpoint
        @self.sock.route("/stream")
        def stream(ws):
            try:
                self.handle_audio(ws)
            # except websockets.exceptions.ConnectionClosedError:
            #    logging.info("WebSocket connection closed")
            except ConnectionClosed:
                logging.info("WebSocket connection closed")
            except Exception as e:
                logging.error(f"WebSocket error: {e}")
            return "", 200


        @self.app.route('/call', methods=['POST'])
        def call():
            """Initiates a call to the specified number."""
            phone_number = request.form.get('phone_number')

            try:
                call = self.client.calls.create(
                    to=phone_number,
                    from_=self.from_phone,
                    url=f"https://{self.remote_host}/incoming-voice"  # Use your ngrok or deployed URL
                )
                return jsonify({"message": f"Calling {phone_number}... Call SID: {call.sid}"})
            except Exception as e:
                return jsonify({"error": str(e)})

    def start_call(self, to_phone: str, system_message: str, job_description: str):
        
        self.hr.set_system_content(system_message + "\n\n" + job_description)

        self.client.calls.create(
            url=f"https://{self.remote_host}/incoming-voice" ,
            to=to_phone,
            from_=self.from_phone,
        )

    def _start(self):
        logging.info("Starting Twilio + HR AI assistant Server")
        #WSGIServer(("0.0.0.0", self.port), self.app).serve_forever()
        self.app.run(host="0.0.0.0", port=self.port, debug=True, use_reloader=False)

    def start(self):
        self.server_thread.start()


    def handle_audio(self, ws):
        logging.info('Handling audio')  # Added logging
        stream_sid = None
        bridge = SpeechClientBridge(stream_config, lambda response: asyncio.run(self.on_transcription_response(response, ws)))
        t = threading.Thread(target=bridge.start)
        t.start()
        while True:
            message = ws.receive()

            if message is None:
                bridge.add_request(None)
                logging.info("No message received...")
                continue
            
            # Messages are a JSON encoded string
            data = json.loads(message)

            # Using the event type you can determine what type of message you are receiving
            if data['event'] == "connected":
                logging.info("Connected Message received: {}".format(message))
            elif data['event'] == "start":
                
                stream_sid = data['start']['streamSid']
                stream_config.update_stream_sid(stream_sid)
                logging.info("Start Message received: {}".format(message))

            elif data['event'] == "media":
                #logging.info("Media message: {}".format(message))
                payload = data['media']['payload']
                #logging.info("Payload is: {}".format(payload))
                audio_data = base64.b64decode(payload)
                # logging.info("That's {} bytes media data".format(len(audio_data)))

                # Split the audio data on silence
                #audio_chunks = whisper_handler.split_on_silence(audio_data)
                #logging.info('Split audio data into %d chunks', len(audio_chunks))  # Added logging

                # Transcribe each audio chunk
                #transcriptions = [whisper_handler.transcribe_audio(chunk) for chunk in audio_chunks]
                # asyncio.run(process_and_respond(ws, audio_data))
                bridge.add_request(audio_data)
                #logging.info('Transcribed audio chunks: %s', transcriptions)  # Added logging
            elif data['event'] == "closed":
                logging.info("Closed Message received: {}".format(message))
                break

    # ****************** AUDIO PROCESSING THREAD ******************
    async def on_transcription_response(self, response, ws):
        if not response:
            return

        transcription = response[0]["text"]
        if not transcription:
            return

        global processing_flag
        with lock:
            if processing_flag:
                print(f"Skipping data: {transcription}")
                return
            processing_flag = True


        #print(f"Processing data: {transcription}")
        current_sentence = transcription
        #print("Complete Sentence:", current_sentence)
        print("User question:", current_sentence)
        gpt_response = self.hr.chat(current_sentence)
        print("GPT Response:", gpt_response)
        audio_data = self.text_to_speech(gpt_response)
        self.send_static_audio(ws, audio_data)
        # time.sleep(int(len(gpt_response.split())/2)) # sleep the number of tokens
        # time.sleep(2)  # Suspend execution for 2 seconds
        await asyncio.sleep(int(len(gpt_response.split())/2))  # Pauses execution for 2 seconds
        
        with lock:
            processing_flag = False



    def text_to_speech(self, text):
        # Replace with your TTS logic (Twilio, Google Cloud TTS, etc.)
        # For Twilio TTS, you'd use the <Say> verb in TwiML.
        # For other TTS engines, you'd generate an audio file.
        audio_data = self.tts_client.infer(text, "cpu")
        # Placeholder - just return the text for now (using <Say>)

        print(f"TTS conversion complete, audio data length: {len(audio_data)}")
        save_locally = True
        if save_locally:
            rate = 22050
            write('tts_output.wav', stream_config.stream_rate, audio_data)
            print("TTS output saved locally as tts_output.mp3")

        return audio_data


    def send_static_audio(self, ws, audio_data=None):
        if stream_config.stream_sid is None:
            print("stream_sid is None, not ready for stream audio transfer")
            return
        try:

            if audio_data is not None:
                indata = scipy.signal.resample(audio_data, int(len(audio_data)*8000/22050))
                pcm_data = (indata * 32767).astype(np.int16).tobytes()
                # Convert to mu-law encoding
                mu_law_data = audioop.lin2ulaw(pcm_data, 2) # 2 = 16-bit samples

                audio_b64 = base64.b64encode(mu_law_data).decode('utf-8')
                message = json.dumps({
                    "event": "media",
                    "streamSid": stream_config.stream_sid,
                    "media": {
                        "payload": audio_b64
                    }
                })
                ws.send(message)
            else:
                # Load a static audio file (in PCM mu-law format)
                with open("tts_output.wav", "rb") as f:
                    audio_data = f.read()

                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                    message = json.dumps({
                        "event": "media",
                        "streamSid": stream_config.stream_sid,
                        "media": {
                            "payload": audio_b64
                        }
                    })
                    ws.send(message)
                    # sleep(0.1)  # Small delay between chunks

            print("Static audio sent successfully")
        except Exception as e:
            print(f"Error sending static audio: {e}")



if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    # REMOTE_HOST
    tws = TwilioAIAssistant(remote_host="cc3b-74-94-77-238.ngrok-free.app", port=8080,)
    # Point twilio voice webhook to https://abcdef.ngrok.app/audio/incoming-voice
    tws.start()