import logging
from os.path import exists
from pathlib import Path


THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST = False



class ContextFile:
    def __init__(self,filename:str= None, throw_error_on_load=THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST) -> None:
        self.filename = filename
        self.content:str = None
        self.loaded = False
        self.throw_error_on_load: bool = throw_error_on_load
        self._logger = logging.Logger(__file__)
        
    def load(self):
        file_path = Path(self.filename)
        if not file_path.exists():
            self._logger.error(f"File not found : {self.filename}")
            if self.throw_error_on_load: raise FileNotFoundError(self.filename)
            self.loaded = False
        else:
            self.content = Path(self.filename).read_text()
            self.loaded = True