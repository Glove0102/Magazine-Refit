import fitz  # PyMuPDF
import os
import time
from openai import OpenAI
from replit.object_storage import Client

# --- Configuration ---
# 1. Name of the PDF you want to translate
input_pdf = "0723.pdf.pdf"
# 2. Name for the new, translated PDF
output_pdf = "0723zh.pdf"
# 3. Name of the REGULAR font file
font_path_regular = "NotoSansSC-Regular.ttf"
# 4. Name of the BOLD font file
font_path_bold = "NotoSansSC-Bold.ttf"

# --- OpenAI Configuration ---
# Initialize the OpenAI client
# It's recommended to set your API key as an environment variable or use Replit secrets.
# Example: client = OpenAI(api_key="YOUR_API_KEY")
# If OPENAI_API_KEY is set as a secret in Replit, this will automatically use it.
client = OpenAI()

def translate_with_openai(text):
    """
    Translates text using OpenAI's GPT model.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",  # Specify the model as requested
            messages=[
                {"role": "system", "content": "You are a helpful assistant that translates text to Simplified Chinese."},
                {"role": "user", "content": f"Translate the following text to Simplified Chinese: \"{text}\""}
            ],
            max_completion_tokens=2500 # Adjust as needed
        )
        translated_text = response.choices[0].message.content.strip()
        return translated_text
    except Exception as e:
        print(f"      - OpenAI translation failed for '{text[:30]}...': {e}")
        return None

def translate_pdf_with_bolding(input_path, output_path, regular_font, bold_font):
    """
    Translates PDF text, preserving color and bolding.
    """
    # Initialize Object Storage client
    storage_client = Client()

    # Check if PDF exists in Object Storage or local filesystem
    pdf_data = None
    if os.path.exists(input_path):
        # Read from local file
        with open(input_path, 'rb') as f:
            pdf_data = f.read()
    else:
        try:
            # Try to download from Object Storage
            print(f"📥 Downloading '{input_path}' from Object Storage...")
            pdf_data = storage_client.download_as_bytes(input_path)
        except Exception as e:
            print(f"❌ Error: The file '{input_path}' was not found in local storage or Object Storage. Error: {e}")
            return
    if not os.path.exists(regular_font):
        print(f"❌ Error: Regular font '{regular_font}' not found.")
        return
    if not os.path.exists(bold_font):
        print(f"❌ Error: Bold font '{bold_font}' not found. Bold text will use the regular font.")
        # Degrade gracefully by using regular font as a fallback
        bold_font = regular_font

    print(f"📖 Opening '{input_path}'...")
    original_doc = fitz.open(stream=pdf_data, filetype="pdf")
    new_doc = fitz.open()

    print("🚀 Starting translation process with bold detection...")

    for page_num, page in enumerate(original_doc):
        print(f"    -> Processing page {page_num + 1}/{len(original_doc)}...")
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.show_pdf_page(new_page.rect, original_doc, page_num)

        text_blocks = page.get_text("dict")["blocks"]
        for block in text_blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        original_text = span["text"].strip()
                        rect = fitz.Rect(span["bbox"])

                        if original_text:
                            # --- NEW: BOLD DETECTION LOGIC ---
                            # PyMuPDF uses a flag system. Flag '16' (2**4) means bold.
                            is_bold = span['flags'] & 16

                            # Choose the font file and a unique name for embedding in the PDF
                            if is_bold:
                                font_file_to_use = bold_font
                                font_name_for_pdf = "china-font-bold"
                            else:
                                font_file_to_use = regular_font
                                font_name_for_pdf = "china-font-regular"
                            # --- END OF NEW LOGIC ---

                            try:
                                # Skip very short or non-meaningful text
                                if len(original_text.strip()) < 2:
                                    continue

                                # Use OpenAI for translation
                                translated_text = translate_with_openai(original_text)

                                # If translation failed, skip this text
                                if translated_text is None:
                                    print(f"      - Skipping translation for: '{original_text[:30]}...'")
                                    continue

                                new_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

                                # Normalize color values to 0-1 range
                                original_color = span["color"]
                                if isinstance(original_color, int):
                                    # Convert integer color to RGB tuple (0-1 range)
                                    r = ((original_color >> 16) & 255) / 255.0
                                    g = ((original_color >> 8) & 255) / 255.0
                                    b = (original_color & 255) / 255.0
                                    normalized_color = (r, g, b)
                                elif isinstance(original_color, (list, tuple)):
                                    # Ensure color components are in 0-1 range
                                    if len(original_color) >= 3:
                                        # Check if values are in 0-255 range and normalize
                                        if any(c > 1.0 for c in original_color[:3]):
                                            normalized_color = tuple(c / 255.0 for c in original_color[:3])
                                        else:
                                            normalized_color = tuple(original_color[:3])
                                    else:
                                        normalized_color = (0, 0, 0)  # Default to black
                                else:
                                    normalized_color = (0, 0, 0)  # Default to black

                                # Insert text using the chosen font
                                new_page.insert_textbox(
                                    rect,
                                    translated_text,
                                    fontname=font_name_for_pdf,  # Use the selected font name
                                    fontfile=font_file_to_use, # Use the selected font file
                                    fontsize=span["size"],
                                    color=normalized_color,
                                    align=fitz.TEXT_ALIGN_LEFT
                                )
                            except Exception as e:
                                print(f"      - Could not process span: '{original_text}'. Error: {e}")
    try:
        print(f"💾 Saving translated PDF as '{output_path}'...")
        # Save to local file first
        new_doc.save(output_path, garbage=4, deflate=True, clean=True)

        # Also upload to Object Storage for persistence
        print(f"☁️ Uploading to Object Storage...")
        with open(output_path, 'rb') as f:
            storage_client.upload_from_bytes(output_path, f.read())
        print("✅ Translation complete! PDF saved locally and uploaded to Object Storage.")
    except Exception as e:
        print(f"❌ Error saving PDF: {e}")
    finally:
        original_doc.close()
        new_doc.close()

# --- Run the script ---
if __name__ == "__main__":
    translate_pdf_with_bolding(input_pdf, output_pdf, font_path_regular, font_path_bold)