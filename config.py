
import json
import logging
from os.path import exists, basename,dirname
import pathlib
import pickle

class ProgramConfig:
    def __init__(self,config:dict) -> None:
        self.config=config

    
    def get(key:str,default_value=None):# -> Any:
        return ProgramConfig.current.config.get(key,default_value)    

    def set(self,key:str,value=None) -> None:
        ProgramConfig.current.config[key] = value

    @classmethod
    def load(self,filename) -> None:
        logger = logging.Logger(name=__file__)
        filename:str = basename(filename)
        
        if not exists(path=filename):
            logger.level = logging.ERROR
            logger.error("Configuration file not found.", filename)
            return
            
        with open(filename) as f:
            text_content:str = pathlib.Path(filename).read_text().replace("{root_dir}",dirname(__file__))
            data:str = json.loads(text_content)
            ProgramConfig.current = ProgramConfig(config=data)
    

current : ProgramConfig
