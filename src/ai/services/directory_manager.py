import os
import shutil

from ai.color import Color
import ai.functions as func


class DirectoryManager:


    def __init__(self):
        self.root_directory = func.get_root_directory()
        self.system_directory = os.path.join(self.root_directory, "system")
        self.user_directory = os.path.join(self.root_directory,"user") 
    
    def get_user_directory(self):
        return self.user_directory
    
    def get_user_tools_directory(self):
        tools_directory = os.path.join(self.user_directory, "tools")
        if not os.path.exists(tools_directory):
            os.makedirs(tools_directory)
            func.debug(f"{Color.GREEN}Tools directory created at: {tools_directory}{Color.RESET}")
        return tools_directory
    
    def _create_user_directory(self):
        if not os.path.exists(self.user_directory):
            os.makedirs(self.user_directory)
            func.debug(f"{Color.GREEN}User directory created at: {self.user_directory}{Color.RESET}")
        else:
            func.debug(f"{Color.YELLOW}[ * ] User directory already exists at: {self.user_directory}{Color.RESET}")
   
    def get_system_prompts_templates_directory(self):
        system_templates_directory = os.path.join(self.system_directory, "system-prompt")
        if not os.path.exists(system_templates_directory):
            os.makedirs(system_templates_directory)
            func.debug(f"{Color.GREEN}System templates directory created at: {system_templates_directory}{Color.RESET}")
        return system_templates_directory

    def get_system_temp_directory(self):
        temp_directory = os.path.join(self.system_directory, "temp")
        if not os.path.exists(temp_directory):
            os.makedirs(temp_directory)
            func.debug(f"{Color.GREEN}Temp directory created at: {temp_directory}{Color.RESET}")
        return temp_directory
    
    def get_system_logs_directory(self):
        logs_directory = os.path.join(self.system_directory, "logs")
        if not os.path.exists(logs_directory):
            os.makedirs(logs_directory)
            func.debug(f"{Color.GREEN}Logs directory created at: {logs_directory}{Color.RESET}")
        return logs_directory

    def get_system_agents_directory(self):
        agents_directory = os.path.join(self.system_directory, "agents")
        if not os.path.exists(agents_directory):
            os.makedirs(agents_directory)
            func.debug(f"{Color.GREEN}Agents directory created at: {agents_directory}{Color.RESET}")
        return agents_directory

    def get_system_templates_directory(self):
        templates_directory = os.path.join(self.system_directory, "templates")
        if not os.path.exists(templates_directory):
            os.makedirs(templates_directory)
            func.debug(f"{Color.GREEN}Templates directory created at: {templates_directory}{Color.RESET}")
        return templates_directory

    def get_system_models_directory(self):
        return os.path.join(self.system_directory, "models")

    def get_system_dir(self):
        return self.system_directory

    def get_root_dir(self):
            return self.root_directory
   
    def get_pid_directory(self):
        pid_directory = os.path.join(self.system_directory, "pids")
        if not os.path.exists(pid_directory):
            os.makedirs(pid_directory)
            func.debug(f"{Color.GREEN}PID directory created at: {pid_directory}{Color.RESET}")
        return pid_directory

    def get_system_pipelines_directory(self):
        pipelines_directory = os.path.join(self.system_directory, "pipelines")
        if not os.path.exists(pipelines_directory):
            os.makedirs(pipelines_directory)
            func.debug(f"{Color.GREEN}System Pipelines directory created at: {pipelines_directory}{Color.RESET}")
        return pipelines_directory

    def get_user_pipelines_directory(self):
        directory = os.path.join(self.user_directory, "pipelines")
        if not os.path.exists(directory):
            os.makedirs(directory)
            func.debug(f"{Color.GREEN}User Pipelines directory created at: {directory}{Color.RESET}")
        return directory

 
    def get_user_models_directory(self):
        directory = os.path.join(self.user_directory, "models")
        if not os.path.exists(directory):
            os.makedirs(directory)
            func.debug(f"{Color.GREEN}User model config directory created at: {directory}{Color.RESET}")
        return directory

    