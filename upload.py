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
        
    # --- Calculations ---
    percent = uploaded / total
    elapsed_time = time.monotonic() - start_time
    speed = uploaded / elapsed_time if elapsed_time > 0 else 0
    eta = (total - uploaded) / speed if speed > 0 else 0

    # --- Use fixed-width formatting for all text elements for stability ---
    size_str = f"{format_size(uploaded):>9s}/{format_size(total):<9s}"
    speed_str = f"{format_size(speed)+'/s':<11s}"
    percent_str = f"{percent:6.1%}" # e.g., " 50.1%"
    eta_str = f"{int(eta // 60):>3}m {int(eta % 60):02}s" # e.g., "  6m 02s"
    
    # --- Define characters for the bar style ---
    filled_char = '█'
    empty_char = '⣀'
    
    # --- Building the Bar ---
    static_text = f"Uploading... || {percent_str} {size_str} @ {speed_str} ETA: {eta_str}"
    bar_length = terminal_width - len(static_text) - 1
    bar_length = max(10, bar_length)
    
    filled_length = int(bar_length * percent)
    
    bar = Ansi.GREEN + filled_char * filled_length + Ansi.RESET + empty_char * (bar_length - filled_length)
    
    # --- Assembling the full detailed line with stable components ---
    line = (f"{Ansi.YELLOW}Uploading... {Ansi.RESET}"
            f"|{bar}| {percent_str} "
            f"{Ansi.CYAN}{size_str}{Ansi.RESET} @ "
            f"{Ansi.GREEN}{speed_str}{Ansi.RESET} "
            f"ETA: {eta_str}")
    
    # --- Printing ---
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

    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        return None

    fields = {'user': user_hash}
    files = {'file': file_path}
    
    boundary = f'----------{uuid4().hex}'
    content_type = f'multipart/form-data; boundary={boundary}'
    
    file_size = os.path.getsize(file_path)
    start_time = time.monotonic()

    # --- FRAME RATE LIMITER for smooth UI without slowing the upload ---
    last_update_time = 0
    # Update the visual bar at most 20 times per second (1/20 = 0.05s)
    update_interval = 0.05 

    def progress_callback(uploaded, total):
        nonlocal last_update_time
        current_time = time.monotonic()
        # Check if enough time has passed since the last UI update
        if current_time - last_update_time > update_interval:
            display_progress(uploaded, total, start_time)
            last_update_time = current_time
        
    body_generator = multipart_body_generator(fields, files, boundary, progress_callback)
    content_length = calculate_total_size(fields, files, boundary)
    
    # Draw initial bar at 0%
    display_progress(0, file_size, start_time)

    req = request.Request(upload_server_url, data=body_generator)
    req.add_header('Content-Type', content_type)
    req.add_header('Content-Length', str(content_length))

    try:
        with request.urlopen(req) as response:
            # Draw final bar at 100% to ensure it completes
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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {os.path.basename(__file__)} <path_to_file> [user_hash]")
        sys.exit(1)

    file_to_upload = sys.argv[1]
    user_hash_arg = sys.argv[2] if len(sys.argv) > 2 else ""

    download_link = upload_file(file_to_upload, user_hash_arg)

    if download_link:
        print()
        display_success_message(download_link)
