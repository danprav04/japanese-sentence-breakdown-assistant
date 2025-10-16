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
        # This prompt establishes the persona of a Japanese teacher and asks for
        # text with predictable headers, allowing for markdown.
        prompt_parts = [
            "You are a helpful and patient Japanese language teacher.",
            "Your student has sent you a Japanese sentence (either as text or in an image) for analysis.",
            "Your responses should be short and concise.",
            "If an image is provided, first extract the Japanese text from it.",
            "\n--- YOUR TASK ---\n",
            "Provide a brief but detailed analysis of the sentence. Organize your response with these exact headers, each on a new line:",
            "Extracted Japanese Text",
            "English Translation",
            "Vocabulary Breakdown",
            "Grammar Analysis",
            "\n--- RESPONSE FORMATTING ---\n",
            "Use Markdown for emphasis (e.g., **bold** for key terms). I will handle the final formatting for the platform.",
            "Under 'Vocabulary Breakdown', list each word on a new line. **DO NOT use tables or the '|' character.** Use a format like: '**Word** (Reading) - Part of Speech: Meaning.'",
            "Under 'Grammar Analysis', provide a concise explanation. You can use numbers (e.g., '1.', '2.') or asterisks ('* ') for bullet points if needed.",
        ]
        if text:
            prompt_parts.append(f"\nHere is the sentence from your student: {text}")

        if image_bytes:
            img = Image.open(io.BytesIO(image_bytes))
            prompt_parts.append("\nHere is the image from your student:")
            prompt_parts.append(img)

        response = model.generate_content(prompt_parts)

        # Clean the history to focus on the content, not the instructions.
        # This helps guide follow-up questions towards the Japanese analysis.
        cleaned_user_prompt_parts = []
        if text:
            cleaned_user_prompt_parts.append(f"Please analyze the following Japanese sentence for me: {text}")
        elif image_bytes:
            # For image-based follow-ups, the image must be in the history.
            img = Image.open(io.BytesIO(image_bytes))
            cleaned_user_prompt_parts = ["Please analyze the Japanese text in this image.", img]

        conversation_history[user_id] = [
            {'role': 'user', 'parts': cleaned_user_prompt_parts},
            {'role': 'model', 'parts': [response.text]}
        ]

        return response.text

    elif text: # It's a follow-up question
        if not conversation_history.get(user_id):
            return "Please send a Japanese sentence or image first so I have something to talk about."

        chat_model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
        chat = chat_model.start_chat(history=conversation_history[user_id])
        # Add a conciseness instruction for follow-up questions as well.
        response = chat.send_message("Please answer this concisely: " + text)

        conversation_history[user_id] = chat.history

        return response.text

    else:
        return "Please send a Japanese sentence or an image with a Japanese sentence."