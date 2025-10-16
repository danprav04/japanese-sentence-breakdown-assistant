import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest
from .config import TELEGRAM_BOT_TOKEN
from .gemini import get_gemini_response

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def format_response(text: str) -> str:
    """
    Takes text from Gemini (potentially with Markdown) and formats it
    for Telegram's MarkdownV2. It handles both initial analysis responses
    with headers and follow-up messages without them.
    """
    def process_text_content(content: str) -> str:
        """
        Escapes text for MarkdownV2, but converts Gemini's **bold** to
        Telegram's *bold* and preserves list formatting.
        """
        placeholders = []

        # Protect **bold** text and convert it to Telegram's *bold* format.
        def bold_replacer(match):
            inner_content = match.group(1)
            # Escape characters inside the bold tag that could break formatting.
            safe_content = re.sub(r'[\[\]()~`>#+\-=|{}.!]', r'\\\g<0>', inner_content)
            placeholders.append(f"*{safe_content}*")
            return f"__PLACEHOLDER_{len(placeholders)-1}__"
        
        processed_text = re.sub(r'\*\*(.*?)\*\*', bold_replacer, content)

        # Escape all remaining special characters.
        escape_chars = r"[_*\[\]()~`>#+\-=|{}.!]"
        processed_text = re.sub(escape_chars, r"\\\g<0>", processed_text)
        
        # Restore the protected bold text.
        for i, replacement in enumerate(placeholders):
            processed_text = processed_text.replace(f"__PLACEHOLDER_{i}__", replacement)
            
        # Fix list formatting that may have been broken by the escaper.
        # Un-escape the dot in numbered lists (e.g., "1\." -> "1.").
        processed_text = re.sub(r'(?m)^(\s*\d+)\\\.', r'\1.', processed_text)
        # Replace an escaped leading asterisk with a bullet point for clarity.
        processed_text = re.sub(r'(?m)^\\\*\s', '• ', processed_text)

        return processed_text

    # Split the response by known headers to format it section by section.
    sections = re.split(r'\n(Extracted Japanese Text|English Translation|Vocabulary Breakdown|Grammar Analysis)\n', text)
    
    # If splitting results in only one part, no headers were found.
    # This indicates a follow-up message, so we process the entire text.
    if len(sections) <= 1:
        return process_text_content(text)
    
    # Headers were found; format each section.
    formatted_parts = []
    # The first element of sections is anything before the first header, usually empty.
    # We iterate through header-content pairs.
    for i in range(1, len(sections), 2):
        header = sections[i]
        content = sections[i+1].strip()
        
        # Make the header bold.
        formatted_parts.append(f"*{header}*")
        # Process the content of the section.
        formatted_parts.append(process_text_content(content))

    return "\n\n".join(formatted_parts)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    welcome_text = (
        "Welcome to the Japanese Language Analyzer bot\\!\n\n"
        "Send me a Japanese sentence or an image containing Japanese text, "
        "and I will break down the grammar and provide a translation\\."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages from the user."""
    user_id = update.message.from_user.id
    user_text = update.message.text
    
    loading_message = await update.message.reply_text("⏳ Analyzing, please wait\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)

    try:
        raw_response = get_gemini_response(user_id, text=user_text)
        if not raw_response.strip():
             raise ValueError("Received empty response from API")
        formatted_response = format_response(raw_response)
        await loading_message.edit_text(formatted_response, parse_mode=ParseMode.MARKDOWN_V2)
    except BadRequest as e:
        logger.warning(f"MarkdownV2 parsing failed: {e}. Sending raw response as plain text.")
        # As a fallback, send the original unformatted response.
        await loading_message.edit_text(raw_response)
    except Exception as e:
        logger.error(f"Error processing text message: {e}")
        await loading_message.edit_text("Sorry, I encountered an error\\. Please try again\\.", parse_mode=ParseMode.MARKDOWN_V2)

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles image messages from the user."""
    user_id = update.message.from_user.id
    
    loading_message = await update.message.reply_text("⏳ Analyzing image, please wait\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        user_caption = update.message.caption or ""
        raw_response = get_gemini_response(user_id, text=user_caption, image_bytes=bytes(photo_bytes))
        if not raw_response.strip():
             raise ValueError("Received empty response from API")
        formatted_response = format_response(raw_response)
        await loading_message.edit_text(formatted_response, parse_mode=ParseMode.MARKDOWN_V2)
    except BadRequest as e:
        logger.warning(f"MarkdownV2 parsing failed: {e}. Sending raw response as plain text.")
        # As a fallback, send the original unformatted response.
        await loading_message.edit_text(raw_response)
    except Exception as e:
        logger.error(f"Error processing image message: {e}")
        await loading_message.edit_text("Sorry, I encountered an error processing the image\\.", parse_mode=ParseMode.MARKDOWN_V2)

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image_message))

    application.run_polling()

if __name__ == "__main__":
    main()