import os

# --- Configuration ---

# 1. Define the project files to be included in the context.
#    The script will look for these files in the directory it is run from.
FILES_TO_INCLUDE = [
    ".env.example",  # Using a safe example file, not the real .env
    "requirements.txt",
    "Dockerfile",
    "README.md",
    "src/config.py",
    "src/gemini.py",
    "src/bot.py"
]

# 2. Define the name of the output file.
OUTPUT_FILENAME = "llm_context.txt"

# --- Script Logic ---

def create_env_example_if_needed():
    """
    Creates a temporary .env.example from .env to avoid leaking secrets.
    Returns True if the file was created, False otherwise.
    """
    if ".env.example" in FILES_TO_INCLUDE and not os.path.exists(".env.example"):
        print("Creating temporary '.env.example' from '.env' for context...")
        if not os.path.exists(".env"):
            print("  - WARNING: .env file not found. Creating a generic .env.example.")
            with open(".env.example", "w", encoding="utf-8") as f:
                f.write(
                    'TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"\n'
                    'GEMINI_API_KEY="YOUR_GEMINI_API_KEY"\n'
                    'GEMINI_VISION_MODEL="gemini-pro-vision"\n'
                    'GEMINI_TEXT_MODEL="gemini-pro"\n'
                )
            return True

        with open(".env", "r", encoding="utf-8") as env_file:
            lines = env_file.readlines()
        
        with open(".env.example", "w", encoding="utf-8") as example_file:
            for line in lines:
                if "=" in line:
                    key = line.split("=")[0]
                    example_file.write(f'{key}="YOUR_{key}_HERE"\n')
        return True
    return False

def combine_project_files():
    """
    Combines the content of specified project files into a single
    text file, formatted for an LLM context.
    """
    was_example_created = create_env_example_if_needed()

    print(f"Starting to combine project files into '{OUTPUT_FILENAME}'...")

    try:
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as outfile:
            outfile.write(
                "# Project Context for LLM\n\n"
                "This file contains the complete source code and configuration "
                "for the project, structured for analysis by an LLM.\n\n"
            )

            for file_path in FILES_TO_INCLUDE:
                print(f"  - Processing: {file_path}")
                
                if not os.path.exists(file_path):
                    outfile.write(f'{"-"*80}\n')
                    outfile.write(f"--- FILE: {file_path} (Not Found)\n")
                    outfile.write(f'{"-"*80}\n\n')
                    print(f"    - WARNING: File not found. Skipping content.")
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as infile:
                        content = infile.read()
                    
                    file_extension = file_path.split('.')[-1]
                    lang_hint = ""
                    if file_extension == 'py':
                        lang_hint = 'python'
                    elif file_extension == 'md':
                        lang_hint = 'markdown'
                    
                    # Rename .env.example back to .env for the LLM's understanding
                    display_path = file_path.replace('.env.example', '.env')

                    outfile.write(f'{"-"*80}\n')
                    outfile.write(f"--- FILE: {display_path}\n")
                    outfile.write(f'{"-"*80}\n')
                    outfile.write(f"```{lang_hint}\n")
                    outfile.write(content.strip())
                    outfile.write("\n```\n\n")

                except Exception as e:
                    print(f"    - ERROR reading file {file_path}: {e}")

        print(f"\n✅ Success! Project combined into '{OUTPUT_FILENAME}'.")

    except IOError as e:
        print(f"\n❌ ERROR: Could not write to output file '{OUTPUT_FILENAME}': {e}")
    finally:
        # Clean up the temporary .env.example file if it was created
        if was_example_created:
            os.remove(".env.example")
            print("   - Cleaned up temporary '.env.example'.")


if __name__ == "__main__":
    combine_project_files()