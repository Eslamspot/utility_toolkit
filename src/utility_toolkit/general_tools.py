import csv
import datetime
import gzip
import hashlib
import io
import json
import platform
import re
import shlex
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List
from typing import Tuple, Optional

import magic
import requests
from PIL import Image
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet

from . import log


# Function to add a timeout to a function
class TimeoutException(Exception):
    pass


def timeout(seconds):
    def decorator(func):
        import threading
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.start()
            thread.join(seconds)
            if thread.is_alive():
                raise TimeoutException(f"Function '{func.__name__}' timed out after {seconds} seconds")
            if exception[0]:
                raise exception[0]
            return result[0]

        return wrapper

    return decorator


@log.log_decorator()
def write_list_to_csv_file(data: list, filename: str or Path) -> None:
    """
    Write a list of lists to a CSV file.

    Args:
        data (list): A list of lists containing the data to be written.
        filename (str or Path): The path to the output CSV file.

    Returns:
        None

    Example:
    data = [['Name', 'Age'], ['Alice', 30], ['Bob', 25]]
    write_list_to_csv_file(data, 'people.csv')
    """
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(data)


@log.log_decorator()
def write_dict_to_text_file(dictionary: dict or list, file_path: str or Path) -> None:
    """
    Save a dictionary or list to a text file in JSON format.

    Args:
        dictionary (dict or list): The dictionary or list to save.
        file_path (str or Path): The path to the file where the data will be saved.

    Returns:
        None

    Example:
        data = {'name': 'Alice', 'age': 30}
        write_dict_to_text_file(data, 'data.json')
    """
    import json
    with open(file_path, 'w') as f:
        json.dump(dictionary, f, indent=4)


@log.log_decorator()
def sort_dict_by_value(d: dict):
    from collections import OrderedDict
    return dict(OrderedDict(sorted(d.items(), key=lambda x: x[1], reverse=True)))


@log.log_decorator()
def read_dict_from_text_file(file_path: str or Path) -> dict or list:
    """
    Load a dictionary or list from a text file in JSON format.

    Args:
        file_path (str or Path): The path to the file to load.

    Returns:
        dict or list: The loaded dictionary or list.

    Example:
        data = read_dict_from_text_file('data.json')
        print(data)
    """
    import json
    with open(file_path, 'r') as f:
        return json.load(f)


