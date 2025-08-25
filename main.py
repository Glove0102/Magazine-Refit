import fitz  # PyMuPDF
import translators as ts
import os
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
                                translated_text = ts.translate_text(
                                    original_text, translator='google', to_language='zh-CN'
                                )

                                new_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)

                                # Insert text using the chosen font
                                new_page.insert_textbox(
                                    rect,
                                    translated_text,
                                    fontname=font_name_for_pdf,  # Use the selected font name
                                    fontfile=font_file_to_use, # Use the selected font file
                                    fontsize=span["size"],
                                    color=span["color"],
                                    align=fitz.TEXT_ALIGN_LEFT
                                )
                            except Exception as e:
                                print(f"      - Could not translate text: '{original_text}'. Error: {e}")
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