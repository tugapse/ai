from threading import Thread

class ExecutorResult:
    
    def __init__(self,result, error = None) -> None:
        self.result = result
        self.error = error


class CommandExecutor:
    def __init__(self,command,finish_callback) -> None:
        self._command_string = command
        self.finished_callback = finish_callback
    
    def _trigger_callback(self,result,error=None):
        self.finished_callback(ExecutorResult(result,error))
    
    def run(self, *args,**kargs):
        raise NotImplementedError("Hey, don't forget to implement the run")

    def output_requested(self):
        raise NotImplementedError("Hey, don't forget to implement the run")
        


class AsyncExecutor(CommandExecutor):

    def __init__(self, command, finish_callback) -> None:
        super().__init__(command, finish_callback)
        self.thread_name = "Async Executor"
        self.thread = None
    
    def _run_thread(self):
        pass
    
    def run(self, auto_start=True, wait=False, **kargs):
        
        self.thread = Thread( target=self._run_thread)
        self.thread.setName(self.thread_name)
        
        if not auto_start: 
            return
        
        self.thread.start()
        if wait: self.thread.join()

    def treminate(self):
        self.thread = None

    