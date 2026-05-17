import logging
from os.path import exists
from pathlib import Path
from typing import Optional


THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST = False



class ContextFile:
    """
    Represents a file loaded into the context.
    """
    def __init__(self,filename:Optional[str]= None, throw_error_on_load=THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST) -> None:
        """
        Initializes the ContextFile.

        Args:
            filename (str, optional): The path to the file.
            throw_error_on_load (bool): Whether to throw an error if the file is not found.
        """
        self.filename = filename
        self.content:Optional[str] = None
        self.loaded = False
        self.throw_error_on_load: bool = throw_error_on_load
        self._logger = logging.Logger(__file__)
        
    def load(self):
        """
        Loads the content of the file.

        Raises:
            FileNotFoundError: If the file does not exist and throw_error_on_load is True.
            ValueError: If no filename is provided.
        """
        if not self.filename:
            raise ValueError("No filename provided")

        file_path = Path(self.filename)
        if not file_path.exists():
            self._logger.error(f"File not found : {self.filename}")
            if self.throw_error_on_load: raise FileNotFoundError(self.filename)
            self.loaded = False
        else:
            self.content = Path(self.filename).read_text()
            self.loaded = True