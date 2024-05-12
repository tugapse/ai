import logging,time,os
from ai import functions as func
from ai.core import LLMBot, ContextFile
from ai.core.tasks import TaskPass
from ai.color import Color

class TaskType:
    EACH_FILE = "each_file"
            
class Task:
    def __init__(self, name:str,system_message:str=None) -> None:
        self.name = name
        self.system_message = system_message
        self.messages = []
        self.model_name:str = None
        self.passes_list:list[TaskPass] = list()
        self.pass_index = 0
        self._loaded = False
        self._logger = logging.Logger(__file__)
        self._running_llm : LLMBot = None

    def load(self):
        t_pass: TaskPass = self.passes_list[self.pass_index]

        # Load needed Files
        t_pass._context_files = list()
        
        if t_pass.load_files_from:
            context_files: func.ContextFile = func.get_files(
                directory=t_pass.load_files_from.get("dir"),
                extension=t_pass.load_files_from.get("extension"))
                
            for context_file in context_files or []:
                context_file.load()
                if context_file.loaded:
                    t_pass._context_files.append(context_file)
                
        for filename in t_pass.filenames or []:
            context_file = ContextFile(filename=filename)
            context_file.load()
            if context_file.loaded:
                t_pass._context_files.append(context_file)
                
        if t_pass.message_filename:
            t_pass.message = func.read_file(filename=t_pass.message_filename)
        

    def llm_stream(self, token):
        self.add_output(content = token,filemode = func.FILE_MODE_APPEND)

    def llm_finish_stream(self, data):
        self.add_output(content = data,filemode = func.FILE_MODE_APPEND)
        del self._running_llm

    def add_output(self, content="",filemode=func.FILE_MODE_CREATE):
        output_filename: str = self.get_output_filename()
        func.write_to_file(output_filename,content,filemode=filemode)
        

    def get_output_filename(self):
        t_pass: TaskPass = self.passes_list[self.pass_index]
        return t_pass.output_file or f"{self.name}_pass{self.pass_index}.md"
        
    def validate_pass(self, t_pass:TaskPass) -> None:       
        if len(self.passes_list) == 0: raise Exception(f"Task: {self.name}","Please provide one or more TaskPass!") 

    def _run_pass(self,index=0):
        t_pass: TaskPass = self.passes_list[index]
        print(f"{Color.BLUE}## {Color.RESET} Starting pass {t_pass.name}") 
        
        self.validate_pass(t_pass=t_pass)

        messages = self._create_context(t_pass)

        print(f"{Color.BLUE}## {Color.RESET} Loading LLMBot") 
        
        self._running_llm = LLMBot(model=self.model_name,system_prompt=self.system_message)

        print(f"{Color.BLUE}## {Color.RESET} Running pass {t_pass.name}") 
        for token in self._running_llm.chat(messages=messages):
            self.llm_stream(token=token)
            print(token,end="",flush=True)
        print(Color.GREEN)    
        print(f"Done {t_pass.name} {Color.BLUE}------------------------------------------------------------{Color.RESET} ") 

    def _create_context(self, t_pass):
        print(f"{Color.BLUE}## {Color.RESET} Creating pass context") 
        messages = []
        messages.append( LLMBot.create_message(LLMBot.ROLE_SYSTEM, self.system_message))
        if t_pass._context_files:
            for file in t_pass._context_files:
                messages.append(LLMBot.create_message(LLMBot.ROLE_USER,message=file.content))

        messages.append(LLMBot.create_message(LLMBot.ROLE_USER, message=t_pass.message ))
        return messages
        
        
    def run_passes(self):
        self.pass_index = 0
        print(f"{Color.BLUE}## {Color.RESET} Found: {len(self.passes_list)} passes to run")        
        for t_pass_index in range(len(self.passes_list)):
            print(f"{Color.BLUE}## {Color.RESET} Loading pass {t_pass_index+1}") 
            self.load()
            self._run_pass(t_pass_index)
            self.pass_index += 1
            print("____________________________________________________________________________")

class EachFileTask(Task):
    def __init__(self, name: str, system_message: str = None, directory:str =None, extension:str=None,sleep:int=30) -> None:
        super().__init__(name, system_message)
        self.directory = directory
        self.extension = extension
        self.files: list[ContextFile] = func.get_files(self.directory,self.extension)
        self.current_context_file = None
        self.sleep = sleep

    def run_passes(self) -> None:
        n_files = len(self.files)
        print(f"{Color.BLUE}## {Color.RESET} Found {n_files} '{self.extension}' files in {self.directory}") 
        file_index = 1
        for file in self.files:
            
            self.name = f"file {os.path.basename(file.filename)}"
            print(f"{Color.BLUE}## {Color.RESET} Loading file {file.filename} -> {file_index} of {n_files}") 
            file.load()
            self.current_context_file: ContextFile = file
            print(f"{Color.BLUE}## {Color.RESET} Running task' {self.name} ") 
            super().run_passes()    
            print(f"{Color.BLUE}## {Color.RESET} Sleep for ' {self.sleep} seconds") 
            time.sleep(self.sleep)
            
        

    def _create_context(self, t_pass)->list:
        messages = super()._create_context(t_pass)
        messages.append(LLMBot.create_message(LLMBot.ROLE_USER,message=self.current_context_file.content))
        return messages