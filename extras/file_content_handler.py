import re
import os
import functions as func
# import sys # No longer directly using sys.stdout.flush() for debugs here

from extras.thinking_log_manager import ThinkingLogManager

class FileContentHandler:
    """
    Handles the detection and extraction of file content enclosed within <file>...</file> tags
    from an LLM's token stream. It supports 'name', 'type', and 'ext' attributes on the opening tag.
    The content within the tags is suppressed from direct console output and returned for processing.
    Additionally, this class is now responsible for saving the extracted file content to disk.
    """

    # Regex to find the opening <file> tag and capture its attributes
    FILE_START_PATTERN = re.compile(r'\s*<file\s+name=["\'](?P<name>[^"\']+?)["\'](?:(?:\s+type=["\'](?P<type>[^"\']+?)["\'])|(?:\s+ext=["\'](?P<ext>[^"\']+?)["\']))*\s*>\s*')
    FILE_END_PATTERN = re.compile(r'\s*</file>\s*')
    CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x09\x0B-\x1F\x7F]') # Control characters to clean up

    # Mapping for common MIME types to file extensions
    MIME_TYPE_TO_EXT = {
        'text/html': '.html',
        'text/plain': '.txt',
        'application/json': '.json',
        'application/javascript': '.js',
        'text/css': '.css',
        'text/markdown': '.md',
        'application/x-python': '.py', 
        'text/x-python': '.py',
        'application/xml': '.xml',
        'image/jpeg': '.jpg',
        'image/png': '.png',
    }

    def __init__(self, log_manager: ThinkingLogManager = None, output_base_dir: str = None):
        """
        Initializes the FileContentHandler.

        Args:
            log_manager (ThinkingLogManager, optional): An instance of ThinkingLogManager
                                                         to log raw file content tokens (for debugging parser). Defaults to None.
            output_base_dir (str, optional): The base directory where files should be saved.
                                             Defaults to None. This directory will be created if it doesn't exist.
        """
        self._log_manager = log_manager
        self._output_base_dir = output_base_dir
        
        self._is_active = False # True if currently inside a <file> tag
        self._buffer = "" # Accumulates content between <file> and </file>
        self._file_metadata = {} # Stores 'name', 'type', and 'ext' attributes
        self._token_accumulation_buffer = "" # For handling fragmented tags across tokens

        if self._output_base_dir:
            os.makedirs(self._output_base_dir, exist_ok=True)
            func.log(f"[FileContentHandler] Initialized. Output base directory: {self._output_base_dir}")
        else:
            func.log("[FileContentHandler] Initialized without an output_base_dir. Files will not be savable.")


    def process_token(self, raw_token_string: str) -> tuple[bool, str, dict or None]:
        """
        Processes a raw token string from the LLM stream.
        Manages the state of file content accumulation and extracts file data.

        Args:
            raw_token_string (str): The raw token string from the LLM.

        Returns:
            tuple[bool, str, dict or None]:
                - bool: True if the handler is currently accumulating file content (is_file_active).
                - str: The token content to be printed (tags removed and file content suppressed).
                       This will be an empty string if in an active file content phase.
                - dict or None: This will always be None, as file saving is now handled internally.
        """
        self._token_accumulation_buffer += raw_token_string
        cleaned_buffer = self.CONTROL_CHARS_PATTERN.sub('', self._token_accumulation_buffer)
        token_content_for_display = ""
        extracted_file_data = None 

        # --- Handle closing tag first ---
        end_match = self.FILE_END_PATTERN.search(cleaned_buffer)
        if end_match:
            if self._is_active:
                self._buffer += cleaned_buffer[:end_match.start()]
                
                # Retrieve metadata, providing defaults
                file_name_base = self._file_metadata.get('name', 'untitled_file')
                file_type = self._file_metadata.get('type', '')
                file_ext_attr = self._file_metadata.get('ext', '')

                final_file_name = file_name_base
                determined_ext = ''
                if file_ext_attr:
                    determined_ext = file_ext_attr
                elif file_type:
                    if file_type.startswith('.'):
                        determined_ext = file_type
                    else:
                        determined_ext = self.MIME_TYPE_TO_EXT.get(file_type.lower(), '')
                        if not determined_ext:
                            if file_type.lower() == 'python':
                                determined_ext = '.py'
                            elif file_type.lower() == 'html':
                                determined_ext = '.html'
                            elif file_type.lower() == 'css':
                                determined_ext = '.css'
                            elif file_type.lower() == 'js':
                                determined_ext = '.js'
                            elif file_type.lower() == 'txt':
                                determined_ext = '.txt'
                                
                name_has_ext = '.' in os.path.basename(final_file_name)
                if determined_ext and not final_file_name.lower().endswith(determined_ext.lower()):
                    final_file_name += determined_ext
                elif not name_has_ext and final_file_name.strip():
                    final_file_name += ".txt"
                elif not final_file_name.strip():
                     final_file_name = "untitled.txt"

                file_data_to_save = {
                    "name": final_file_name,
                    "content": self._buffer.strip(),
                    "original_name": file_name_base,
                    "type": file_type,
                    "ext": file_ext_attr
                }
                
                func.log(f"[FileContentHandler] Detected and extracted file: {file_data_to_save['name']}")

                try:
                    self.save_file(file_data_to_save)
                except (ValueError, IOError) as e:
                    func.log(f"[FileContentHandler ERROR] Failed to save file internally: {e}")

                # Reset state for next file
                self._is_active = False
                self._buffer = ""
                self._file_metadata = {}
                self._token_accumulation_buffer = cleaned_buffer[end_match.end():] 
                
                return False, "", None
            else:
                self._token_accumulation_buffer = self.FILE_END_PATTERN.sub('', cleaned_buffer)
                return self.process_token("")

        # --- Handle opening tag if no closing tag was found or handled ---
        start_match = self.FILE_START_PATTERN.search(self._token_accumulation_buffer)
        if start_match:
            if not self._is_active:
                token_content_for_display = self._token_accumulation_buffer[:start_match.start()]
                
                self._file_metadata = start_match.groupdict()
                self._file_metadata = {k: v for k, v in self._file_metadata.items() if v is not None}
                
                self._is_active = True
                self._buffer = ""
                self._token_accumulation_buffer = self._token_accumulation_buffer[start_match.end():]
                
                return True, token_content_for_display, None
            else:
                self._token_accumulation_buffer = self.FILE_START_PATTERN.sub('', self._token_accumulation_buffer)
                return self.process_token("")


        # --- Default accumulation/display if no tags found/handled ---
        if self._is_active:
            func.out(f"\rCreating file :{self._file_metadata.get('name', 'untitled_file')}", end="",flush=True)
            self._buffer += self._token_accumulation_buffer
            self._token_accumulation_buffer = ""
            
            return True, token_content_for_display, None
        else:
            token_content_for_display = self._token_accumulation_buffer
            self._token_accumulation_buffer = ""
            return False, token_content_for_display, None


    def save_file(self, file_data: dict) -> None:
        """
        Saves the extracted file content to disk within the configured output_base_dir.

        Args:
            file_data (dict): A dictionary containing 'name' (filename), and 'content' (file content).
                              'type' and 'ext' attributes are also expected but not directly used for saving.
        
        Raises:
            ValueError: If 'name' is missing from file_data or output_base_dir is not configured.
            IOError: If there's an issue writing the file to disk (e.g., permissions, invalid path).
        """
        file_name = file_data.get("name")
        file_content = file_data.get("content", "")

        if not file_name:
            func.log("[FileContentHandler ERROR] Attempted to save file without a 'name' in extracted data.")
            raise ValueError("Cannot save file: 'name' attribute is missing in extracted file data.")

        if not self._output_base_dir:
            func.log(f"[FileContentHandler ERROR] Output directory not configured for file '{file_name}'. (output_base_dir is None)")
            raise ValueError(f"Cannot save file '{file_name}': output directory not configured for handler.")

        # Construct the full path, ensuring parent directories exist
        file_path = os.path.join(self._output_base_dir, file_name)
        func.log(f"[FileContentHandler] Attempting to save file to: {file_path}")

        try:
            # Create parent directories if they don't exist
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                func.log(f"[FileContentHandler] Creating parent directories for {parent_dir}")
                os.makedirs(parent_dir, exist_ok=True) 

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            func.out(f"'{file_name}' successfully saved to: {file_path}")
        except OSError as e:
            func.log(f"[FileContentHandler ERROR] OS error saving file '{file_name}' to {file_path}: {e}")
            raise IOError(f"Error writing file '{file_name}' to disk: {e}") from e
        except Exception as e:
            func.log(f"[FileContentHandler ERROR] An unexpected error occurred while saving file '{file_name}' to {file_path}: {e}")
            raise IOError(f"An unexpected error occurred while saving file '{file_name}': {e}") from e
