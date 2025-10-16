import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from .config import TELEGRAM_BOT_TOKEN
from .gemini import get_gemini_response

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# State to track the last analyzed sentence for follow-up questions
user_context = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Welcome to the Japanese Language Analyzer bot!\n\n"
        "Send me a Japanese sentence or an image containing Japanese text, "
        "and I will break down the grammar and provide a translation."
    )

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles text messages from the user."""
    user_id = update.message.from_user.id
    user_text = update.message.text

    # Show a "typing..." status
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        response = get_gemini_response(user_id, text=user_text)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error processing text message: {e}")
        await update.message.reply_text("Sorry, I encountered an error. Please try again.")

async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles image messages from the user."""
    user_id = update.message.from_user.id
    
    # Show a "typing..." status
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        user_caption = update.message.caption if update.message.caption else ""

        response = get_gemini_response(user_id, text=user_caption, image_bytes=bytes(photo_bytes))
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error processing image message: {e}")
        await update.message.reply_text("Sorry, I encountered an error processing the image.")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image_message))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()