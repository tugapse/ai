import argparse
from ai.program import Program 

class AutomatedTask(Program):
    def __init__(self) -> None:
        super().__init__()
        

    def load_args(self) -> None:
        parser = argparse.ArgumentParser(description='AI Assistant Automated Task')
        parser.add_argument('--msg', type=str, help='Direct question')

    def init_program(self, args=None):
        return super().init_program(args)

    def main(self) -> None:
        pass