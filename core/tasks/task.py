import logging
from ai.core.llm import LLMBot
from ai.core.tasks.task_pass import TaskPass


            
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
        t_pass.context_files = list() if not t_pass.context_files else t_pass.context_files.clear()
        for filename in t_pass.load_files:
            context_file = ContextFile(filename=filename)
            context_file.load()
            if context_file.loaded:
                t_pass.context_files.append(context_file)

        self.llm.add_event(event_name=LLMBot.STREAMING_TOKEN_EVENT,listener=self.llm_stream)
        self.llm.add_event(event_name=LLMBot.STREAMING_TOKEN_EVENT,listener=self.llm_finish_stream)
        
        self._loaded = True

    def llm_stream(token):
        pass

    def llm_finish_stream( token):
        pass


    def validate_pass(self, t_pass:TaskPass):        
        if not self.llm: raise Exception(f"Task: {self.name}","Please provide a LLMBot object to run the task!")
        if not self._loaded: raise Exception(f"Task: {self.name}","Please run the 'load' method, before running!")

    def run_pass(self,index=0):
        t_pass: TaskPass = self.passes_list[index]
        self.validate_pass(t_pass)
        
       

    def run_passes(self):
        for t_pass_index in range(len(self.passes_list)):
            self.run_pass(t_pass_index)
