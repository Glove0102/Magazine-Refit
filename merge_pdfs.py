
import fitz  # PyMuPDF
import os
from replit.object_storage import Client

def merge_pdfs_from_folder(folder_path):
    """
    Merges all PDF files from a specified folder in Object Storage into a single PDF.
    
    Args:
        folder_path (str): The folder path in Object Storage (e.g., "0723.pdf")
    """
    # Initialize Object Storage client
    storage_client = Client()
    
    print(f"🔍 Looking for PDF files in Object Storage folder: '{folder_path}'")
    
    try:
        # List all objects in the bucket
        all_objects = storage_client.list()
        
        # Filter objects that are in our target folder and are PDF files
        pdf_objects = []
        for obj in all_objects:
            if obj.name.startswith(f"{folder_path}/") and obj.name.endswith(".pdf"):
                pdf_objects.append(obj)
        
        if not pdf_objects:
            print(f"❌ No PDF files found in folder '{folder_path}'")
            return
        
        # Sort the PDF objects by name to ensure correct order (page_001.pdf, page_002.pdf, etc.)
        pdf_objects.sort(key=lambda x: x.name)
        
        print(f"📄 Found {len(pdf_objects)} PDF files to merge:")
        for obj in pdf_objects:
            print(f"   - {obj.name}")
        
        # Create a new PDF document for the merged result
        merged_doc = fitz.open()
        
        print("🔄 Starting merge process...")
        
        # Process each PDF file
        for i, pdf_obj in enumerate(pdf_objects):
            try:
                print(f"   -> Processing {pdf_obj.name} ({i+1}/{len(pdf_objects)})")
                
                # Download the PDF from Object Storage
                pdf_data = storage_client.download_as_bytes(pdf_obj.name)
                
                # Open the PDF
                current_doc = fitz.open(stream=pdf_data, filetype="pdf")
                
                # Get page count before closing
                page_count = len(current_doc)
                
                # Add all pages from this PDF to the merged document
                for page_num in range(page_count):
                    merged_doc.insert_pdf(current_doc, from_page=page_num, to_page=page_num)
                
                print(f"      ✅ Added {page_count} page(s) from {pdf_obj.name}")
                
                # Close the current document after processing
                current_doc.close()
                
            except Exception as e:
                print(f"      ❌ Error processing {pdf_obj.name}: {e}")
                # Make sure to close the document even if there was an error
                try:
                    if 'current_doc' in locals():
                        current_doc.close()
                except:
                    pass
                continue
        
        if len(merged_doc) == 0:
            print("❌ No pages were successfully merged. Aborting.")
            merged_doc.close()
            return
        
        print(f"📋 Merged document contains {len(merged_doc)} total pages")
        
        # Save the merged PDF to a temporary bytes buffer
        import io
        merged_pdf_bytes = io.BytesIO()
        merged_doc.save(merged_pdf_bytes, garbage=4, deflate=True, clean=True)
        merged_pdf_bytes.seek(0)
        
        # Upload the merged PDF back to Object Storage in the same folder
        merged_filename = f"{folder_path}_merged.pdf"
        storage_path = f"{folder_path}/{merged_filename}"
        
        storage_client.upload_from_bytes(storage_path, merged_pdf_bytes.getvalue())
        
        print(f"✅ Successfully merged {len(pdf_objects)} PDF files!")
        print(f"📁 Merged PDF saved as: {storage_path}")
        print(f"📊 Total pages in merged PDF: {len(merged_doc)}")
        
        merged_doc.close()
        
    except Exception as e:
        print(f"❌ Error during merge process: {e}")

def list_available_folders():
    """
    Lists available folders in Object Storage that contain PDF files.
    """
    storage_client = Client()
    
    try:
        all_objects = storage_client.list()
        folders = set()
        
        for obj in all_objects:
            if "/" in obj.name and obj.name.endswith(".pdf"):
                folder = obj.name.split("/")[0]
                folders.add(folder)
        
        if folders:
            print("📂 Available folders with PDF files:")
            for folder in sorted(folders):
                print(f"   - {folder}")
            return sorted(folders)
        else:
            print("❌ No folders with PDF files found in Object Storage")
            return []
            
    except Exception as e:
        print(f"❌ Error listing folders: {e}")
        return []

# --- Configuration ---
# Set the folder path you want to merge PDFs from
# Example: "0723.pdf" (this would merge all PDFs in the 0723.pdf folder)
target_folder = "0723.pdf"

# --- Run the script ---
if __name__ == "__main__":
    print("🔧 PDF Merger for Object Storage")
    print("=" * 50)
    
    # First, show available folders
    print("Available folders:")
    available_folders = list_available_folders()
    
    print("\n" + "=" * 50)
    
    if target_folder:
        print(f"🎯 Target folder: {target_folder}")
        merge_pdfs_from_folder(target_folder)
    else:
        print("❌ Please set the 'target_folder' variable in the script")
        print("Example: target_folder = '0723.pdf'")
