import google.generativeai as genai
from PIL import Image
import io

from .config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

# In-memory conversation history
conversation_history = {}

def get_gemini_response(user_id, text=None, image_bytes=None):
    """
    Gets a response from the Gemini API.

    Args:
        user_id: The ID of the user to maintain conversation history.
        text: The text input from the user.
        image_bytes: The image bytes from the user.

    Returns:
        The response from the Gemini API as a string.
    """
    model = genai.GenerativeModel('gemini-pro-vision')

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # If new Japanese text or image is provided, start a new conversation thread
    if text and any(char > '\u3040' for char in text) or image_bytes:
        conversation_history[user_id] = []
        prompt = [
            "You are a helpful Japanese language assistant.",
            "Analyze the following Japanese sentence or the sentence in the image.",
            "Break it down into grammar points with explanations.",
            "Provide the English translation.",
            "If an image is provided, first extract the Japanese text from it."
        ]
        if text:
            prompt.append(f"Here is the sentence: '{text}'")
        
        if image_bytes:
            img = Image.open(io.BytesIO(image_bytes))
            prompt.append(img)
        
        conversation_history[user_id].append({"role": "user", "parts": prompt})

    elif text: # It's a follow-up question
        conversation_history[user_id].append({"role": "user", "parts": [text]})

    else:
        return "Please send a Japanese sentence or an image with a Japanese sentence."

    # Generate the response
    chat = model.start_chat(history=conversation_history[user_id])
    response = chat.send_message(conversation_history[user_id][-1]['parts'], stream=False)
    
    # Add the model's response to the history
    conversation_history[user_id].append({"role": "model", "parts": [response.text]})

    return response.text