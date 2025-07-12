# services/config_applier.py

import os
import argparse
from typing import Optional

import functions as func # Re-added import as func.debug/log is used

from config import ProgramConfig, ProgramSetting

class ConfigApplier:
    """
    Applies command-line arguments to the ProgramConfig instance.
    """

    @staticmethod
    def apply_cli_args_to_config(config: ProgramConfig, args: Optional[argparse.Namespace]):
        """
        Applies command-line argument values to the program configuration.
        """
        if not args:
            return

        if args.model:
            config.set(ProgramSetting.MODEL_CONFIG_NAME, args.model)
            func.debug(f"CLI override: Model config set to '{args.model}'") 

        if args.system:
            system_templates_dir = config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES, "")
            filepath: str = os.path.join(
                system_templates_dir, args.system.replace(".md", "") + ".md"
            )
            if os.path.exists(filepath):
                config.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)
                func.debug(f"CLI override: System prompt file set to '{filepath}' (from --system)") 
            else:
                func.log(f"System prompt file '{filepath}' for '--system {args.system}' not found. Ignoring CLI override.", level="WARNING") 

        if args.system_file:
            filepath = args.system_file
            if os.path.exists(filepath):
                config.set(ProgramSetting.SYSTEM_PROMPT_FILE, filepath)
                func.debug(f"CLI override: System prompt file set to '{filepath}' (from --system-file)") 
            else:
                func.log(f"System prompt file '{filepath}' for '--system-file' not found. Ignoring CLI override.", level="WARNING") 

        if hasattr(args, "print_log") and args.print_log is not None:
            config.set(ProgramSetting.PRINT_LOG,  args.print_log)
            func.debug(f"CLI override: PRINT_LOG set to { args.print_log}") 
        
        if hasattr(args, "print_debug") and args.print_debug is not None:
            config.set(ProgramSetting.PRINT_DEBUG,  args.print_debug)
            func.debug(f"CLI override: PRINT_DEBUG set to { args.print_debug}")   
            
        if hasattr(args, "no_out") and args.no_out is not None:
            config.set(ProgramSetting.PRINT_OUTPUT, not args.no_out)
            func.debug(f"CLI override: PRINT_OUTPUT set to {not args.no_out}") 
        
        func.LOCK_LOG = not config.get(ProgramSetting.PRINT_LOG)
        func.LOCK_DEBUG = not config.get(ProgramSetting.PRINT_DEBUG)

