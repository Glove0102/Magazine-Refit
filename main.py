
import fitz  # PyMuPDF
import os
import time
import sys
from openai import OpenAI
from replit.object_storage import Client
import json
import traceback

# --- New Logging Configuration ---
LOG_FILE = "translation_log.txt"

def log_message(message):
    """Appends a message to the log file with a timestamp."""
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
        print(f"Logging failed: {e}")

# --- Configuration ---
output_pdf = "0723zh.pdf"
font_path_regular = "NotoSansSC-Regular.ttf"
font_path_bold = "NotoSansSC-Bold.ttf"

# --- OpenAI Configuration ---
if "OPENAI_API_KEY" not in os.environ:
    log_message("FATAL ERROR: The OPENAI_API_KEY environment variable is not set.")
    sys.exit(1)
client = OpenAI()

def translate_batch_with_openai(text_segments):
    try:
        texts_to_translate = []
        for i, segment in enumerate(text_segments):
            if len(segment['text'].strip()) >= 2:
                texts_to_translate.append({"id": i, "text": segment['text']})

        if not texts_to_translate:
            return {}

        prompt = f"""Translate the following texts to Simplified Chinese. Return the result as a JSON object where each key is the "id" and the value is the translated text.

Input texts:
{texts_to_translate}

Return format: {{"0": "translated text 1", "1": "translated text 2", ...}}"""

        response = client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that translates text to Simplified Chinese. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=19000,
            response_format={"type": "json_object"}
        )

        response_content = response.choices[0].message.content
        log_message(f"      - API response received, length: {len(response_content) if response_content else 0}")
        if not response_content:
            log_message("      - Empty response from OpenAI API - likely token limit exceeded")
            return {}

        translations = json.loads(response_content)
        log_message(f"      - Successfully parsed {len(translations)} translations")
        return translations

    except json.JSONDecodeError as e:
        log_message(f"      - JSON decode error: {e}")
        log_message(f"      - Response content preview: {response.choices[0].message.content[:200] if response.choices[0].message.content else 'None'}")
        return {}
    except Exception as e:
        log_message(f"      - Batch OpenAI translation failed: {e}")
        return {}

