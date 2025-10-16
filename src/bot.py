import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from .config import TELEGRAM_BOT_TOKEN
from .gemini import get_gemini_response

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def escape_markdown_v2(text: str) -> str:
    """Escapes characters for Telegram's MarkdownV2 parser."""
    # Characters to escape are: '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'
    escape_chars = r"[_*\[\]()~`>#+\-=|{}.!]"
    return re.sub(escape_chars, r"\\\g<0>", text)

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
        response = get_gemini_response(user_id, text=user_text)
        safe_response = escape_markdown_v2(response)
        await loading_message.edit_text(safe_response, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Error processing text message: {e}")
        error_text = escape_markdown_v2("Sorry, I encountered an error. Please try again.")
        await loading_message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles image messages from the user."""
    user_id = update.message.from_user.id
    
    loading_message = await update.message.reply_text("⏳ Analyzing image, please wait\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        user_caption = update.message.caption or ""
        response = get_gemini_response(user_id, text=user_caption, image_bytes=bytes(photo_bytes))
        safe_response = escape_markdown_v2(response)
        await loading_message.edit_text(safe_response, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Error processing image message: {e}")
        error_text = escape_markdown_v2("Sorry, I encountered an error processing the image.")
        await loading_message.edit_text(error_text, parse_mode=ParseMode.MARKDOWN_V2)

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image_message))

    application.run_polling()

if __name__ == "__main__":
    main()