@log.log_decorator()
def dict_to_csv(data: list, filename: str or Path) -> None:
    """
    Convert a list of dictionaries to a CSV file.

    Args:
        data (list): A list of dictionaries to be written to CSV.
        filename (str or Path): The path to the output CSV file.

    Returns:
        None

    Example:
    data = [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
    dict_to_csv(data, 'people.csv')
    """
    with open(filename, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


@log.log_decorator()
def advanced_recognize_file_type(file_path):
    """
    Recognize the MIME type of a file using the magic package.

    Example:
    file_type = recognize_file_type('document.pdf')
    print(file_type)  # Output: application/pdf
    """
    return magic.from_file(file_path, mime=True)


def recognize_file_type(data):
    import magic
    # pipenv install python-magic
    import mimetypes

    # Convert memoryview to bytes
    if isinstance(data, memoryview):
        data = data.tobytes()

    m = magic.Magic(mime=True)

    # Recognize file type
    mime_type = m.from_buffer(data)

    if mime_type:
        file_extension = mimetypes.guess_extension(mime_type)
        if file_extension:
            return mime_type, file_extension

    # Map MIME types to a list of possible extensions
    mime_to_extensions = {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx', '.docm'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx', '.xlsm'],
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx', '.pptm'],
        'application/pdf': ['.pdf'],
        'text/plain': ['.txt'],
        'text/html': ['.html', '.htm'],
        'application/json': ['.json'],
        'application/javascript': ['.js'],
        'application/xml': ['.xml'],
        'text/css': ['.css'],
        'image/jpeg': ['.jpeg', '.jpg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'image/svg+xml': ['.svg'],
    }

    # Get file extension
    if mime_type in mime_to_extensions:
        # Choose the appropriate extension based on your requirements
        file_extension = mime_to_extensions[mime_type][0]
    else:
        file_extension = mimetypes.guess_extension(mime_type)

    return mime_type, file_extension


@log.log_decorator()
def stream_to_file(stream: io.IOBase, filename: str or Path) -> None:
    """
    Stream data to a file.

    Args:
        stream (io.IOBase): The input stream to read from.
        filename (str or Path): The path to the output file.

    Returns:
        None

    Example:
    response = requests.get('https://example.com/large_file', stream=True)
        stream_to_file(response.raw, 'large_file.dat')
    """
    with open(filename, 'wb') as file:
        for chunk in stream.iter_content(chunk_size=8192):
            file.write(chunk)


@log.log_decorator()
def string_to_pdf(file_path: str or Path, data: str) -> None:
    """
    Convert a string to a PDF file.

    Args:
        file_path (str or Path): The path to the output PDF file.
        data (str): The string content to be written to the PDF.

    Returns:
        None

    Example:
        text = "This is a sample text for the PDF."
        string_to_pdf('output.pdf', text)
    """
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.lib.pagesizes import letter
    from pathlib import Path

    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(file_path), pagesize=letter)
    width, height = letter

    # convert data to string if it is not
    if not isinstance(data, str):
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        elif isinstance(data, memoryview):
            data = data.tobytes().decode('utf-8')
        else:
            data = str(data)

    # Replace tab characters with spaces
    # data = data.replace('\t', '    ')  # Replace with 4 spaces or any other appropriate character
    data = data.replace('\t', ' ')  # Replace with 2 spaces or any other appropriate character

    data = data.replace('\r\n', '\n').replace('\r', '\n')
    data = data.split('\n')
    line_height = 10
    margin = 20
    text_width = width - 2 * margin
    # start y position
    y = height - margin
    font_name = "Helvetica"
    font_size = 8
    c.setFont(font_name, font_size)

    for line in data:
        while line:
            # Find the maximum number of characters that fit in the text_width
            for i in range(len(line), 0, -1):
                if pdfmetrics.stringWidth(line[:i], font_name, font_size) <= text_width:
                    break
            else:
                i = 1

            # Draw the line and move to the next line
            c.drawString(margin, y, line[:i])
            y -= line_height
            line = line[i:]

            # if reached the bottom of the page
            if y < margin:
                # start a new page
                c.showPage()
                c.setFont(font_name, font_size)
                # reset y position to the top of the new page
                y = height - margin
    c.save()


@log.log_decorator()
def bytes_to_file(data: bytes, filename: str or Path) -> None:
    """
    Save bytes to a file.

    Args:
        data (bytes): The byte data to be written to the file.
        filename (str or Path): The path to the output file.

    Returns:
        None

    Example:
    data = b'Hello, World!'
    bytes_to_file(data, 'hello.txt')
    """
    with open(filename, 'wb') as file:
        file.write(data)


@log.log_decorator()
def json_to_pdf(json_data: dict, filename: str or Path) -> None:
    """
    Convert JSON data to a PDF file.

    Args:
        json_data (dict): The JSON data to be converted to PDF.
        filename (str or Path): The path to the output PDF file.

    Returns:
        None

    Example:
    data = {'name': 'Alice', 'age': 30}
    json_to_pdf(data, 'person.pdf')
    """
    text = json.dumps(json_data, indent=2)
    string_to_pdf(filename, text)


