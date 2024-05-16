import ollama
from tqdm import tqdm
from ai import ProgramConfig, ProgramSetting
from ai.color import Color


class Setup:
    
    def __init__(self) -> None:
        pass

    def check_model(self, model_name:str)->bool:
        models = ollama.list().get("models")
        for model in models:
            if model.get("name") == model_name: return 
        print(f"{Color.RED}Model: {model_name} not found.\n{Color.YELLOW}Download{Color.RESET} from ollama.com ? ( {Color.GREEN}y/N{Color.RESET} ): ")
        answer = input("> ").strip()
        if  answer == "y" or answer == "Y":
            print(f"Downloading {model_name} ...{Color.BLUE}")
            self.__pull_model(model_name)
            print(Color.RESET)

        else:
            exit(1)
    
    def perform_check(self):
        model_name = ProgramConfig.current.get(ProgramSetting.MODEL_NAME)
        self.check_model(model_name)
          

    def __pull_model(self,model_name):
        current_digest, bars = '', {}
        for progress in ollama.pull(model_name, stream=True):
            digest = progress.get('digest', '')
            if digest != current_digest and current_digest in bars:
                bars[current_digest].close()

            if not digest:
                print(progress.get('status'))
                continue

            if digest not in bars and (total := progress.get('total')):
                bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)

            if completed := progress.get('completed'):
                bars[digest].update(completed - bars[digest].n)

            current_digest = digest