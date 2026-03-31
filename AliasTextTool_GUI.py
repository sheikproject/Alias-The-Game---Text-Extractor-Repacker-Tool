import os
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def log_message(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)

def align_to_16(f):
    """Moves the file pointer to the next 16-byte boundary."""
    current_pos = f.tell()
    padding = (16 - (current_pos % 16)) % 16
    if padding > 0:
        f.seek(padding, 1)

def extract_surgical():
    filepath = filedialog.askopenfilename(title="Select .all file to extract")
    if not filepath: return
    
    try:
        with open(filepath, 'rb') as f:
            main_header = f.read(16)
            file_count = struct.unpack('<I', main_header[:4])[0]
            
            log_message(f"--- Extracting {file_count} files ---")
            
            file_entries = []
            for i in range(file_count):
                entry_data = f.read(72)
                name = entry_data[:64].split(b'\x00')[0].decode('ascii', errors='ignore')
                size = struct.unpack('<Q', entry_data[64:72])[0]
                file_entries.append({'name': name, 'size': size})

            align_to_16(f)

            output_dir = filepath + "_extracted"
            os.makedirs(output_dir, exist_ok=True)
            
            for entry in file_entries:
                if entry['size'] == 0: continue
                
                data = f.read(entry['size'])
                # Move to next 16-byte boundary for the next file
                align_to_16(f)
                
                out_path = os.path.join(output_dir, entry['name'])
                
                # Logic to detect and clean text files
                if entry['name'].lower().endswith('.txt') and data.startswith(b'\xff\xfe'):
                    data = data.rstrip(b'\x00')
                    text_content = data.decode('utf-16le', errors='ignore')
                    with open(out_path, 'w', encoding='utf-8', newline='') as t_file:
                        t_file.write(text_content)
                    log_message(f"Extracted: {entry['name']}")
                else:
                    with open(out_path, 'wb') as b_file:
                        b_file.write(data)
                    log_message(f"Extracted (Binary): {entry['name']}")

        messagebox.showinfo("Success", f"Extraction complete!\nFiles saved to: {output_dir}")
        
    except Exception as e:
        log_message(f"Error: {e}")

def repack_surgical():
    original_filepath = filedialog.askopenfilename(title="1. Select ORIGINAL .all file")
    if not original_filepath: return
    
    extracted_dir = filedialog.askdirectory(title="2. Select folder with edited files")
    if not extracted_dir: return
    
    output_filepath = filedialog.asksaveasfilename(title="3. Save REPACKED file as...", defaultextension=".all")
    if not output_filepath: return

    try:
        with open(original_filepath, 'rb') as f:
            main_header = f.read(16)
            file_count = struct.unpack('<I', main_header[:4])[0]
            filenames = []
            for _ in range(file_count):
                name = f.read(64).split(b'\x00')[0].decode('ascii', errors='ignore')
                f.seek(8, 1)
                filenames.append(name)

        new_data_blocks = []
        new_sizes = []
        
        for name in filenames:
            file_path = os.path.join(extracted_dir, name)
            if os.path.exists(file_path):
                if name.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8', newline='') as t_file:
                        text = t_file.read()
                    
                    text = text.lstrip('\ufeff') # Prevent Double BOM (ÿþÿþ)
                    text = text.replace('\r\n', '\n').replace('\n', '\r\n')
                    encoded_data = b'\xff\xfe' + text.encode('utf-16le')
                else:
                    with open(file_path, 'rb') as b_file:
                        encoded_data = b_file.read()
                
                # Apply 16-byte padding to the data itself
                remainder = len(encoded_data) % 16
                if remainder > 0:
                    encoded_data += b'\x00' * (16 - remainder)
                
                new_data_blocks.append(encoded_data)
                new_sizes.append(len(encoded_data))
                log_message(f"Packed: {name} ({len(encoded_data)} bytes)")
            else:
                new_data_blocks.append(b"")
                new_sizes.append(0)

        with open(output_filepath, 'wb') as out:
            out.write(main_header)
            for i in range(file_count):
                out.write(filenames[i].encode('ascii').ljust(64, b'\x00'))
                out.write(struct.pack('<Q', new_sizes[i]))
            
            # Align before writing the first data block
            current_pos = out.tell()
            padding = (16 - (current_pos % 16)) % 16
            out.write(b'\x00' * padding)
            
            for block in new_data_blocks:
                out.write(block)

        messagebox.showinfo("Success", "Repack complete!")

    except Exception as e:
        log_message(f"Error: {e}")

# --- GUI Setup ---
root = tk.Tk()
root.title("Alias Text Tool")
root.geometry("600x600")
root.configure(bg="#f0f0f0")

# Image Header Section
img_path = "AliasTextTool_GUI.png"
if os.path.exists(img_path):
    try:
        header_img = tk.PhotoImage(file=img_path)
        img_label = tk.Label(root, image=header_img, bg="#f0f0f0")
        img_label.pack(pady=10)
    except Exception as e:
        tk.Label(root, text=f"[Error loading image: {e}]", fg="red").pack()
else:
    # Placeholder if image is missing
    tk.Label(root, text=f"Put '{img_path}' in this folder to see the header.", fg="gray").pack(pady=20)

# Buttons Section
btn_frame = tk.Frame(root, pady=10, bg="#f0f0f0")
btn_frame.pack()

tk.Button(btn_frame, text="Extract .all File", command=extract_surgical, width=20, height=2, 
          bg="#3498db", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=15)

tk.Button(btn_frame, text="Repack .all File", command=repack_surgical, width=20, height=2, 
          bg="#27ae60", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=15)

# Log Section
log_box = scrolledtext.ScrolledText(root, height=15, font=("Consolas", 9), bg="#ffffff")
log_box.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

log_message("Note: Don't forget to have AliasTextTool_GUI.png in the same folder as this tool.")

root.mainloop()
