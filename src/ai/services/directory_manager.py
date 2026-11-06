import os
import shutil

from ai.color import Color
import ai.functions as func


class DirectoryManager:
    """
    Manages the creation and retrieval of various necessary directories for the AI application.

    This class ensures that all required system and user directories (like logs, templates,
    tools, and pipelines) exist before the application attempts to use them.
    """

    def __init__(self):
        """
        Initializes the DirectoryManager by setting up paths to the root, system, and user directories.
        """
        self.root_directory = func.get_root_directory()
        self.system_directory = os.path.join(self.root_directory, "system")
        self.user_directory = os.path.join(self.root_directory, "user")
        self.legacy_user_directory = self.root_directory

    def get_user_directory(self):
        """
        Retrieves the path to the main user data directory.

        The runtime stores task/system/tool assets under the configured root directory,
        while a nested legacy `user/` folder may remain for compatibility with older
        setups. Prefer the active root directory when it contains the expected assets,
        and only fall back to the legacy folder if the root is effectively empty.

        :return: str: The path to the user directory.
        """
        root_markers = [
            os.path.join(self.root_directory, "task"),
            os.path.join(self.root_directory, "tools"),
            os.path.join(self.root_directory, "pipelines"),
        ]
        if any(os.path.exists(path) for path in root_markers):
            return self.root_directory

        if os.path.isdir(self.user_directory) :
            legacy_markers = [
                os.path.join(self.legacy_user_directory, "task"),
                os.path.join(self.legacy_user_directory, "tools"),
                os.path.join(self.legacy_user_directory, "pipelines"),
            ]
            if any(os.path.exists(path) for path in legacy_markers):
                return self.legacy_user_directory

        return self.user_directory
    
    def get_user_tools_directory(self):
        """
        Gets the path to the user's tools directory, creating it if it does not exist.

        :return: str: The path to the user tools directory.
        """
        tools_directory = os.path.join(self.user_directory, "tools")
        if not os.path.exists(tools_directory):
            os.makedirs(tools_directory)
            func.debug(f"{Color.GREEN}Tools directory created at: {tools_directory}{Color.RESET}")
        return tools_directory
    
    def _create_user_directory(self):
        """
        Ensures the main user directory exists, logging a message if it already exists.
        """
        if not os.path.exists(self.user_directory):
            os.makedirs(self.user_directory)
            func.debug(f"{Color.GREEN}User directory created at: {self.user_directory}{Color.RESET}")
        else:
            func.debug(f"{Color.YELLOW}[ * ] User directory already exists at: {self.user_directory}{Color.RESET}")
   
    def get_system_prompts_templates_directory(self):
        """
        Gets the path to the system-specific prompt templates directory, creating it if necessary.

        :return: str: The path to the system prompt templates directory.
        """
        system_templates_directory = os.path.join(self.system_directory, "system-prompt")
        if not os.path.exists(system_templates_directory):
            os.makedirs(system_templates_directory)
            func.debug(f"{Color.GREEN}System templates directory created at: {system_templates_directory}{Color.RESET}")
        return system_templates_directory

    def get_system_temp_directory(self):
        """
        Gets the path to the system temporary files directory, creating it if necessary.

        :return: str: The path to the system temp directory.
        """
        temp_directory = os.path.join(self.system_directory, "temp")
        if not os.path.exists(temp_directory):
            os.makedirs(temp_directory)
            func.debug(f"{Color.GREEN}Temp directory created at: {temp_directory}{Color.RESET}")
        return temp_directory
    
    def get_system_logs_directory(self):
        """
        Gets the path to the system logs directory, creating it if necessary.

        :return: str: The path to the system logs directory.
        """
        logs_directory = os.path.join(self.system_directory, "logs")
        if not os.path.exists(logs_directory):
            os.makedirs(logs_directory)
            func.debug(f"{Color.GREEN}Logs directory created at: {logs_directory}{Color.RESET}")
        return logs_directory

    def get_system_agents_directory(self):
        """
        Gets the path to the system agents directory, creating it if necessary.

        :return: str: The path to the system agents directory.
        """
        agents_directory = os.path.join(self.system_directory, "agents")
        if not os.path.exists(agents_directory):
            os.makedirs(agents_directory)
            func.debug(f"{Color.GREEN}Agents directory created at: {agents_directory}{Color.RESET}")
        return agents_directory

    def get_system_templates_directory(self):
        """
        Gets the path to the general system templates directory, creating it if necessary.

        :return: str: The path to the system templates directory.
        """
        templates_directory = os.path.join(self.system_directory, "templates")
        if not os.path.exists(templates_directory):
            os.makedirs(templates_directory)
            func.debug(f"{Color.GREEN}Templates directory created at: {templates_directory}{Color.RESET}")
        return templates_directory

    def get_system_models_directory(self):
        """
        Gets the path to the system models directory.

        :return: str: The path to the system models directory.
        """
        return os.path.join(self.system_directory, "models")

    def get_system_dir(self):
        """
        Retrieves the path to the main system directory.

        :return: str: The path to the system directory.
        """
        return self.system_directory

    def get_root_dir(self):
        """
        Retrieves the path to the application's root directory.

        :return: str: The path to the root directory.
        """
        return self.root_directory
   
    def get_pid_directory(self):
        """
        Gets the path to the process ID (PID) directory, creating it if necessary.

        :return: str: The path to the PID directory.
        """
        pid_directory = os.path.join(self.system_directory, "pids")
        if not os.path.exists(pid_directory):
            os.makedirs(pid_directory)
            func.debug(f"{Color.GREEN}PID directory created at: {pid_directory}{Color.RESET}")
        return pid_directory

    def get_system_pipelines_directory(self):
        """
        Gets the path to the system pipelines directory, creating it if necessary.

        :return: str: The path to the system pipelines directory.
        """
        pipelines_directory = os.path.join(self.system_directory, "pipelines")
        if not os.path.exists(pipelines_directory):
            os.makedirs(pipelines_directory)
            func.debug(f"{Color.GREEN}System Pipelines directory created at: {pipelines_directory}{Color.RESET}")
        return pipelines_directory

    def get_user_pipelines_directory(self):
        """
        Gets the path to the user's pipelines directory, creating it if necessary.

        :return: str: The path to the user pipelines directory.
        """
        directory = os.path.join(self.user_directory, "pipelines")
        if not os.path.exists(directory):
            os.makedirs(directory)
            func.debug(f"{Color.GREEN}User Pipelines directory created at: {directory}{Color.RESET}")
        return directory

 
    def get_user_models_directory(self):
        """
        Gets the path to the user's models configuration directory, creating it if necessary.

        :return: str: The path to the user models directory.
        """
        directory = os.path.join(self.user_directory, "models")
        if not os.path.exists(directory):
            os.makedirs(directory)
            func.debug(f"{Color.GREEN}User model config directory created at: {directory}{Color.RESET}")
        return directory