@log.log_decorator()
def clean_html(html_content: str) -> str:
    """
    Clean up HTML content by removing unnecessary whitespace, converting HTML entities,
    and handling various encoding issues.

    Args:
    html_content (str): The HTML content to be cleaned.

    Returns:
    str: The cleaned HTML content.

    Example:
        dirty_html = "<html><body><p>   Messy    content   </p></body></html>"
        clean = clean_html(dirty_html)
        print(clean)
    """
    from html import unescape
    import re

    # Remove DOCTYPE and any XML declarations
    html_content = re.sub(r'<!DOCTYPE[^>]*>', '', html_content)
    html_content = re.sub(r'<\?xml[^>]*\?>', '', html_content)

    # Ensure the input is decoded properly
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8', errors='replace')

    html_content = html_content.replace('\xc2\xa0', ' ').replace('\xa0', ' ').replace('Â', '').replace('&nbsp;', ' ')

    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Function to clean text nodes
    def clean_text(text):
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\xc2\xa0', ' ').replace('\xa0', ' ').replace('Â', '')
        return text.strip()

    # Clean all text nodes
    for element in soup.find_all(text=True):
        if element.parent.name not in ['script', 'style']:
            cleaned_text = clean_text(element.string)
            element.replace_with(cleaned_text)

    # Convert back to string, preserving original structure
    cleaned_html = soup.decode(formatter="minimal")

    # Final cleanup
    cleaned_html = re.sub(r'\s+', ' ', cleaned_html)
    cleaned_html = re.sub(r'>\s+<', '><', cleaned_html)

    return cleaned_html.strip()


