import os
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def log_message(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)

def get_align_padding(current_pos, alignment=16):
    return (alignment - (current_pos % alignment)) % alignment

def extract_surgical():
    filepath = filedialog.askopenfilename(title="Select .all file to extract")
    if not filepath: return
    
    try:
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            f.seek(0)
            
            # Check for XPR0 (Xbox Resource) files - these are not text archives
            if magic == b'XPR0':
                log_message(f"Skipping {os.path.basename(filepath)}: This is an XPR0 Texture/Font container, not a text archive.")
                messagebox.showwarning("Incompatible File", "This is an XPR0 resource file (Textures/Fonts).\n\nThis tool only supports Alias .ALL text/data archives.")
                return

            main_header = f.read(16)
            file_count = struct.unpack('<I', main_header[:4])[0]
            
            # Safety check for corrupted or non-standard .all files
            if file_count > 5000 or file_count == 0:
                log_message("Error: Invalid file count. This might not be a supported .all archive.")
                return

            log_message(f"--- Extracting {file_count} files ---")
            
            file_entries = []
            for i in range(file_count):
                entry_data = f.read(72)
                if len(entry_data) < 72: break # Prevent buffer error
                
                name = entry_data[:64].split(b'\x00')[0].decode('ascii', errors='ignore')
                size = struct.unpack('<Q', entry_data[64:72])[0]
                file_entries.append({'name': name, 'size': size})

            # Skip header padding
            f.seek(get_align_padding(f.tell()), 1)

            output_dir = filepath + "_extracted"
            os.makedirs(output_dir, exist_ok=True)
            
            for entry in file_entries:
                if entry['size'] == 0: continue
                
                data = f.read(entry['size'])
                f.seek(get_align_padding(f.tell()), 1)
                
                out_path = os.path.join(output_dir, entry['name'])
                
                is_text = False
                bom_pos = -1
                if entry['name'].lower().endswith('.txt'):
                    bom_pos = data.find(b'\xff\xfe', 0, 128) # Larger scan for prototype buffers
                    if bom_pos != -1:
                        is_text = True
                
                if is_text:
                    text_payload = data[bom_pos:].rstrip(b'\x00')
                    text_content = text_payload.decode('utf-16le', errors='ignore')
                    with open(out_path, 'w', encoding='utf-8', newline='') as t_file:
                        t_file.write(text_content)
                    log_message(f"Extracted Text: {entry['name']}")
                else:
                    with open(out_path, 'wb') as b_file:
                        b_file.write(data)
                    log_message(f"Extracted Binary: {entry['name']}")

        messagebox.showinfo("Success", "Extraction complete!")
        
    except Exception as e:
        log_message(f"Error: {e}")

def repack_surgical():
    original_filepath = filedialog.askopenfilename(title="Select ORIGINAL .all file")
    if not original_filepath: return
    
    extracted_dir = filedialog.askdirectory(title="Select folder with edited files")
    if not extracted_dir: return
    
    output_filepath = filedialog.asksaveasfilename(title="Save REPACKED file as...", defaultextension=".all")
    if not output_filepath: return

    try:
        with open(original_filepath, 'rb') as f:
            header_start = f.read(16)
            file_count = struct.unpack('<I', header_start[:4])[0]
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
                        text = t_file.read().lstrip('\ufeff')
                    text = text.replace('\r\n', '\n').replace('\n', '\r\n')
                    encoded_data = b'\xff\xfe' + text.encode('utf-16le')
                else:
                    with open(file_path, 'rb') as b_file:
                        encoded_data = b_file.read()
                
                padding_size = get_align_padding(len(encoded_data))
                encoded_data += b'\x00' * padding_size
                
                new_data_blocks.append(encoded_data)
                new_sizes.append(len(encoded_data))
                log_message(f"Packed: {name}")
            else:
                new_data_blocks.append(b"")
                new_sizes.append(0)

        with open(output_filepath, 'wb') as out:
            out.write(header_start)
            for i in range(file_count):
                out.write(filenames[i].encode('ascii').ljust(64, b'\x00'))
                out.write(struct.pack('<Q', new_sizes[i]))
            
            out.write(b'\x00' * get_align_padding(out.tell()))
            for block in new_data_blocks:
                out.write(block)

        messagebox.showinfo("Success", "Repack complete!")

    except Exception as e:
        log_message(f"Error: {e}")

# --- GUI ---
root = tk.Tk()
root.title("Alias Text Tool")
root.geometry("600x620")
root.configure(bg="#f0f0f0")

img_path = "AliasTextTool_GUI.png"
if os.path.exists(img_path):
    try:
        header_img = tk.PhotoImage(file=img_path)
        tk.Label(root, image=header_img, bg="#f0f0f0").pack(pady=10)
    except: pass

btn_frame = tk.Frame(root, bg="#f0f0f0")
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="Extract .all File", command=extract_surgical, width=20, height=2, 
          bg="#3498db", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=15)

tk.Button(btn_frame, text="Repack .all File", command=repack_surgical, width=20, height=2, 
          bg="#27ae60", fg="white", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=15)

# Log Section
log_box = scrolledtext.ScrolledText(root, height=15, font=("Consolas", 9), bg="#ffffff")
log_box.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

log_message("Note: Don't forget to have AliasTextTool_GUI.png in the same folder as this tool.")
root.mainloop()
