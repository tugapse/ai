# services/prompt_loader.py

import os
from pathlib import Path
from typing import Optional

import functions as func 
from services.config_helper import ProgramConfig, ProgramSetting
from core.template_injection import TemplateInjection

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."

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
            else:
                if not system_templates_dir:
                    system_templates_dir = os.path.join(func.get_root_directory(), "system")
                    func.debug(
                        f"PromptLoader: defaulting system templates dir to {system_templates_dir}"
                    )

                if system_templates_dir:
                    template_filename = system_file_setting
                    if not template_filename.endswith(".md"):
                        template_filename += ".md"
                    
                    system_filepath_in_templates = os.path.join(
                        system_templates_dir, template_filename
                    )
                    if os.path.exists(system_filepath_in_templates):
                        resolved_filepath = system_filepath_in_templates
                        func.log(f"Loaded system file from templates directory: {resolved_filepath}")

                if not resolved_filepath and system_file_setting.strip().lower() == "default":
                    repo_root = Path(__file__).resolve().parent.parent
                    builtin_default_path = os.path.join(
                        repo_root, "templates", "system", "default.md"
                    )
                    if os.path.exists(builtin_default_path):
                        resolved_filepath = builtin_default_path
                        func.log(
                            f"Loaded built-in default system prompt from repo templates: {resolved_filepath}"
                        )

            if resolved_filepath:
                system_prompt_content = func.read_file(resolved_filepath)
            elif system_file_setting.strip().lower() == "default":
                func.log(
                    "Using built-in fallback system prompt for 'default'.",
                    level="WARNING",
                )
                system_prompt_content = DEFAULT_SYSTEM_PROMPT
            else:
                func.log(
                    f"System prompt file '{system_file_setting}' not found at any known location (explicit path or in templates dir).",
                    level="WARNING",
                )
        else:
            func.log(f"No system prompt file specified in configuration.")

        if len(system_prompt_content) == 0:
            func.log(
                f"No system prompt loaded or found. Continuing without a system prompt.",
                level="WARNING",
            )

        injection_template = TemplateInjection(system_prompt_content)
        result = injection_template.replace_system_template()
        return result