@log.log_decorator()
def html_to_pdf(html_content: str, filename: str or Path) -> None:
    """
    Convert HTML content to a PDF file.

    Args:
        html_content (str): The HTML content to be converted to PDF.
        filename (str or Path): The path to the output PDF file.

    Returns:
        None

    Example:
    html = "<html><body><h1>Hello, World!</h1></body></html>"
    html_to_pdf(html, 'webpage.pdf')
    """
    html_content = clean_html(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text()
    string_to_pdf(filename, text)


@log.log_decorator()
def advanced_html_to_pdf(html_code: str, new_file_path: str or Path) -> None:
    import pdfkit
    options = {
        'enable-local-file-access': None,
        'page-size': 'letter',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'dpi': 300  # adjust till it fits (try like 250 or 350)
    }

    # add css
    css = 'style.css'

    html_code = clean_html(html_code)
    pdfkit.from_string(html_code, new_file_path, options=options, css=css)

    if not Path(new_file_path).exists():
        raise Exception(f"Fail to convert html to pdf")


@log.log_decorator()
def xml_to_pdf(xml_content: str, file_path: str or Path, xslt_doc_path: str or Path = None) -> None:
    """
    Convert XML content to a PDF file.

    Args:
        xml_content (str): The XML content to be converted to PDF.
        file_path (str or Path): The path to the output PDF file.
        xslt_doc_path (str or Path, optional): The path to the XSLT document for transformation.

    Returns:
        None

    Example:
        xml = "<root><item>Content</item></root>"
        xml_to_pdf(xml, 'data.pdf')
    """
    from lxml import etree

    encoding_list = ['utf-8', 'ISO-8859-1', 'windows-1252']
    source_doc = None
    for encoding in encoding_list:
        try:
            source_doc = etree.fromstring(xml_content.encode(encoding),
                                          etree.XMLParser(encoding=encoding, ns_clean=True, recover=True))
            break
        except Exception as e:
            print(f"Error Message: {e}")
            continue
    if source_doc is None:
        raise Exception("Fail to parse xml code")

    if xslt_doc_path is None:
        xslt_doc_path = r'xsl_payload/CDA.xsl'

    xslt_doc = etree.parse(xslt_doc_path)
    xslt_transformer = etree.XSLT(xslt_doc)
    output_doc = xslt_transformer(source_doc)
    # Convert the output_doc to a string
    try:
        html_code = etree.tostring(output_doc, pretty_print=True, method="html").decode("utf-8")
    except Exception as e:
        print(f"Error Message: {e}")
        raise Exception(f"Fail to convert xml to html code, Error: {e}")

    html_to_pdf(html_content=html_code, filename=file_path)


@log.log_decorator()
def combine_images_to_pdf(image_paths: list, output_filename: str or Path) -> None:
    """
    Combine multiple images into a single PDF file.

    Args:
        image_paths (list): A list of paths to the image files.
        output_filename (str or Path): The path to the output PDF file.

    Returns:
        None

    Example:
    images = ['image1.jpg', 'image2.jpg', 'image3.jpg']
    combine_images_to_pdf(images, 'combined.pdf')
    """
    images = [Image.open(path).convert('RGB') for path in image_paths]
    images[0].save(output_filename, save_all=True, append_images=images[1:])


@log.log_decorator()
def advanced_combine_images_to_pdf(image_files: List[str], output_file: str):
    from PIL import Image
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    c = canvas.Canvas(output_file, pagesize=letter)
    page_width, page_height = letter  # Get the dimensions of the page

    for image_file in image_files:
        img = Image.open(image_file)
        width, height = img.size
        aspect_ratio = width / height

        # Calculate the new dimensions
        if aspect_ratio > 1:
            # Image width is greater than height
            img_width = page_width
            img_height = img_width / aspect_ratio
        else:
            # Image height is greater than width
            img_height = page_height
            img_width = img_height * aspect_ratio

        # Draw the image centered on the page
        x = (page_width - img_width) / 2
        y = (page_height - img_height) / 2
        c.drawImage(image_file, x, y, width=img_width, height=img_height)
        c.showPage()

    c.save()


@log.log_decorator()
def call_api_with_file(api_url: str, file_path: Path, output_file_path: Path, additional_data: dict = None) -> None:
    """
    Calls an API with the ability to send and receive files.

    Args:
        api_url (str): The URL of the API endpoint.
        file_path (Path): The path to the file to be sent.
        output_file_path (Path): The path where the received file will be saved.
        additional_data (dict, optional): Additional data to be sent with the request.

    Returns:
        None

    Example:
        api_url = "https://api.example.com/convert"
        file_path = Path("input.docx")
        output_file_path = Path("output.pdf")
        additional_data = {"format": "pdf"}
        call_api_with_file(api_url, file_path, output_file_path, additional_data)
    """
    import requests

    if not file_path.exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    files = {'file': open(file_path, 'rb')}
    data = additional_data if additional_data else {}

    try:
        response = requests.post(api_url, files=files, data=data)
        response.raise_for_status()

        with open(output_file_path, 'wb') as output_file:
            output_file.write(response.content)

    except requests.RequestException as e:
        print(f"An error occurred: {e}")
    finally:
        files['file'].close()


@log.log_decorator()
def create_directory_if_not_exists(directory: str or Path) -> None:
    """
    Create a directory if it doesn't exist.

      Args:
          directory (str or Path): The path of the directory to create.

      Returns:
          None

      Example:
        create_directory_if_not_exists('data/processed')
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


@log.log_decorator()
def get_file_size(file_path: str or Path) -> int:
    """
    Get the size of a file in bytes.

      Args:
          file_path (str or Path): The path to the file.

      Returns:
          int: The size of the file in bytes.

        Example:
        size = get_file_size('large_file.dat')
        print(f"File size: {size} bytes")
    """
    return Path(file_path).stat().st_size


@log.log_decorator()
def rename_file(old_name: str or Path, new_name: str or Path) -> None:
    """
    Rename a file.

  Args:
      old_name (str or Path): The current name of the file.
      new_name (str or Path): The new name for the file.

  Returns:
      None

    Example:
    rename_file('old_name.txt', 'new_name.txt')
    """
    Path(old_name).rename(new_name)


@log.log_decorator()
def list_files_in_directory(directory: str or Path) -> list:
    """
    List all files in a directory.

  Args:
      directory (str or Path): The path to the directory.

  Returns:
      list: A list of file paths in the directory.

    Example:
    files = list_files_in_directory('documents')
    for file in files:
        print(file)
    """
    return list(Path(directory).rglob('*.*'))


@log.log_decorator()
def compress_file(file_path: str or Path, output_path: str or Path) -> None:
    """
    Compress a file using gzip.

  Args:
      file_path (str or Path): The path to the file to compress.
      output_path (str or Path): The path for the compressed output file.

  Returns:
      None

    Example:
    compress_file('large_file.dat', 'large_file.dat.gz')
    """
    with open(file_path, 'rb') as f_in:
        with gzip.open(output_path, 'wb') as f_out:
            f_out.writelines(f_in)


@log.log_decorator()
def decompress_file(file_path: str or Path, output_path: str or Path) -> None:
    """
    Decompress a gzip file.

  Args:
      file_path (str or Path): The path to the compressed file.
      output_path (str or Path): The path for the decompressed output file.

  Returns:
      None

    Example:
    decompress_file('large_file.dat.gz', 'large_file.dat')
    """
    with gzip.open(file_path, 'rb') as f_in:
        with open(output_path, 'wb') as f_out:
            f_out.writelines(f_in)


@log.log_decorator()
def encrypt_file(file_path: str or Path, key: bytes, output_path: str or Path) -> None:
    """
    Encrypt a file using Fernet encryption.

  Args:
      file_path (str or Path): The path to the file to encrypt.
      key (bytes): The encryption key.
      output_path (str or Path): The path for the encrypted output file.

  Returns:
      None

    Example:
    key = Fernet.generate_key()
    encrypt_file('sensitive.txt', key, 'sensitive.enc')
    """
    fernet = Fernet(key)
    with open(file_path, 'rb') as file:
        original = file.read()
    encrypted = fernet.encrypt(original)
    with open(output_path, 'wb') as encrypted_file:
        encrypted_file.write(encrypted)


@log.log_decorator()
def decrypt_file(file_path: str or Path, key: bytes, output_path: str or Path) -> None:
    """
    Decrypt a Fernet-encrypted file.

  Args:
      file_path (str or Path): The path to the encrypted file.
      key (bytes): The decryption key.
      output_path (str or Path): The path for the decrypted output file.

  Returns:
      None

    Example:
    decrypt_file('sensitive.enc', key, 'sensitive_decrypted.txt')
    """
    fernet = Fernet(key)
    with open(file_path, 'rb') as enc_file:
        encrypted = enc_file.read()
    decrypted = fernet.decrypt(encrypted)
    with open(output_path, 'wb') as dec_file:
        dec_file.write(decrypted)


@log.log_decorator()
def calculate_md5(file_path: str or Path) -> str:
    """
    Calculate the MD5 hash of a file.

  Args:
      file_path (str or Path): The path to the file.

  Returns:
      str: The MD5 hash of the file.

    Example:
    md5_hash = calculate_md5('document.pdf')
    print(f"MD5 hash: {md5_hash}")
    """
    with open(file_path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
    return file_hash.hexdigest()


@log.log_decorator()
def download_file(url: str, filename: str or Path) -> None:
    """
    Download a file from a given URL.

  Args:
      url (str): The URL of the file to download.
      filename (str or Path): The path where the downloaded file will be saved.

  Returns:
      None

    Example:
    download_file('https://example.com/file.zip', 'downloaded_file.zip')
    """
    response = requests.get(url)
    with open(filename, 'wb') as file:
        file.write(response.content)


@log.log_decorator()
def extract_zip(zip_path: str or Path, extract_to: str or Path) -> None:
    """
    Extract contents of a zip file.

  Args:
      zip_path (str or Path): The path to the zip file.
      extract_to (str or Path): The directory where the contents will be extracted.

  Returns:
      None

    Example:
    extract_zip('archive.zip', 'extracted_folder')
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)


