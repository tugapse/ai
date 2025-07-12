from core import ContextFile


class TaskPass:
    def __init__(self,name:str=None,message:str = None, message_filename :str = None, load_files_from : dict = None,
                 filenames:str = None, context_files:list[ContextFile] = None,output_filename:str = None,use_previous_output = False) -> None:
        self.name:str = name
        self.message:str = message
        self.message_filename:str = message_filename
        self.load_files_from:dict = load_files_from
        self.filenames: str = filenames
        self._context_files:list[ContextFile] = context_files
        self.output_file:str = output_filename
        self.use_previous_output = use_previous_output
