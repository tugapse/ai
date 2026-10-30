import os
import shutil

from ai.color import Color
import ai.functions as func


class DirectoryManager:


    def __init__(self):
        root_directory = func.get_root_directory()
        self.system_directory = os.path.join(root_directory, "system")
        self.user_directory = os.path.join(root_directory,"user") 
    
    def get_user_directory(self):
        return self.user_directory
    
    def get_user_tools_directory(self):
        tools_directory = os.path.join(self.user_directory, "tools")
        if not os.path.exists(tools_directory):
            os.makedirs(tools_directory)
            func.debug(f"{Color.GREEN}Tools directory created at: {tools_directory}{Color.RESET}")
        return tools_directory
    
    
    


    def get_system_prompts_templates_directory(self):
        system_templates_directory = os.path.join(self.system_directory, "templates", "system")
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

  

    
    def _create_user_directory(self):
        if not os.path.exists(self.user_directory):
            os.makedirs(self.user_directory)
            func.debug(f"{Color.GREEN}User directory created at: {self.user_directory}{Color.RESET}")
        else:
            func.debug(f"{Color.YELLOW}[ * ] User directory already exists at: {self.user_directory}{Color.RESET}")

    def _delete_user_directory(self):
        if os.path.exists(self.user_directory):
            shutil.rmtree(self.user_directory)
            func.debug(f"{Color.RED}[ - ] User directory deleted at: {self.user_directory}{Color.RESET}")
        else:
            func.debug(f"{Color.YELLOW}[ * ] User directory does not exist at: {self.user_directory}{Color.RESET}")

    def get_system_models_directory(self):
        return os.path.join(self.system_directory, "models")

    def get_pid_directory(self):
        pid_directory = os.path.join(self.system_directory, "pids")
        if not os.path.exists(pid_directory):
            os.makedirs(pid_directory)
            func.debug(f"{Color.GREEN}PID directory created at: {pid_directory}{Color.RESET}")
        return pid_directory