@log.log_decorator()
def create_zip(zip_filename: str or Path, files_to_zip: list) -> None:
    """
    Create a zip file from given files.

  Args:
      zip_filename (str or Path): The name of the zip file to create.
      files_to_zip (list): A list of file paths to include in the zip file.

  Returns:
      None

    Example:
    files = ['file1.txt', 'file2.pdf', 'file3.jpg']
    create_zip('archive.zip', files)
    """
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for file in files_to_zip:
            zipf.write(file, Path(file).name)


@log.log_decorator()
def copy_file(src: str or Path, dst: str or Path) -> None:
    """
    Copy a file from source to destination.

  Args:
      src (str or Path): The path to the source file.
      dst (str or Path): The path to the destination file.

  Returns:
      None

    Example:
    copy_file('original.txt', 'backup/original_copy.txt')
    """
    shutil.copy2(src, dst)


@log.log_decorator()
def move_file(src: str or Path, dst: str or Path) -> None:
    """
    Move a file from source to destination.

  Args:
      src (str or Path): The path to the source file.
      dst (str or Path): The path to the destination file.

  Returns:
      None

    Example:
    move_file('old_location/file.txt', 'new_location/file.txt')
    """
    shutil.move(src, dst)


@log.log_decorator()
def get_file_creation_time(file_path: str or Path) -> datetime.datetime:
    """
    Get the creation time of a file.

  Args:
      file_path (str or Path): The path to the file.

  Returns:
      datetime.datetime: The creation time of the file.

    Example:
    creation_time = get_file_creation_time('document.pdf')
    print(f"File created on: {creation_time}")
    """
    return datetime.datetime.fromtimestamp(Path(file_path).stat().st_ctime)


