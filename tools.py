import os

import ollama
from chat import ChatRoles
from llm import LLMBot
from color import Color,pformat_text
import json


class ToolSelector(LLMBot):
    
    def __init__(self, model, system_prompt=None):
        with  open('./prompt_templates/tool_selector.md', 'r') as file:
            system_prompt = file.read()
        super().__init__(model, system_prompt)

    def  check_tool_request(self,text):
        if("'tool':" in text or '"tool":' in text):
            pformat_text("Checking for tool request ...",Color.RED)
            new_messages = self.check_system_prompt([{'role':ChatRoles.USER,'content':text}])
            res = ollama.chat(model=self.model_name, messages=new_messages, stream=False) 
            result = json.loads(res['message']['content'])
        
            return result['tool'] is not None
        return False


class FileLister:

    def __init__(self, directory):

        self.directory = directory


    def list_files(self, extension=None):

        if extension and not extension.startswith('.'):

            extension = '.' + extension


        files = []

        for filename in os.listdir(self.directory):

            if os.path.isfile(os.path.join(self.directory, filename)):

                if not extension or filename.endswith(extension):

                    files.append(filename)

        return files