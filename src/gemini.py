import google.generativeai as genai
from PIL import Image
import io

from .config import GEMINI_API_KEY, GEMINI_VISION_MODEL, GEMINI_TEXT_MODEL

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
    # Use the vision model specified in the environment variables
    model = genai.GenerativeModel(GEMINI_VISION_MODEL)

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # If new Japanese text or image is provided, start a new conversation
    if (text and any(char > '\u3040' for char in text)) or image_bytes:
        prompt_parts = [
            "You are a helpful Japanese language assistant for Telegram.",
            "Analyze the following Japanese sentence or the sentence in the image.",
            "Your output MUST be formatted using Telegram's MarkdownV2 syntax.",
            "\n--- FORMATTING RULES ---\n",
            "1. Use *bold* for all headers (e.g., *Extracted Japanese Text*). Do NOT use '##'.",
            "2. Use _italics_ for alternative translations or notes.",
            "3. For the 'Vocabulary Breakdown', format it as a single pre-formatted code block (using ```). Ensure the columns are neatly aligned with spaces.",
            "4. Use `inline code` for Japanese words within your grammar analysis.",
            "5. You MUST escape the following characters with a preceding backslash '\\': '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'",
            "   For example, write 'go straight ahead\\.' instead of 'go straight ahead.'",
            "\n--- TASK ---\n",
            "Provide the following sections: *Extracted Japanese Text*, *English Translation*, *Vocabulary Breakdown*, and *Grammar Analysis*.",
        ]
        if text:
            prompt_parts.append(f"\nHere is the sentence: `{text}`")
        
        if image_bytes:
            img = Image.open(io.BytesIO(image_bytes))
            prompt_parts.append(img)
        
        # For a new analysis, we use generate_content directly
        response = model.generate_content(prompt_parts)
        
        # We save the initial prompt and response to start a conversation history
        conversation_history[user_id] = [
            {'role': 'user', 'parts': prompt_parts},
            {'role': 'model', 'parts': [response.text]}
        ]
        
        return response.text

    elif text: # It's a follow-up question
        if not conversation_history.get(user_id):
            return "Please send a Japanese sentence or image first so I have something to talk about\\."

        # Use the text model specified in the environment for follow-ups
        chat_model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
        chat = chat_model.start_chat(history=conversation_history[user_id])
        
        follow_up_prompt = f"{text}\n\n(Remember to format your response in Telegram MarkdownV2 and escape special characters like '.' and '-')",
        response = chat.send_message(follow_up_prompt)
        
        conversation_history[user_id] = chat.history
        
        return response.text

    else:
        return "Please send a Japanese sentence or an image with a Japanese sentence\\."