import os
from ai.config import ProgramConfig, ProgramSetting
import ai.functions as func

class TemplateInjection():
    """
    Handles injection of templates into the system prompt.

    This class is responsible for reading predefined template files and replacing
    placeholders within a base system template using content loaded from these files.
    """
    
    def __init__(self, system_template, task_template=None, program=None):
        """
        Initializes the TemplateInjection.

        Args:
            system_template (str): The base system template string.
            task_template (str, optional): The task template string. Defaults to None.
            program (object, optional): The program instance object. Defaults to None.
        """
        self.system_template = system_template or ""
        self.task_template = task_template
    
    def replace_system_template(self):
        """
        Replaces placeholders in the system template with injected content.

        It retrieves the list of template injections from the current program configuration
        and iterates through them, replacing keys in the system template with the content
        loaded from the corresponding template files.

        Returns:
            str: The modified system template with all injections applied.
        """

        injections = ProgramConfig.get_current().config.get("INJECT_TEMPLATES",[])
        replaced_text = self.system_template
        
        for inj in injections:
            template = self._load_injection_template(inj.get("value"))
            replaced_text = replaced_text.replace(inj.get("key"),template)
        return replaced_text

    def _load_injection_template(self, template_name:str):
        """
        Loads an injection template from a file.

        It constructs the full file path by joining the configured injection templates directory
        with the template name, ensuring the extension is always .md.

        Args:
            template_name (str): The name of the template file (e.g., "my_template").

        Returns:
            str: The content of the template file, or an empty string if the file is not found.
        """
        
        inject_templates_dir = ProgramConfig.get_current().get(ProgramSetting.PATHS_INJECT_TEMPLATES)
        filepath: str = os.path.join(  inject_templates_dir, template_name.replace(".md","")+".md")            
        if os.path.exists(filepath): 
            return func.read_file(filepath)
        return ""