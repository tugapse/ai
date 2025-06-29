# services/prompt_loader.py

import os
from pathlib import Path
from typing import Optional

import functions as func 
from config import ProgramConfig, ProgramSetting
from core.template_injection import TemplateInjection

class PromptLoader:
    """
    Manages loading and processing of system prompt files.
    """

    @staticmethod
    def load_system_prompt(config: ProgramConfig, system_file_setting: str) -> str:
        """
        Reads and processes the content of a system prompt file.
        """
        system_templates_dir = config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES)
        system_prompt_content = ""
        resolved_filepath: Optional[str] = None

        if system_file_setting:
            if os.path.exists(system_file_setting):
                resolved_filepath = system_file_setting
                func.log(f"Loaded system file from explicit path: {resolved_filepath}") 
            elif system_templates_dir:
                template_filename = system_file_setting
                if not template_filename.endswith(".md"):
                    template_filename += ".md"
                
                system_filepath_in_templates = os.path.join(
                    system_templates_dir, template_filename
                )
                if os.path.exists(system_filepath_in_templates):
                    resolved_filepath = system_filepath_in_templates
                    func.log(f"Loaded system file from templates directory: {resolved_filepath}") 
            
            if resolved_filepath:
                system_prompt_content = func.read_file(resolved_filepath) 
            else:
                func.log(f"System prompt file '{system_file_setting}' not found at any known location (explicit path or in templates dir).", level="WARNING") 
        else:
            func.log(f"No system prompt file specified in configuration.") 

        if len(system_prompt_content) == 0:
            func.log(f"No system prompt loaded or found. Continuing without a system prompt.", level="WARNING") 

        injection_template = TemplateInjection(system_prompt_content)
        result = injection_template.replace_system_template()
        return result

