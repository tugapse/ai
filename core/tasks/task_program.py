import json
import argparse, logging
from ai.init import print_initial_info
import ai.functions as func
from ai.program import Program ,ProgramConfig
from ai.color import Color
from ai.core.tasks import Task, TaskPass, EachFileTask, TaskType

from pathlib import Path

class AutomatedTask(Program):
    def __init__(self, args_parser:argparse.ArgumentParser=None) -> None:
        super().__init__()
        
        func.clear_console()
        self._logger = logging.Logger(name=__file__,level=logging.INFO)
        self.arg_parser: argparse.ArgumentParser = args_parser or self._create_args_parser()
        self.llm_options = {
            'num_ctx': 16384,
            'temperature':0.0,
            'seed':16384
        }
        self.init_program()

        
    def load_args(self, parser:argparse.ArgumentParser) -> argparse.Namespace:
        return parser.parse_args()

    def init_program(self, args=None) -> None:
        self.args: argparse.Namespace = self.load_args(parser=self.arg_parser)
        return super().init_program(args=self.args)

    def _create_args_parser(self, description):
        return argparse.ArgumentParser(description=description)
        
    
    def create_task_from_config_json(self, json_config:dict) -> Task:

        model_name = json_config.get('model_name')
        system_message = json_config.get('system_message')

        if filename:= json_config.get("system_filename") and Path(filename).exists():
            system_message = json.loads(Path(filename).read_text())
                     

        task : Task = self.__create_task_from_type(
            name=json_config.get('name'),
            system_message=system_message,
            type=json_config.get('type'),
            data=json_config.get('data'))


        task.system_message = system_message
        task.model_name = model_name
        
        for j_pass in json_config.get('task_passes',[]):
            task.passes_list.append(self.create_task_pass(json_pass_config=j_pass))

        return task

    def __create_task_from_type(self,name,system_message,type,data=None):
        if type == TaskType.EACH_FILE:
            return EachFileTask(name=name,system_message=system_message,**data)
        return Task(name=name,system_message=system_message)    
            
    def create_task_pass(self, json_pass_config:dict) -> None:
        # TODO: handle missing properties 
        t_pass = TaskPass(
            name = json_pass_config.get("name"),
            message_filename = json_pass_config.get("message_filename"),
            message = json_pass_config.get("message"),
            filenames = json_pass_config.get("filenames"),
            load_files_from = json_pass_config.get("load_files_from"),
            output_filename =  json_pass_config.get("output_filename"),
            use_previous_output = json_pass_config.get("use_previous_output"),
        )
        return t_pass
    
    def run_task(self, config_filename:str = None,task:Task=None) -> None:
        a_task :Task = task
        if config_filename:
            from pathlib import Path
            import json
            a_path = Path(config_filename) 
            if a_path.exists():

                print(f"{Color.BLUE}## {Color.RESET} Loading automated task configuration file {config_filename}")
                json_obj = json.loads(a_path.read_text())

                print(f"{Color.BLUE}## {Color.RESET} Creating Task")
                a_task = self.create_task_from_config_json(json_config=json_obj)

                print(f"{Color.BLUE}## {Color.RESET} Starting task {a_task.name or '< no name provided >'}")
                print(f"{Color.YELLOW}____________________________________________________________________{Color.RESET}")
                
                a_task.run_passes(self.llm_options)
            else:
                raise FileNotFoundError(config_filename)
        else: raise BaseException("Please provide a config filename", config_filename)