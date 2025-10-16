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

def escape_markdown_v2(text: str) -> str:
    """Escapes characters for Telegram's MarkdownV2 parser."""
    escape_chars = r"[_*\[\]()~`>#+\-=|{}.!]"
    return re.sub(escape_chars, r"\\\g<0>", text)

def format_response(text: str) -> str:
    """
    Takes the clean text from Gemini and applies MarkdownV2 formatting.
    """
    # Escape the entire response first to make it safe
    escaped_text = escape_markdown_v2(text)

    # Find the vocabulary section
    vocab_match = re.search(r"Vocabulary Breakdown\n(.*?)\nGrammar Analysis", escaped_text, re.DOTALL)
    if vocab_match:
        # Extract the vocabulary content, un-escape it, and wrap in a code block
        vocab_content = vocab_match.group(1).strip()
        # The content of a code block doesn't need escaping
        unescaped_vocab = vocab_content.replace('\\', '') 
        code_block = f"```\n{unescaped_vocab}\n```"
        # Replace the original vocabulary section with the formatted code block
        escaped_text = escaped_text.replace(vocab_content, code_block)

    # Add bold formatting to headers AFTER processing the code block
    headers = [
        "Extracted Japanese Text",
        "English Translation",
        "Vocabulary Breakdown",
        "Grammar Analysis"
    ]
    for header in headers:
        # The header might already be escaped, so we find and replace that version
        escaped_header = escape_markdown_v2(header)
        escaped_text = escaped_text.replace(escaped_header, f"*{header}*")
    
    return escaped_text

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
        formatted_response = format_response(raw_response)
        await loading_message.edit_text(formatted_response, parse_mode=ParseMode.MARKDOWN_V2)
    except BadRequest as e:
        logger.warning(f"MarkdownV2 parsing failed: {e}. Sending as plain text.")
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
        formatted_response = format_response(raw_response)
        await loading_message.edit_text(formatted_response, parse_mode=ParseMode.MARKDOWN_V2)
    except BadRequest as e:
        logger.warning(f"MarkdownV2 parsing failed: {e}. Sending as plain text.")
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