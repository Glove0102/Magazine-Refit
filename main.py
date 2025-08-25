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

def translate_batch_with_openai(text_segments):
    """
    Translates multiple text segments in one API call using JSON format.
    """
    try:
        # Create a list of texts with IDs for mapping back
        texts_to_translate = []
        for i, segment in enumerate(text_segments):
            if len(segment['text'].strip()) >= 2:  # Only include meaningful text
                texts_to_translate.append({
                    "id": i,
                    "text": segment['text']
                })
        
        if not texts_to_translate:
            return {}
        
        # Create the prompt for batch translation
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
            max_completion_tokens=19000,  # Increased significantly for large batches
            response_format={"type": "json_object"}
        )
        
        import json
        response_content = response.choices[0].message.content
        
        # Debug: print response length and preview
        print(f"      - API response length: {len(response_content) if response_content else 0}")
        if not response_content:
            print("      - Empty response from OpenAI API - likely token limit exceeded")
            return {}
            
        if len(response_content) < 100:
            print(f"      - Short response content: {response_content}")
        
        translations = json.loads(response_content)
        print(f"      - Successfully parsed {len(translations)} translations")
        return translations
        
    except json.JSONDecodeError as e:
        print(f"      - JSON decode error: {e}")
        print(f"      - Response content preview: {response.choices[0].message.content[:200] if response.choices[0].message.content else 'None'}")
        return {}
    except Exception as e:
        print(f"      - Batch OpenAI translation failed: {e}")
        return {}

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

        # Step 1: Collect all text segments from the page
        text_segments = []
        text_blocks = page.get_text("dict")["blocks"]
        
        for block in text_blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        original_text = span["text"].strip()
                        if original_text and len(original_text.strip()) >= 2:
                            # Store all the span information we need
                            text_segments.append({
                                'text': original_text,
                                'rect': fitz.Rect(span["bbox"]),
                                'is_bold': span['flags'] & 16,
                                'color': span["color"],
                                'size': span["size"]
                            })
        
        if not text_segments:
            continue
            
        print(f"      - Found {len(text_segments)} text segments, translating in batch...")
        
        # Step 2: Translate text segments in batches (limit batch size to prevent token overflow)
        batch_size = 50  # Limit batch size to prevent token issues
        all_translations = {}
        
        for i in range(0, len(text_segments), batch_size):
            batch = text_segments[i:i+batch_size]
            print(f"      - Translating batch {i//batch_size + 1} ({len(batch)} segments)...")
            batch_translations = translate_batch_with_openai(batch)
            
            # Adjust indices for the overall segment list
            for key, value in batch_translations.items():
                all_translations[str(int(key) + i)] = value
        
        translations = all_translations
        
        # Step 3: Apply translations to the page
        for i, segment in enumerate(text_segments):
            try:
                # Get the translation for this segment
                translated_text = translations.get(str(i))
                if not translated_text:
                    print(f"      - No translation found for segment {i}: '{segment['text'][:30]}...'")
                    continue
                
                # Choose the font based on boldness
                if segment['is_bold']:
                    font_file_to_use = bold_font
                    font_name_for_pdf = "china-font-bold"
                else:
                    font_file_to_use = regular_font
                    font_name_for_pdf = "china-font-regular"
                
                # Cover the original text
                new_page.draw_rect(segment['rect'], color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
                
                # Normalize color values to 0-1 range
                original_color = segment['color']
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
                
                # Insert the translated text
                new_page.insert_textbox(
                    segment['rect'],
                    translated_text,
                    fontname=font_name_for_pdf,
                    fontfile=font_file_to_use,
                    fontsize=segment['size'],
                    color=normalized_color,
                    align=fitz.TEXT_ALIGN_LEFT
                )
            except Exception as e:
                print(f"      - Could not process segment {i}: '{segment['text'][:30]}...'. Error: {e}")
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