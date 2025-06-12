import sys
import os
import json
import mimetypes
from urllib import request, error
from uuid import uuid4

def get_upload_server():
    """Gets the upload server URL using only built-in libraries."""
    url = 'https://vikingfile.com/api/get-server'
    try:
        with request.urlopen(url) as response:
            if response.status != 200:
                print(f"Error: Failed to get upload server (Status: {response.status})")
                return None
            data = json.load(response)
            return data.get('server')
    except error.URLError as e:
        print(f"Error connecting to VikingFile API: {e.reason}")
        return None

def create_multipart_form(fields, files):
    """
    Creates a multipart/form-data body and the corresponding Content-Type header.
    """
    boundary = f'----------{uuid4().hex}'
    content_type = f'multipart/form-data; boundary={boundary}'
    
    body = bytearray()
    
    # Add form fields
    for name, value in fields.items():
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode('utf-8'))
        body.extend(f'{value}\r\n'.encode('utf-8'))
        
    # Add files
    for name, filepath in files.items():
        filename = os.path.basename(filepath)
        # Guess the MIME type or default to octet-stream
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode('utf-8'))
        body.extend(f'Content-Type: {mimetype}\r\n\r\n'.encode('utf-8'))
        
        with open(filepath, 'rb') as f:
            body.extend(f.read())
        
        body.extend('\r\n'.encode('utf-8'))
        
    # Add final boundary
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    
    return body, content_type

def upload_file(file_path, user_hash=""):
    """Uploads a file to VikingFile and returns the download link."""
    upload_server_url = get_upload_server()
    if not upload_server_url:
        return None

    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        return None

    print("Preparing to upload...")
    fields = {'user': user_hash}
    files = {'file': file_path}
    
    # Manually create the multipart request body and headers
    body, content_type = create_multipart_form(fields, files)
    
    req = request.Request(upload_server_url, data=body)
    req.add_header('Content-Type', content_type)
    req.add_header('Content-Length', str(len(body)))

    print("Uploading file...")
    try:
        with request.urlopen(req) as response:
            if response.status == 200:
                upload_info = json.load(response)
                return upload_info.get('url')
            else:
                print(f"Error uploading file. Server responded with status: {response.status}")
                print(response.read().decode('utf-8'))
                return None
    except error.HTTPError as e:
        print(f"HTTP Error during upload: {e.code} {e.reason}")
        print("Response body:", e.read().decode('utf-8', 'ignore'))
        return None
    except error.URLError as e:
        print(f"URL Error during upload: {e.reason}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_vikingfile_no_deps.py <path_to_file> [user_hash]")
        sys.exit(1)

    file_to_upload = sys.argv[1]
    user_hash_arg = sys.argv[2] if len(sys.argv) > 2 else ""

    download_link = upload_file(file_to_upload, user_hash_arg)

    if download_link:
        print("\nFile uploaded successfully!")
        print(f"Download link: {download_link}")

