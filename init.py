import os

from chat import Chat
from command_executor import CommandExecutor
from llm import LLMbot
from listen import Microfone,ExecutorResult
from color import Color, format_text
import functions as func


# model_name = "phi3:instruct"
model_name = "llama3:instruct"
func.set_console_title("Ai assistant: " + model_name)

chat  = Chat()
llm = LLMbot(model_name)
microfone = Microfone()

active_executor:CommandExecutor = None


# llm = LLMbot("llama3:instruct")

def start_chat(user_input):

    outs = llm.chat(chat.messages)
    print(format_text("Assistant:",Color.GREEN))
    print(Color.YELLOW)
    for text in outs:
        chat.current_message += text
        print(text, end="", flush=True)
    print(Color.RESET)


def chat_finished(data):
    print("\n")
    chat.chat_finished()
    message = chat.messages[-1]
    text = message['content']
    os.system(f'espeak -vpt+f4 -p 50 -s 190 "{text}"' )


def _record_finished(result:ExecutorResult):
    microfone.save_as_wave("./test.wav")
    chat.terminate_command()

def check_command(user_input:str):
    if user_input.startswith("/listen"):
        active_executor = microfone
        microfone.start_recording(_record_finished )
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