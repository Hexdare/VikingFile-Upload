import sys
import os
import json
import mimetypes
import time
from urllib import request, error
from uuid import uuid4

# --- UI Enhancements: ANSI Colors and Styles ---
class Ansi:
    """A helper class for adding color and style to terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Colors
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    WHITE = "\033[97m"
    
    # Box Drawing
    H = "═"  # Horizontal line
    V = "║"  # Vertical line
    TL = "╔" # Top-left corner
    TR = "╗" # Top-right corner
    BL = "╚" # Bottom-left corner
    BR = "╝" # Bottom-right corner

def format_size(size_in_bytes):
    """Formats a size in bytes to a human-readable string (KB, MB, GB)."""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024**2:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024**3:
        return f"{size_in_bytes / 1024**2:.1f} MB"
    else:
        return f"{size_in_bytes / 1024**3:.1f} GB"

def display_progress(uploaded, total, start_time):
    """Displays a smooth, informative, and stable progress bar."""
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        terminal_width = 80
        
    if total == 0:
        return
        
    percent = uploaded / total
    elapsed_time = time.monotonic() - start_time
    speed = uploaded / elapsed_time if elapsed_time > 0 else 0
    eta = (total - uploaded) / speed if speed > 0 else 0

    size_str = f"{format_size(uploaded):>9s}/{format_size(total):<9s}"
    speed_str = f"{format_size(speed)+'/s':<11s}"
    percent_str = f"{percent:6.1%}"
    eta_str = f"{int(eta // 60):>3}m {int(eta % 60):02}s"
    
    filled_char = '█'
    empty_char = '⣀'
    
    static_text = f"Uploading... || {percent_str} {size_str} @ {speed_str} ETA: {eta_str}"
    bar_length = terminal_width - len(static_text) - 1
    bar_length = max(10, bar_length)
    
    filled_length = int(bar_length * percent)
    
    bar = Ansi.GREEN + filled_char * filled_length + Ansi.RESET + empty_char * (bar_length - filled_length)
    
    line = (f"{Ansi.YELLOW}Uploading... {Ansi.RESET}"
            f"|{bar}| {percent_str} "
            f"{Ansi.CYAN}{size_str}{Ansi.RESET} @ "
            f"{Ansi.GREEN}{speed_str}{Ansi.RESET} "
            f"ETA: {eta_str}")
    
    sys.stdout.write(f"\r{line.ljust(terminal_width)}")
    sys.stdout.flush()


def display_success_message(link):
    """Displays the final download link in a formatted box."""
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80
        
    print(f"{Ansi.GREEN}{Ansi.TL}{Ansi.H * (width - 2)}{Ansi.TR}{Ansi.RESET}")
    success_msg = "File Uploaded Successfully!"
    print(f"{Ansi.GREEN}{Ansi.V}{Ansi.RESET} {success_msg.center(width - 4)} {Ansi.GREEN}{Ansi.V}{Ansi.RESET}")
    print(f"{Ansi.GREEN}{Ansi.V}{Ansi.H * (width - 2)}{Ansi.V}{Ansi.RESET}")
    link_text = f" {Ansi.BOLD}Link:{Ansi.RESET} {Ansi.CYAN}{link}{Ansi.RESET}"
    ansi_offset = len(Ansi.BOLD) + len(Ansi.RESET) + len(Ansi.CYAN) + len(Ansi.RESET)
    padding = width - 4 - (len(link_text) - ansi_offset)
    print(f"{Ansi.GREEN}{Ansi.V}{link_text}{' ' * padding}{Ansi.GREEN}{Ansi.V}{Ansi.RESET}")
    print(f"{Ansi.GREEN}{Ansi.BL}{Ansi.H * (width - 2)}{Ansi.BR}{Ansi.RESET}")


def get_upload_server():
    """Gets the upload server URL using only built-in libraries."""
    url = 'https://vikingfile.com/api/get-server'
    try:
        with request.urlopen(url) as response:
            if response.status != 200:
                print(f"Error: Failed to get upload server (Status: {response.status})")
                return
            data = json.load(response)
            return data.get('server')
    except error.URLError as e:
        print(f"Error connecting to VikingFile API: {e.reason}")
        return None

def calculate_total_size(fields, files, boundary):
    """Calculates the total size of the multipart/form-data body."""
    total_size = 0
    for name, value in fields.items():
        total_size += len(f'--{boundary}\r\n'.encode('utf-8'))
        total_size += len(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode('utf-8'))
        total_size += len(f'{value}\r\n'.encode('utf-8'))
    for name, filepath in files.items():
        filename = os.path.basename(filepath)
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        total_size += len(f'--{boundary}\r\n'.encode('utf-8'))
        total_size += len(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode('utf-8'))
        total_size += len(f'Content-Type: {mimetype}\r\n\r\n'.encode('utf-8'))
        total_size += os.path.getsize(filepath)
        total_size += len('\r\n'.encode('utf-8'))
    total_size += len(f'--{boundary}--\r\n'.encode('utf-8'))
    return total_size

def multipart_body_generator(fields, files, boundary, progress_callback=None):
    """Yields the multipart/form-data body chunk by chunk."""
    encoder = 'utf-8'
    total_uploaded = 0
    for name, value in fields.items():
        header_part = f'--{boundary}\r\n' + f'Content-Disposition: form-data; name="{name}"\r\n\r\n' + f'{value}\r\n'
        yield header_part.encode(encoder)
    for name, filepath in files.items():
        filename = os.path.basename(filepath)
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        header_part = f'--{boundary}\r\n' + f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n' + f'Content-Type: {mimetype}\r\n\r\n'
        yield header_part.encode(encoder)
        file_size = os.path.getsize(filepath)
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(16384)
                if not chunk:
                    break
                yield chunk
                total_uploaded += len(chunk)
                if progress_callback:
                    progress_callback(total_uploaded, file_size)
        yield '\r\n'.encode(encoder)
    yield f'--{boundary}--\r\n'.encode(encoder)

def upload_file(file_path, user_hash=""):
    """Uploads a file to VikingFile and returns the download link."""
    upload_server_url = get_upload_server()
    if not upload_server_url:
        return None

    # The file path existence is checked here, covering both interactive and argument-based input.
    if not os.path.exists(file_path):
        print(f"\n{Ansi.YELLOW}Error: File not found at '{file_path}'{Ansi.RESET}")
        return None

    fields = {'user': user_hash}
    files = {'file': file_path}
    
    boundary = f'----------{uuid4().hex}'
    content_type = f'multipart/form-data; boundary={boundary}'
    
    file_size = os.path.getsize(file_path)
    start_time = time.monotonic()

    last_update_time = 0
    update_interval = 0.05 

    def progress_callback(uploaded, total):
        nonlocal last_update_time
        current_time = time.monotonic()
        if current_time - last_update_time > update_interval:
            display_progress(uploaded, total, start_time)
            last_update_time = current_time
        
    body_generator = multipart_body_generator(fields, files, boundary, progress_callback)
    content_length = calculate_total_size(fields, files, boundary)
    
    display_progress(0, file_size, start_time)

    req = request.Request(upload_server_url, data=body_generator)
    req.add_header('Content-Type', content_type)
    req.add_header('Content-Length', str(content_length))

    try:
        with request.urlopen(req) as response:
            display_progress(file_size, file_size, start_time)
            print() 
            if response.status == 200:
                upload_info = json.load(response)
                return upload_info.get('url')
            else:
                print(f"Error uploading file. Server responded with status: {response.status}")
                print(response.read().decode('utf-8'))
                return None
    except error.HTTPError as e:
        print(f"\nHTTP Error during upload: {e.code} {e.reason}")
        print("Response body:", e.read().decode('utf-8', 'ignore'))
        return None
    except error.URLError as e:
        print(f"\nURL Error during upload: {e.reason}")
        return None

# --- MODIFIED SECTION: Handles both command-line arguments and interactive input ---
if __name__ == "__main__":
    
    file_to_upload = ""
    user_hash_arg = ""

    # Mode 1: Check for command-line arguments (for scripting and non-interactive use)
    if len(sys.argv) > 1:
        file_to_upload = sys.argv[1]
        if len(sys.argv) > 2:
            user_hash_arg = sys.argv[2]
            
    # Mode 2: If no arguments were given, switch to interactive mode
    else:
        try:
            prompt_arrow = f"{Ansi.CYAN}▶{Ansi.RESET}"
            file_to_upload = input(f"{prompt_arrow} Enter the path to the file: ")
            user_hash_arg = input(f"{prompt_arrow} Enter user hash (optional, press Enter to skip): ")
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully during input
            print("\n\nUpload cancelled by user.")
            sys.exit(0)

    # Validate that we have a file path before proceeding
    if not file_to_upload.strip():
        print(f"\n{Ansi.YELLOW}Error: No file path provided. Aborting.{Ansi.RESET}")
        sys.exit(1)

    # Call the main upload function with the collected details
    download_link = upload_file(file_to_upload.strip(), user_hash_arg.strip())

    if download_link:
        print()
        display_success_message(download_link)

