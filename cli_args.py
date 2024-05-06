import os
from chat import ChatRoles
import functions as func

class CliArgs:
    def __init__(self,prog, ask:callable) -> None:
        self.ask = ask
        self.create_message = prog.llm.create_message
        
    def parse_args(self,prog,args)-> None:

        self._is_list_models(args)
        self._has_output_files(prog, args)
        self._has_task(prog, args)
        self._has_task_file(args)
        self._has_folder(prog, args)
        self._has_file(prog, args)
        self._has_message(prog, args)

    def _is_list_models(self, args):
        if args.list_models: 
            os.system("ollama list")
            exit(0)

    def _has_output_files(self,prog, args):
        if args.output_file:
            prog.write_to_file = True
            prog.output_filename = args.output_file
            
    def _has_message(self, prog, args):
        if args.msg:
            prog.chat.messages.append(self.create_message(ChatRoles.USER,args.msg))
            self.ask(prog.llm, prog.chat.messages)
            exit(0)

    def _has_folder(self, prog, args):
        if args.load_folder:
            files = func.get_files(args.load_folder,args.extension)
            messages = list()
            for file in files:
                messages.append(prog.llm.create_message(ChatRoles.USER, f"Filename: {file['filename']} \n File Content:\n```{file['content']}\n"))
                prog.chat.messages = messages 

    def _has_file(self, prog, args):
        if args.file:
            text_file = func.read_file(args.file)
            prog.chat._add_message(ChatRoles.USER, f"File: {args.file} \n\n  ```{text_file}```")

    def _has_task_file(self, args):
        if args.task_file:
            task = func.read_file(args.task_file)
            args.msg = task

    def _has_task(self, prog, args):
        if args.task:
            filename = os.path.join(prog.config['PATHS']['TASK_USER_PROMPT'],args.task.replace(".md","")+".md")
            task = func.read_file(filename)
            args.msg = task