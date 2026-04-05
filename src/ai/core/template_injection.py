from config import ProgramConfig, ProgramSetting
import functions
import os

class TemplateInjection():
    """
    Handles injection of templates into the system prompt.
    """
    
    def __init__(self, system_template, task_template=None, program=None):
        """
        Initializes the TemplateInjection.

        Args:
            system_template (str): The base system template.
            task_template (str, optional): The task template.
            program (object, optional): The program instance.
        """
        self.system_template = system_template or ""
        self.task_template = task_template
    
    def replace_system_template(self):
        """
        Replaces placeholders in the system template with injected content.

        Returns:
            str: The modified system template.
        """

        injections = ProgramConfig.current.config.get("INJECT_TEMPLATES",[])
        replaced_text = self.system_template
        
        for inj in injections:
            template = self._load_injection_template(inj.get("value"))
            replaced_text = replaced_text.replace(inj.get("key"),template)
        return replaced_text

    def _load_injection_template(self, template_name:str):
        """
        Loads an injection template from a file.

        Args:
            template_name (str): The name of the template file.

        Returns:
            str: The content of the template file.
        """
        
        inject_templates_dir = ProgramConfig.current.get(ProgramSetting.PATHS_INJECT_TEMPLATES)
        filepath: str = os.path.join(  inject_templates_dir, template_name.replace(".md","")+".md")            
        if os.path.exists(filepath): 
            return functions.read_file(filepath)
        return ""
