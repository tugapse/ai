
import json
import logging
from os.path import exists,dirname
import pathlib

class ProgramSetting:
    MODEL_NAME = "MODEL_NAME"
    SYSTEM_PROMPT_FILE = "SYSTEM_PROMPT_FILE"
    SYSTEM_PROMPT_FOLDER = "SYSTEM_PROMPT_FOLDER"
    PATHS = "PATHS"
    CHAT_LOG = "CHAT_LOG"
    TASK_USER_PROMPT = "TASK_USER_PROMPT"
    SYSTEM_PROMPT = "SYSTEM_PROMPT"
    OLLAMA_HOST = "OLLAMA_HOST"


class ProgramConfig:

    def __init__(self,config:dict) -> None:
        self.config=config

    
    def get(self, key:str,default_value=None):# -> Any:
        return ProgramConfig.current.config.get(key, default_value)    

    def set(self,key:str,value=None) -> None:
        ProgramConfig.current.config[key] = value

    @classmethod
    def load(self,filename) -> None:
        logger = logging.Logger(name=__file__)
        
        if not exists(path=filename):
            logger.level = logging.ERROR
            logger.error("Configuration file not found.", filename)
            return
            
        with open(filename) as f:
            import os
            text_content:str = pathlib.Path(filename).read_text().replace("{root_dir}",dirname(__file__)).replace(os.path.sep,"/")
            data:str = json.loads(text_content)
            ProgramConfig.current = ProgramConfig(config=data)
    

current : ProgramConfig
