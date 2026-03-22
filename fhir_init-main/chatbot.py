# chatbot.py
import logging
import sys

# Try importing ollama
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Hugging Face fallback
from transformers import pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class AYUSHChatbot:
    def __init__(self, model: str = "llama3", fallback_model: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"):
        """
        Initializes the chatbot. Prefers Ollama, falls back to Hugging Face if unavailable.
        """
        self.use_ollama = False
        self.model = model
        self.fallback_model = fallback_model

        self.conversation_history = [
            {
                "role": "system",
                "content": (
                    "You are Dr. AYUSH, an AI assistant specialized in traditional medicine like Ayurveda. "
                    "You can answer questions about general symptoms and suggest traditional, non-medical approaches. "
                    "You must always include a disclaimer that this is not medical advice and recommend consulting a qualified doctor."
                ),
            }
        ]

        if OLLAMA_AVAILABLE:
            try:
                ollama.ps()  # check if Ollama service is running
                self.use_ollama = True
                logging.info(f"AYUSHChatbot initialized with Ollama model: {self.model}")
            except Exception:
                logging.warning("Ollama not running. Will initialize Hugging Face on demand.")
                self.use_ollama = False
                self.hf_pipeline = None
        else:
            logging.warning("Ollama not available. Will initialize Hugging Face on demand.")
            self.use_ollama = False
            self.hf_pipeline = None

    def _init_hf(self):
        """Initialize Hugging Face pipeline as fallback."""
        logging.info(f"Loading Hugging Face model: {self.fallback_model} (this may take some time)...")
        self.hf_pipeline = pipeline("text-generation", model=self.fallback_model, device_map="auto")
        self.use_ollama = False
        logging.info("Hugging Face fallback initialized.")
    
    def chat(self, user_message: str) -> str:
        """
        A non-streaming version that collects the full response from the stream 
        and returns it as a single string. This is what your web server will call.
        """
        full_response = ""
        try:
            # Internally call the streaming function and build the full response
            for chunk in self.chat_stream(user_message):
                full_response += chunk
            return full_response.strip()
        except Exception as e:
            logging.error(f"Non-streaming chat error: {e}")
            return "I'm having trouble running the model locally."

    def chat_stream(self, user_message: str):
        """
        Handles conversational interaction with either Ollama or Hugging Face.
        """
        try:
            # Add user's message
            self.conversation_history.append({"role": "user", "content": user_message})

            if not self.use_ollama and self.hf_pipeline is None:
                self._init_hf()

            if self.use_ollama:
                # Ollama streaming
                stream = ollama.chat(
                    model=self.model,
                    messages=self.conversation_history,
                    stream=True,
                )
                full_response = ""
                for chunk in stream:
                    content = chunk['message']['content']
                    full_response += content
                    yield content
                if full_response:
                    self.conversation_history.append({"role": "assistant", "content": full_response})
                    logging.info(f"User: {user_message}")
                    logging.info(f"Bot: {full_response.strip()}")
            else:
                # Hugging Face fallback (non-streaming, but we simulate streaming by chunks)
                prompt = self._build_prompt()
                outputs = self.hf_pipeline(prompt, max_new_tokens=300, do_sample=True, temperature=0.7)
                full_response = outputs[0]["generated_text"][len(prompt):]

                # "Stream" the text in chunks
                for i in range(0, len(full_response), 50):
                    yield full_response[i:i+50]

                self.conversation_history.append({"role": "assistant", "content": full_response})
                logging.info(f"User: {user_message}")
                logging.info(f"Bot: {full_response.strip()}")

        except Exception as e:
            logging.error(f"Chat stream error: {e}")
            yield "I'm having trouble running the model locally."

    def _build_prompt(self):
        """Convert conversation history into a text prompt for HF models."""
        prompt = ""
        for msg in self.conversation_history:
            if msg["role"] == "system":
                prompt += f"System: {msg['content']}\n"
            elif msg["role"] == "user":
                prompt += f"User: {msg['content']}\n"
            elif msg["role"] == "assistant":
                prompt += f"Assistant: {msg['content']}\n"
        prompt += "Assistant:"
        return prompt

# Run chatbot in CLI mode
if __name__ == "__main__":
    print("Initializing Dr. AYUSH (local)...")
    print("\n⚠️ Disclaimer: Dr. AYUSH provides general knowledge about traditional medicine.")
    print("This is not medical advice. Always consult a qualified doctor for health issues.\n")

    bot = AYUSHChatbot()

    print("\n--- Dr. AYUSH is ready to help ---")
    print("Ask a question about traditional medicine or describe your symptoms.")
    print("Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        user_message = input("You: ")
        if user_message.lower() in ["exit", "quit"]:
            print("Dr. AYUSH: Stay healthy. Goodbye!")
            break

        print("Dr. AYUSH: ", end="", flush=True)
        for chunk in bot.chat_stream(user_message):
            print(chunk, end="", flush=True)
        print()  # newline after response
