
import json
import logging
import os
import os
from os.path import exists,dirname
import pathlib

from typing import TypeVar, Generic
T = TypeVar('T')

from typing import TypeVar, Generic
T = TypeVar('T')

class ProgramSetting:
    MODEL_NAME = "MODEL_NAME"
    SYSTEM_PROMPT_FILE = "SYSTEM_PROMPT_FILE"
    SYSTEM_PROMPT_FOLDER = "SYSTEM_PROMPT_FOLDER"
    PATHS = "PATHS"
    USER_PATHS = "USER_PATHS"
    USER_PATHS = "USER_PATHS"
    CHAT_LOG = "CHAT_LOG"
    TASKS_TEMPLATES = "TASKS_TEMPLATES"
    SYSTEM_TEMPLATES = "SYSTEM_TEMPLATES"
    INJECT_TEMPLATES:"INJ_TEMPLATES"
    TASKS_TEMPLATES = "TASKS_TEMPLATES"
    SYSTEM_TEMPLATES = "SYSTEM_TEMPLATES"
    OLLAMA_HOST = "OLLAMA_HOST"
    PRINT_LOG = "PRINT_LOG"
    PRINT_OUTPUT = "PRINT_OUTPUT"
    PRINT_LOG = "PRINT_LOG"
    PRINT_OUTPUT = "PRINT_OUTPUT"


class ProgramConfig(Generic[T]):
class ProgramConfig(Generic[T]):

    def __init__(self,config:dict=None) -> None:
    def __init__(self,config:dict=None) -> None:
        self.config=config
        self.logger = logging.Logger(name=__file__)
        

    def load_predefined_config(self):
        root: str = os.path.dirname(__file__)
        config_filename: str = os.path.join(root,"config.json") 
        default_config = self.__load_to_dict(config_filename)
        #handle user overrides        
        user_config_filename: str = os.environ.get('AI_ASSISTANT_CONFIG_FILENAME')
        if user_config_filename and exists(path=user_config_filename):
            user_config = self.__load_to_dict(user_config_filename)
            default_config.update(**user_config)
        self.config = default_config 

    
    def __load_to_dict(self, filename:str) -> dict:  
        if not exists(path=filename):
            self.logger.level = logging.ERROR
            self.logger.error("Configuration file not found.", filename)
            return None
        
        with open(filename) as f:
            text_content:str = pathlib.Path(filename).read_text().replace("{root_dir}",dirname(__file__)).replace(os.path.sep,"/")
            dict_data:str = json.loads(text_content)
            return dict_data

    def get(self, key:str, default_value:T=None) -> T:
        self.logger = logging.Logger(name=__file__)
        

    def load_predefined_config(self):
        root: str = os.path.dirname(__file__)
        config_filename: str = os.path.join(root,"config.json") 
        default_config = self.__load_to_dict(config_filename)
        #handle user overrides        
        user_config_filename: str = os.environ.get('AI_ASSISTANT_CONFIG_FILENAME')
        if user_config_filename and exists(path=user_config_filename):
            user_config = self.__load_to_dict(user_config_filename)
            default_config.update(**user_config)
        self.config = default_config 

    
    def __load_to_dict(self, filename:str) -> dict:  
        if not exists(path=filename):
            self.logger.level = logging.ERROR
            self.logger.error("Configuration file not found.", filename)
            return None
        
        with open(filename) as f:
            text_content:str = pathlib.Path(filename).read_text().replace("{root_dir}",dirname(__file__)).replace(os.path.sep,"/")
            dict_data:str = json.loads(text_content)
            return dict_data

    def get(self, key:str, default_value:T=None) -> T:
        return ProgramConfig.current.config.get(key, default_value)    

    def set(self,key:str,value=None) -> None:
        ProgramConfig.current.config[key] = value

 

 
    @classmethod
    def load(self):
        program_config = ProgramConfig()
        program_config.load_predefined_config()
        ProgramConfig.current = program_config
        return program_config
    def load(self):
        program_config = ProgramConfig()
        program_config.load_predefined_config()
        ProgramConfig.current = program_config
        return program_config

current : ProgramConfig
