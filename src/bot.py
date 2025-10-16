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
    for Telegram's MarkdownV2.
    """
    def escape_markdown_v2_text(text: str, inside_bold: bool = False) -> str:
        """
        Escapes special characters for MarkdownV2.
        If inside_bold is True, we're escaping text that will appear between * markers.
        """
        # Characters that need escaping in MarkdownV2
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        
        result = []
        for char in text:
            if char == '\\':
                result.append('\\\\')
            elif char in escape_chars:
                # If we're inside bold text and it's an asterisk, escape it
                # Otherwise escape all special chars
                result.append('\\' + char)
            else:
                result.append(char)
        
        return ''.join(result)
    
    def process_bold_text(text: str) -> str:
        """
        Process text containing **bold** markers and convert to Telegram MarkdownV2 format.
        """
        result = []
        i = 0
        
        while i < len(text):
            # Check for bold marker
            if i < len(text) - 1 and text[i:i+2] == '**':
                # Find the closing **
                end = text.find('**', i + 2)
                if end != -1:
                    # Extract content between ** markers
                    bold_content = text[i+2:end]
                    # Escape the content for MarkdownV2
                    escaped_content = escape_markdown_v2_text(bold_content, inside_bold=True)
                    # Add as Telegram bold (single *)
                    result.append(f'*{escaped_content}*')
                    i = end + 2
                    continue
            
            # Not a bold section, accumulate regular text
            regular_text_start = i
            # Find next ** or end of string
            next_bold = text.find('**', i)
            if next_bold == -1:
                # No more bold, take rest of string
                regular_text = text[i:]
                i = len(text)
            else:
                # Take text up to next bold
                regular_text = text[i:next_bold]
                i = next_bold
            
            if regular_text:
                result.append(escape_markdown_v2_text(regular_text, inside_bold=False))
        
        return ''.join(result)
    
    # Split by headers
    header_pattern = r'\n(Extracted Japanese Text|English Translation|Vocabulary Breakdown|Grammar Analysis)\n'
    sections = re.split(header_pattern, text)
    
    # If no headers found, process entire text
    if len(sections) <= 1:
        return process_bold_text(text.strip())
    
    # Process each section
    formatted_parts = []
    
    # Handle content before first header
    if sections[0].strip():
        formatted_parts.append(process_bold_text(sections[0].strip()))
    
    # Process header/content pairs
    for i in range(1, len(sections), 2):
        if i+1 < len(sections):
            header = sections[i]
            content = sections[i+1].strip()
            
            # Escape header and make it bold
            escaped_header = escape_markdown_v2_text(header, inside_bold=True)
            formatted_parts.append(f'*{escaped_header}*')
            
            # Process content
            formatted_parts.append(process_bold_text(content))
    
    return '\n\n'.join(formatted_parts)


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