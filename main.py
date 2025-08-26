import fitz  # PyMuPDF
import os
import time
import sys
from openai import OpenAI
from replit.object_storage import Client

# --- Configuration ---
# 1. Name of the PDF you want to translate (now passed as command-line argument)
# input_pdf = "louiseeliasbergs1996bowe.pdf"
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

    # Create output directory name based on input filename
    base_name = os.path.splitext(input_path)[0]  # Remove extension
    output_dir = base_name
    
    print("🚀 Starting translation process with bold detection...")
    print(f"📄 Each page will be saved as a separate PDF in Object Storage under '{output_dir}/' folder")

    for page_num, page in enumerate(original_doc):
        print(f"    -> Processing page {page_num + 1}/{len(original_doc)}...")
        
        # Create a new document for this single page
        single_page_doc = fitz.open()
        new_page = single_page_doc.new_page(width=page.rect.width, height=page.rect.height)
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
        
        print(f"      - Total text segments found: {len(text_segments)}")
        
        if not text_segments:
            print(f"      - No text segments found on this page, creating empty translated page...")
            # Still need to save the page even if it has no text to translate
            try:
                page_filename = f"page_{page_num + 1:03d}.pdf"
                storage_page_path = f"{output_dir}/{page_filename}"
                
                # Save to a temporary bytes buffer instead of local file
                import io
                pdf_bytes = io.BytesIO()
                single_page_doc.save(pdf_bytes, garbage=4, deflate=True, clean=True)
                pdf_bytes.seek(0)
                
                # Upload directly to Object Storage
                storage_client.upload_from_bytes(storage_page_path, pdf_bytes.getvalue())
                print(f"      ✅ Saved to Object Storage: {storage_page_path}")
                    
            except Exception as e:
                print(f"      ❌ Error saving empty page {page_num + 1}: {e}")
            finally:
                single_page_doc.close()
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
                
                # Step 1: Draw a white/light background rectangle to cover the original text
                # Use minimal expansion to avoid overlapping with adjacent text
                cover_rect = fitz.Rect(
                    segment['rect'].x0 - 0.5,  # Minimal expand left
                    segment['rect'].y0,        # No vertical expansion to avoid line overlap
                    segment['rect'].x1 + 0.5,  # Minimal expand right
                    segment['rect'].y1         # No vertical expansion to avoid line overlap
                )
                
                # Draw white rectangle to cover original text
                new_page.draw_rect(cover_rect, color=None, fill=(1, 1, 1))  # White fill
                
                # Step 2: Normalize color values to 0-1 range and ensure visible color
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
                
                # Ensure the color is not white or too light (which would be invisible on white background)
                if sum(normalized_color) > 2.7:  # If color is very light/white
                    normalized_color = (0, 0, 0)  # Use black instead
                    print(f"      - Changed white/light text to black for visibility")
                
                # Step 3: Insert the translated text with better font sizing
                text_inserted = False
                original_font_size = segment['size']
                
                # Start with larger font sizes and work down - be less aggressive with shrinking
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
                        
                        if result > 0:  # Successful insertion
                            if font_scale != 1.0:
                                print(f"      - Text inserted with {int(font_scale*100)}% font size for segment {i}")
                            text_inserted = True
                            break
                        elif result == 0:  # Text fits exactly
                            text_inserted = True
                            break
                            
                    except Exception as text_error:
                        continue  # Try next font scale
                
                # If textbox insertion failed, try simple text insertion with better sizing
                if not text_inserted:
                    try:
                        # Calculate position for simple text insertion
                        text_x = segment['rect'].x0
                        text_y = segment['rect'].y0 + (segment['rect'].height * 0.8)  # Position text better within rect
                        
                        new_page.insert_text(
                            (text_x, text_y),
                            translated_text,
                            fontname=font_name_for_pdf,
                            fontfile=font_file_to_use,
                            fontsize=original_font_size * 0.8,  # Less aggressive shrinking for fallback
                            color=normalized_color
                        )
                        print(f"      - Used fallback text insertion for segment {i}")
                        text_inserted = True
                    except Exception as fallback_error:
                        print(f"      - All text insertion methods failed for segment {i}: {fallback_error}")
                        print(f"        Original: '{segment['text'][:30]}...'")
                        print(f"        Translation: '{translated_text[:30]}...'")
                
                if text_inserted:
                    if segment['is_bold']:
                        print(f"      - Successfully inserted BOLD text for segment {i}")
                    else:
                        print(f"      - Successfully inserted text for segment {i}")
                else:
                    print(f"      - Failed to insert text for segment {i} - skipping")
            except Exception as e:
                print(f"      - Could not process segment {i}: '{segment['text'][:30]}...'. Error: {e}")
        
        # Save this single page as its own PDF directly to Object Storage
        try:
            page_filename = f"page_{page_num + 1:03d}.pdf"
            storage_page_path = f"{output_dir}/{page_filename}"
            
            # Save to a temporary bytes buffer instead of local file
            import io
            pdf_bytes = io.BytesIO()
            single_page_doc.save(pdf_bytes, garbage=4, deflate=True, clean=True)
            pdf_bytes.seek(0)
            
            # Upload directly to Object Storage
            storage_client.upload_from_bytes(storage_page_path, pdf_bytes.getvalue())
            print(f"      ✅ Saved to Object Storage: {storage_page_path}")
                
        except Exception as e:
            print(f"      ❌ Error saving page {page_num + 1}: {e}")
        finally:
            single_page_doc.close()
    print(f"✅ Translation complete! All pages saved individually in Object Storage under '{output_dir}/' folder")
    print(f"📁 Check Object Storage to see pages 1-{len(original_doc)} in the '{output_dir}' folder")
    original_doc.close()

# --- Run the script ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Get the input PDF filename from the first command-line argument
        input_pdf_from_arg = sys.argv[1]
        translate_pdf_with_bolding(input_pdf_from_arg, output_pdf, font_path_regular, font_path_bold)
    else:
        # Print an error if no file is provided, which helps with debugging
        print("ERROR: No input PDF file was specified as a command-line argument.")