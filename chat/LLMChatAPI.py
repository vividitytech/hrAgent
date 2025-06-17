import sys
import os
from openai import OpenAI
#import google.generativeai as genai
from google import genai
from google.genai import types

def generate(input):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.0-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=input)#"""INSERT_INPUT_HERE"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text="""You are good at named entity recognition task and you need to output entities with types and also start index and end index in json. 
For example, jeff hinton is a professor at university of toronto, he is known for deep leraning, and he is good at python and c++. Then, jeff hinton is a person, You need to label as PER. 
professor is job title, label as TITLE, university of toronto is organization, label as ORG, deep learning is CONCEPT, and both python and c++ are TOOL.

Another example: iphone is a product by Apple in California, you can develop ios app using its xcode. Iphone is PROD, California is LOC (or LOCATION), Apple is ORG, and xcode is TOOL. You should be able to process in batch too and output as json."""),
        ],
    )

    res = ""
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")
        res = res + chunk.text
    return res

class LLMChat:
    """
    A general class for chatting with various LLMs (OpenAI, Gemini, etc.) with system messages.
    Allows overriding system message in a new chat session.
    """

    def __init__(self, model_name, provider="openai", system_message=None, **kwargs):
        """
        Initializes the LLMChat instance.

        Args:
            model_name (str): The name of the LLM model to use (e.g., "gpt-3.5-turbo", "gemini-pro").
            provider (str): The provider of the LLM ("openai", "gemini"). Defaults to "openai".
            system_message (str, optional): A system message to set the context or role of the LLM.
                                            Defaults to None.
            **kwargs: Additional keyword arguments that are specific to the provider.
                       For example, for OpenAI, you might pass `temperature=0.7`.

        Raises:
            ValueError: If the provider is not supported or required API keys are missing.
        """

        self.model_name = model_name
        self.provider = provider.lower()
        self.default_system_message = system_message  # Store as default
        self.api_key = kwargs.get("api_key")  # Get the API key from kwargs
        self.kwargs = kwargs
        self.current_system_message = system_message # Set the initial system message
        if kwargs.get("temperature"):
            self.temperature = kwargs.get("temperature")
        else:
            self.temperature = 0.7
        if self.provider ==  "openai":
            self.client = OpenAI(api_key=self.api_key or os.environ.get("OPENAI_API_KEY"))

        elif self.provider == "gemini":
            self.client = genai.Client(
                api_key=self.api_key or os.environ.get("GOOGLE_API_KEY"),
            )
            
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        self.messages = []
        self.contents = []

    def chat(self, prompt,  new_system_message=None):
        """
        Sends a prompt to the LLM and returns the response.  Includes the system message.
        Allows overriding the system message for this specific chat session.

        Args:
            prompt (str): The prompt to send to the LLM.
            history (list, optional): A list of previous messages in the conversation (for stateful chats).
                                      Each message should be a dictionary with 'role' and 'content' keys.
                                      Defaults to None.
            new_system_message (str, optional): A new system message to use for *this* chat session only.
                                                If provided, it overrides the default system message.
                                                Defaults to None.

        Returns:
            str: The response from the LLM.

        Raises:
            Exception: If an error occurs during the API call.
        """

        system_message_to_use = new_system_message if new_system_message is not None else self.current_system_message # Determine system message for this chat

        try:
            if self.provider == "openai":
                
                # Add the system message if it exists and this is the first turn
                if system_message_to_use:
                    self.messages = [] # reset if there is new chat
                    self.messages.append({"role": "system", "content": system_message_to_use})

                self.messages.append({"role": "user", "content": prompt})
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    stop=None,
                    temperature=self.temperature,
                )

                assistant_reply = ""
                # Find the first response from the chatbot that has text in it (some responses may not have text)
                for choice in response.choices:
                    if "text" in choice:
                        assistant_reply = choice.text
                if not assistant_reply:
                    assistant_reply = response.choices[0].message.content    
                self.messages.append({"role": "assistant", "content": assistant_reply})
                return assistant_reply
                '''
                messages.append({"role": "user", "content": prompt})  # User prompt

                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    **self.kwargs
                )
                return response.choices[0].message.content
                '''
            elif self.provider == "gemini":

                if system_message_to_use:
                    generate_content_config = types.GenerateContentConfig(
                            temperature=self.temperature,
                            response_mime_type="text/plain",
                            system_instruction=[
                                types.Part.from_text(text=system_message_to_use),
                            ])
                    self.contents = [] # reset for conversation
                else:
                    generate_content_config = types.GenerateContentConfig(
                            temperature=self.temperature,
                            response_mime_type="text/plain",
                            system_instruction=[
                                types.Part.from_text(text=self.default_system_message),
                            ])
                
                content = types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=prompt)#"""INSERT_INPUT_HERE"""),
                        ],)
                    
                self.contents.append(content)
                response = ""
                for chunk in self.client.models.generate_content_stream(
                        model=self.model_name,
                        contents=self.contents,
                        config=generate_content_config,
                    ):
                        #print(chunk.text, end="")
                    response = response + chunk.text
          
                '''
                    full_prompt = f"{system_message_to_use}\n{prompt}" if system_message_to_use else prompt

                    if history:  # Gemini takes a list of chat turns
                        chat = self.model.start_chat(history=history)
                    else:
                        chat = self.model.start_chat()
                    response = chat.send_message(full_prompt, **self.kwargs)'
                '''

                self.contents.append(
                        types.Content(
                        role="model",
                        parts=[
                            types.Part.from_text(text=response)#"""INSERT_INPUT_HERE"""),
                        ],
                        ))
                return response # Get the text content of the response

            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except Exception as e:
            print(f"Error during API call: {e}")
            raise

    def reset_system_message(self):
        """Resets the system message to the default specified at initialization."""
        self.current_system_message = self.default_system_message

    def update_system_message(self, new_system_message):
        """Update system message during the whole session"""
        self.current_system_message = new_system_message
        
# Example usage
if __name__ == "__main__":
        # ---- Gemini Example ----
    try:
        gemini_api_key = os.environ.get("GOOGLE_API_KEY")
        if not gemini_api_key:
            raise ValueError("Please set GOOGLE_API_KEY environment")
        default_system_message = "You are a friendly chatbot specializing in geography."
        gemini_chat = LLMChat(model_name="gemini-pro", provider="gemini", system_message=default_system_message, api_key=gemini_api_key)
        response1 = gemini_chat.chat("What is the capital of Japan?")
        print(f"Gemini Response 1 (Default System Message): {response1}")

        # Override the system message for this chat only
        response2 = gemini_chat.chat("Act as a chef, what is the most famous food of Italy?",
                                      new_system_message="You are a chef.")
        print(f"Gemini Response 2 (Overridden System Message): {response2}")

        # Normal chat with default system message
        response3 = gemini_chat.chat("what is the capital of Italy?")
        print(f"Gemini Response 3 (Default System Message): {response3}")

    except Exception as e:
        print(f"Gemini Error: {e}")

    # ---- OpenAI Example ----
    try:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("Please set OPENAI_API_KEY environment")
        default_system_message = "You are a helpful assistant that answers questions concisely."
        openai_chat = LLMChat(model_name="gpt-3.5-turbo", provider="openai", system_message=default_system_message, api_key=openai_api_key)
        response1 = openai_chat.chat("What is the capital of France?")
        print(f"OpenAI Response 1 (Default System Message): {response1}")

        # Override the system message for this chat only
        response2 = openai_chat.chat("Now answer like a pirate. What is the capital of England?",
                                      new_system_message="You are a pirate that answers questions in pirate slang")
        print(f"OpenAI Response 2 (Overridden System Message): {response2}")

        # Normal chat with default system message
        response3 = openai_chat.chat("And what about Italy?")
        print(f"OpenAI Response 3 (Default System Message): {response3}")

    except Exception as e:
        print(f"OpenAI Error: {e}")

