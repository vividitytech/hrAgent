from typing import List, Optional
import os, sys
from abc import ABC, abstractmethod
import random
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types
# Gemini API key
GOOGLE_GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")

class AIChat(ABC):
    def __init__(self, client=None, config=None):
        # default parameters - can be overrided using config
        self.temperature = 0.7

        if config is not None and "temperature" in config:
            self.temperature = config["temperature"]

        if config is not None and "api_type" in config:
            raise Exception(
                "Passing api_type is now deprecated. Please pass an OpenAI client instead."
            )

        # set the model list to use
        self.model_list = ["gemini-2.0-flash"]
        self.model_id =random.randint(0, len(self.model_list) - 1)
        self.system_message = ""
        self.messages = [
            #{"role": "system", "content": "You are a coding tutor bot to help user write and optimize python code."},
        ]

        if client is not None:
            self.client = client
            return

        if config is None and client is None:
            self.client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))
            return

        if "api_key" in config:
            self.client = genai.Client(api_key=config["api_key"])

    
    def set_system_content(self, message):
        self.messages = []
        self.system_message = message
    

    def chat(self, message):

        chat = self.client.chats.create(
            model=self.model_list[self.model_id],
            config=types.GenerateContentConfig(
                system_instruction=self.system_message,
                temperature=self.temperature,

            ),

            history = self.messages,
        )

        response = chat.send_message(message)
        assistant_reply = ""
        # Find the first response from the chatbot that has text in it (some responses may not have text)
        if hasattr(response, 'text'):
            assistant_reply = response.text

        self.messages.append(types.UserContent(message))
        self.messages.append(types.ModelContent(assistant_reply))
        return assistant_reply