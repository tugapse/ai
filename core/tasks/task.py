import logging
import pathlib
from ai import functions as func
from ai.core import LLMBot
from ai.core.tasks import ContextFile,TaskPass


            
class Task:
    def __init__(self, name:str, llm:LLMBot, task_message:str=None,
                 system_message:str=None) -> None:
        self.name = name
        self.task_message = task_message
        self.system_message = system_message
        self.messages = []
        self.llm:LLMBot = llm 
        self.passes_list:list[TaskPass] = list()
        self.pass_index = 0
        self._loaded = False
        self._logger = logging.Logger(__file__)

    def load(self, index:int=0):
        t_pass: TaskPass = self.passes_list[self.pass_index]

        # Load needed Files
        t_pass.context_files = list() if not t_pass.context_files else t_pass.context_files.clear()
        for filename in t_pass.load_files:
            context_file = ContextFile(filename=filename)
            context_file.load()
            if context_file.loaded:
                t_pass.context_files.append(context_file)

        # Register events
        self.llm.add_event(event_name=LLMBot.STREAMING_TOKEN_EVENT,
                           listener=lambda token: self.llm_stream(token=token))

        self.llm.add_event(event_name=LLMBot.STREAMING_FINISHED_EVENT,
                           listener=lambda result: self.llm_finish_stream(result))
        
        self._loaded = True

    def llm_stream(self, token):
        self.add_output(content = token,filemode = func.FILE_MODE_APPEND)

    def llm_finish_stream(self, data):
        pass

    def add_output(self, content="",filemode=func.FILE_MODE_CREATE):
        output_filename: str = self.get_output_filename()
        func.write_to_file(output_filename,content,)
        

    def get_output_filename(self):
        t_pass: TaskPass = self.passes_list[self.pass_index]
        return t_pass.output_file or f"{self.name}_pass{self.pass_index}.log"
        
    def validate_pass(self, t_pass:TaskPass):        
        if not self.llm: raise Exception(f"Task: {self.name}","Please provide a LLMBot object to run the task!")
        if not self._loaded: raise Exception(f"Task: {self.name}","Please run the 'load' method, before running!")

    def run_pass(self,index=0):
        t_pass: TaskPass = self.passes_list[index]
        self.validate_pass(t_pass)
        

    def run_passes(self):
        for t_pass_index in range(len(self.passes_list)):
            self.run_pass(t_pass_index)