@log.log_decorator()
def get_file_modification_time(file_path: str or Path) -> datetime.datetime:
    """
    Get the last modification time of a file.

  Args:
      file_path (str or Path): The path to the file.

  Returns:
      datetime.datetime: The last modification time of the file.

    Example:
    mod_time = get_file_modification_time('document.pdf')
    print(f"File last modified on: {mod_time}")
    """
    return datetime.datetime.fromtimestamp(Path(file_path).stat().st_mtime)


@log.log_decorator()
def search_file_content(file_path: str or Path, pattern: str) -> list:
    """
    Search for a regex pattern in a file and return matching lines.

  Args:
      file_path (str or Path): The path to the file to search.
      pattern (str): The regex pattern to search for.

  Returns:
      list: A list of matching lines from the file.

    Example:
    matches = search_file_content('log.txt', r'ERROR.*')
    for match in matches:
        print(match)
    """
    with open(file_path, 'r') as file:
        return [line for line in file if re.search(pattern, line)]


@log.log_decorator()
def count_lines_in_file(file_path: str or Path) -> int:
    """
    Count the number of lines in a file.

  Args:
      file_path (str or Path): The path to the file.

  Returns:
      int: The number of lines in the file.

    Example:
    line_count = count_lines_in_file('large_text_file.txt')
    print(f"The file contains {line_count} lines.")
    """
    with open(file_path, 'r') as file:
        return sum(1 for _ in file)


@log.log_decorator()
def merge_text_files(file_paths: list, output_file: str or Path) -> None:
    """
    Merge multiple text files into a single file.

  Args:
      file_paths (list): A list of paths to the text files to merge.
      output_file (str or Path): The path to the output merged file.

  Returns:
      None

    Example:
    files = ['part1.txt', 'part2.txt', 'part3.txt']
    merge_text_files(files, 'combined.txt')
    """
    with open(output_file, 'w') as outfile:
        for file_path in file_paths:
            with open(file_path, 'r') as infile:
                outfile.write(infile.read())
            outfile.write('\n')


@log.log_decorator()
def sanitize_filename(filename: str) -> str:
    import re
    """
    Remove special characters from a string and replace dots in the middle with hyphens to use it as a file name.

    :param filename: The string to sanitize.
    :return: A sanitized string suitable for use as a file name.
    """
    # Replace dots in the middle of the name with hyphens
    filename = re.sub(r'(?<!^)\.(?!$)', '-', filename)
    # Define a regular expression pattern for allowed characters: letters, numbers, hyphen, underscore, and period.
    pattern = r'[^a-zA-Z0-9\-_.]'
    # Replace characters that don't match the pattern with an empty string
    sanitized_filename = re.sub(pattern, '-', filename)
    return sanitized_filename


