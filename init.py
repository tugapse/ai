import os

from chat import Chat
from tools import ToolSelector, all_tools_info
from command_executor import CommandExecutor
from llm import LLMBot
from listen import Microphone,ExecutorResult
from color import Color, format_text, pformat_text
import functions as func
from dotenv import load_dotenv

load_dotenv()

system_prompt = None
model_name = "llama3:instruct"
_model_chat_name = model_name.split(":")[0]

func.set_console_title("Ai assistant: " + _model_chat_name)
func.clear_console()


pformat_text(f"Starting { _model_chat_name } assistant...",Color.PURPLE)
 
with  open('./prompt_templates/tugapse.md', 'r') as file:
    system_prompt = file.read().replace("{{TOOLS_INFO}}", all_tools_info())
    


chat  = Chat()
llm = LLMBot( model_name, system_prompt=system_prompt)
microphone = Microphone()
tool_inspector = ToolSelector(model_name)

active_executor:CommandExecutor = None
token_states = {
    'printing_block':False
}


# llm = LLMbot("llama3:instruct")
def process_token(token):
    result = token
    if '``' in token:
        if token_states.get('printing_block',False):
            result = token + Color.RESET
            token_states['printing_block'] = False
        else:
            result = token + Color.YELLOW
            token_states['printing_block'] = True
    return result

def start_chat(user_input):

    outs = llm.chat(chat.messages)
    print(format_text("Assistant:", Color.PURPLE)+Color.RESET,end= " ")
    for text in outs:
        new_token = process_token(text)
        chat.current_message += new_token
        print(text, end="", flush=True)
    print(Color.RESET, end="")


def chat_finished(data):
    print("\n")
    chat.chat_finished()
    message = chat.messages[-1]
    text = message['content']
    if command := tool_inspector.check_tool_request(text): 
        print(command)


def _record_finished(result:ExecutorResult):
    microphone.save_as_wave("./test.wav")
    chat.terminate_command()

def check_command(user_input:str):
    if user_input.startswith("/listen"):
        active_executor = microphone
        microphone.start_recording(_record_finished )
    else:
        format_text("> > Invalid comand < < ",Color.RED)
        chat.terminate_command()

def output_requested():
    if active_executor : active_executor.output_requested()



chat.add_event(chat.EVENT_CHAT_SENT, start_chat)
chat.add_event(chat.EVENT_COMMAND_STARTED, check_command)
chat.add_event(chat.output_requested, output_requested)

llm.add_event(llm.STREAMING_FINISHED_EVENT,chat_finished)

chat.loop()