from ai.core.tasks import ContextFile


class TaskPass:
    def __init__(self,name,task_message:str = None,system_message = None, load_files:list[str] = None,
                 context_files:list[ContextFile] = None,output_filename:str = None) -> None:
        self.name:str = name
        self.task_message:str = task_message
        self.system_message:str = system_message
        self.load_files :list[str] = load_files
        self.context_files:list[ContextFile] = context_files
        self.output_file:str = output_filename