def str_to_bool(value: str) -> bool:
    """
    Convert a string to a boolean value.
    Accepts various truthy and falsy expressions.
    Returns True for truthy expressions, False otherwise.
    """
    truthy_values = {'true', 't', 'yes', 'y', '1'}
    # Normalize the string to lowercase to make the check case-insensitive
    return value.strip().lower() in truthy_values


def log_to_csv(data: list[dict[str, any]], file_path: Path, field_names: list[str]) -> None:
    """
    Log the given data to a CSV file at the specified file path.

    Args:
        data (List[Dict[str, Any]]): A list of dictionaries containing the data to be logged.
        file_path (Path): The full path where the CSV file should be saved.
        field_names (List[str]): The list of field names to be used as CSV headers.

    Returns:
        None
    Examples:
        # Sample data
        sample_data = [
            {"name": "Blue T-Shirt", "url": "https://example.com/products/blue-t-shirt-copy-1", "price": 19.99},
            {"name": "Red Shoes", "url": "https://example.com/products/red-shoes", "price": 49.99},
            {"name": "Green Hat (Copy)", "url": "https://example.com/products/green-hat-copy", "price": 14.99},
        ]

        # Define the file path and fieldnames
        file_path = Path("data/logs/updated_products.csv")
        field_names = ["name", "url", "price"]

        # Log the updated data to a CSV file
        log_to_csv(sample_data, file_path, field_names
    """
    import csv
    # Ensure the directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = file_path.exists()

    try:
        with file_path.open(mode='a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names)

            if not file_exists:
                writer.writeheader()

            for item in data:
                writer.writerow({field: item.get(field, "") for field in field_names})

        # print(f"Successfully {'appended to' if file_exists else 'created'} {file_path}")
    except IOError as e:
        print(f"Error writing to CSV file: {e}")


@log.log_decorator()
def run_cli_command(command: str, shell: bool = False, timeout: Optional[int] = None) -> Tuple[int, str, str]:
    """
    Run a CLI command on Windows, macOS, or Linux.

    This function executes the given command and returns the exit code,
    standard output, and standard error.

    Args:
        command (str): The command to execute.
        shell (bool, optional): If True, the command will be executed through the shell.
                                Defaults to False for security reasons.
        timeout (int, optional): The maximum number of seconds the command is allowed to run.
                                 If None, there's no timeout. Defaults to None.

    Returns:
        Tuple[int, str, str]: A tuple containing:
            - The exit code of the command (0 usually means success)
            - The standard output as a string
            - The standard error as a string

    Raises:
        subprocess.TimeoutExpired: If the command execution time exceeds the specified timeout.
        subprocess.SubprocessError: For other subprocess-related errors.
        OSError: If the command cannot be executed (e.g., executable not found).

    Example:
        exit_code, stdout, stderr = run_cli_command("ls -l")
        if exit_code == 0:
            print(f"Command output:\n{stdout}")
        else:
            print(f"Command failed with error:\n{stderr}")
    """
    try:
        if platform.system() == "Windows" and not shell:
            # On Windows, we need to handle command splitting ourselves if not using shell
            args = command if shell else shlex.split(command, posix=False)
        else:
            # On Unix-like systems, we can use shlex normally
            args = command if shell else shlex.split(command)

        # Run the command
        result = subprocess.run(
            args,
            shell=shell,
            check=False,  # We'll handle the exit code ourselves
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired as e:
        return 1, "", f"Command timed out after {timeout} seconds: {str(e)}"
    except subprocess.SubprocessError as e:
        return 1, "", f"Subprocess error occurred: {str(e)}"
    except OSError as e:
        return 1, "", f"OS error occurred: {str(e)}"
    except Exception as e:
        return 1, "", f"An unexpected error occurred: {str(e)}"
