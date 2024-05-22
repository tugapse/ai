import ollama
from tqdm import tqdm
from config import ProgramConfig, ProgramSetting
from color import Color
from core.llms.ollama_model import OllamaModel


class Setup:
    
    def __init__(self) -> None:
        pass

    def check_model(self, model_name:str)->bool:
        host = ProgramConfig.current.get(ProgramSetting.OLLAMA_HOST)
        ol_model = OllamaModel(model_name, host=host)
        if not ":" in model_name:   model_name += ":latest"
        models = ol_model.list().get("models")
        for model in models:
            if model.get("model") == model_name: return 

        print(f"{Color.RESET}  +  Model not found. Download {Color.YELLOW}{model_name}{Color.RESET} from ollama.com website? {Color.GREEN}y/N{Color.RESET} :", end=" ")
        answer = input("> ").strip()
        if  answer == "y" or answer == "Y":
            print(f"Downloading {model_name} ...{Color.BLUE}")
            self.__pull_model(model_name,ol_model)
            print(Color.RESET)

        else:
            exit(1)
    
    def perform_check(self):
        model_name = ProgramConfig.current.get(ProgramSetting.MODEL_NAME)
       
        self.check_model(model_name)
          

    def __pull_model(self,model_name,ollama_inst):
        # Initialize variables: current_digest and bars dictionary                                                                                                                  
        current_digest, bars = '', {}                                                                                                                                               
                                                                                                                                                                                    
        for progress in ollama_inst.pull(model_name, stream=True):                                                                                                                       
            # Extract digest value from each progress item (default to empty string if not present)                                                                                 
            digest = progress.get('digest', '')                                                                                                                                     
                                                                                                                                                                                    
            # If the new digest is different from previous one and it's already tracked                                                                                             
            if digest != current_digest and current_digest in bars:                                                                                                                 
                # Close any existing progress bar for that digest                                                                                                                   
                bars[current_digest].close()                                                                                                                                        
                                                                                                                                                                                    
            # Check if there's no value for this digest (might indicate error or incomplete data)                                                                                   
            if not digest:                                                                                                                                                          
                print(progress.get('status'))  # Print status message from the current progress                                                                                     
                continue                                                                                                                                                            
                                                                                                                                                                                    
            # If it is a new digest: create a new progress bar and update current_digest                                                                                            
            if digest not in bars and (total := progress.get('total')):                                                                                                               
                bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)                                                                         
                                                                                                                                                                                    
            # Update the completed portion of this digest's progress bar (if applicable)                                                                                            
            if completed := progress.get('completed'):                                                                                                                              
                bars[digest].update(completed - bars[digest].n)  # n is probably the current value                                                                                  
                                                                                                                                                                                    
            # Set new current_digest for next iteration                                                                                                                             
            current_digest = digest 