def translate_pdf_with_bolding(input_path, output_path, regular_font, bold_font):
    log_message(f"--- Starting translation for '{input_path}' ---")

    log_message("Initializing Object Storage client...")
    storage_client = Client()
    log_message("Object Storage client initialized.")

    pdf_data = None
    if os.path.exists(input_path):
        log_message(f"Reading '{input_path}' from local filesystem.")
        with open(input_path, 'rb') as f:
            pdf_data = f.read()
    else:
        try:
            log_message(f"Downloading '{input_path}' from Object Storage...")
            pdf_data = storage_client.download_as_bytes(input_path)
            log_message("Download complete.")
        except Exception as e:
            log_message(f"❌ Error: The file '{input_path}' was not found. Error: {e}")
            return

    if not os.path.exists(regular_font):
        log_message(f"❌ Error: Regular font '{regular_font}' not found.")
        return
    if not os.path.exists(bold_font):
        log_message(f"❌ Warning: Bold font '{bold_font}' not found. Using regular font as fallback.")
        bold_font = regular_font

    log_message(f"📖 Opening PDF stream...")
    original_doc = fitz.open(stream=pdf_data, filetype="pdf")

    base_name = os.path.splitext(input_path)[0]
    output_dir = base_name

    log_message(f"🚀 Starting translation. Pages will be saved to '{output_dir}/'")

    for page_num, page in enumerate(original_doc):
        log_message(f"    -> Processing page {page_num + 1}/{len(original_doc)}...")
        
        single_page_doc = fitz.open()
        new_page = single_page_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.show_pdf_page(new_page.rect, original_doc, page_num)
        
        text_segments = []
        text_blocks = page.get_text("dict")["blocks"]
        
        for block in text_blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        original_text = span["text"].strip()
                        if original_text and len(original_text.strip()) >= 2:
                            text_segments.append({
                                'text': original_text, 
                                'rect': fitz.Rect(span["bbox"]), 
                                'is_bold': span['flags'] & 16, 
                                'color': span["color"], 
                                'size': span["size"]
                            })
        
        log_message(f"      - Found {len(text_segments)} text segments.")
        
        if not text_segments:
            log_message("      - No text on page, saving empty page.")
            try:
                page_filename = f"page_{page_num + 1:03d}.pdf"
                storage_page_path = f"{output_dir}/{page_filename}"
                import io
                pdf_bytes = io.BytesIO()
                single_page_doc.save(pdf_bytes, garbage=4, deflate=True, clean=True)
                pdf_bytes.seek(0)
                storage_client.upload_from_bytes(storage_page_path, pdf_bytes.getvalue())
                log_message(f"      ✅ Saved to Object Storage: {storage_page_path}")
            except Exception as e:
                log_message(f"      ❌ Error saving empty page {page_num + 1}: {e}")
            finally:
                single_page_doc.close()
            continue
        
        batch_size = 50
        all_translations = {}
        
        for i in range(0, len(text_segments), batch_size):
            batch = text_segments[i:i+batch_size]
            log_message(f"      - Translating batch {i//batch_size + 1}...")
            batch_translations = translate_batch_with_openai(batch)
            for key, value in batch_translations.items():
                all_translations[str(int(key) + i)] = value
        
        translations = all_translations
        
        for i, segment in enumerate(text_segments):
            try:
                translated_text = translations.get(str(i))
                if not translated_text:
                    continue
                
                if segment['is_bold']:
                    font_file_to_use = bold_font
                    font_name_for_pdf = "china-font-bold"
                else:
                    font_file_to_use = regular_font
                    font_name_for_pdf = "china-font-regular"
                
                cover_rect = fitz.Rect(segment['rect'].x0 - 0.5, segment['rect'].y0, segment['rect'].x1 + 0.5, segment['rect'].y1)
                new_page.draw_rect(cover_rect, color=None, fill=(1, 1, 1))
                
                original_color = segment['color']
                if isinstance(original_color, int):
                    r = ((original_color >> 16) & 255) / 255.0
                    g = ((original_color >> 8) & 255) / 255.0
                    b = (original_color & 255) / 255.0
                    normalized_color = (r, g, b)
                elif isinstance(original_color, (list, tuple)):
                    if len(original_color) >= 3:
                        if any(c > 1.0 for c in original_color[:3]):
                            normalized_color = tuple(c / 255.0 for c in original_color[:3])
                        else:
                            normalized_color = tuple(original_color[:3])
                    else:
                        normalized_color = (0, 0, 0)
                else:
                    normalized_color = (0, 0, 0)
                
                if sum(normalized_color) > 2.7:
                    normalized_color = (0, 0, 0)
                
                text_inserted = False
                original_font_size = segment['size']
                
                for font_scale in [1.2, 1.0, 0.9, 0.8, 0.7, 0.6]:
                    try:
                        scaled_font_size = original_font_size * font_scale
                        result = new_page.insert_textbox(
                            segment['rect'], 
                            translated_text, 
                            fontname=font_name_for_pdf, 
                            fontfile=font_file_to_use, 
                            fontsize=scaled_font_size, 
                            color=normalized_color, 
                            align=fitz.TEXT_ALIGN_LEFT
                        )
                        if result >= 0:
                            text_inserted = True
                            break
                    except Exception:
                        continue
                
                if not text_inserted:
                    try:
                        text_x = segment['rect'].x0
                        text_y = segment['rect'].y0 + (segment['rect'].height * 0.8)
                        new_page.insert_text(
                            (text_x, text_y), 
                            translated_text, 
                            fontname=font_name_for_pdf, 
                            fontfile=font_file_to_use, 
                            fontsize=original_font_size * 0.8, 
                            color=normalized_color
                        )
                    except Exception as fallback_error:
                        log_message(f"      - All text insertion methods failed for segment {i}: {fallback_error}")
                        
            except Exception as e:
                log_message(f"      - Could not process segment {i}: '{segment['text'][:30]}...'. Error: {e}")
        
        try:
            page_filename = f"page_{page_num + 1:03d}.pdf"
            storage_page_path = f"{output_dir}/{page_filename}"
            import io
            pdf_bytes = io.BytesIO()
            single_page_doc.save(pdf_bytes, garbage=4, deflate=True, clean=True)
            pdf_bytes.seek(0)
            storage_client.upload_from_bytes(storage_page_path, pdf_bytes.getvalue())
            log_message(f"      ✅ Saved to Object Storage: {storage_page_path}")
        except Exception as e:
            log_message(f"      ❌ Error saving page {page_num + 1}: {e}")
        finally:
            single_page_doc.close()
    
    log_message(f"✅ Translation complete for '{input_path}'!")
    original_doc.close()

# --- Run the script ---
if __name__ == "__main__":
    try:
        log_message("--- main.py script started ---")
        if len(sys.argv) > 1:
            input_pdf_from_arg = sys.argv[1]
            log_message(f"Input PDF from command line: {input_pdf_from_arg}")
            translate_pdf_with_bolding(input_pdf_from_arg, output_pdf, font_path_regular, font_path_bold)
            log_message("--- main.py script finished successfully ---")
        else:
            log_message("ERROR: No input PDF file was specified as a command-line argument.")
    except Exception as e:
        error_message = traceback.format_exc()
        log_message(f"--- SCRIPT CRASHED ---\n{error_message}")
