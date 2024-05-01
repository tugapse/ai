from events import Events
from color import Color,format_text

class ChatRoles:
    USER = "user"
    ASSISTANCE = "assistance"
    SYSTEM = "system"

class Chat(Events):
    
    EVENT_CHAT_SENT = 'chat_sent'
    EVENT_COMMAND_STARTED = 'command_started'
    EVENT_OUTPUT_REQUESTED = 'output_requested'
    EVENT_MESSAGES_UPDATED = 'messages_updated'

    def __init__(self):
        super().__init__()
        self.terminate = False
        self.terminate_tokens = ['stop', 'quit','q']
        self.running_command = False
        self.waiting_for_response = False
        self.messages= []
        self.current_message = ""
        self.user_prompt = "User: "
        self.assistant_prompt = "Assistant: "
        self.max_chat_log = 30
        self.cache_messages = True
        self._add_message(ChatRoles.SYSTEM, """Tu és Ema uma asistente virtual, Responde apenas usando o portugues  """ )

    def _add_message(self, role, message):
        if self.cache_messages:
            self.messages.append({'role':role,'content':message})
            self._check_messages_size(self.max_chat_log)

    def _reset_chat(self):
        self.messages = []

    def _check_messages_size(self,max_messages):
        if len(self.messages)>max_messages:
            self.messages.pop(0)
        
    def loop(self):
        while not self.terminate:
            self.process_loop_frame()    

    def process_loop_frame(self):
        """ This function runs a frame in the chat loop """
        if self.running_command:
            user_input = input('')
            self.output_requested(user_input)
            return  # Skip the rest of the loop and go to next iteration
        elif self.waiting_for_response:
            return
        else:
            user_input = input(format_text('User: ',Color.GREEN)+Color.BLUE)

        
        if user_input.startswith('/'):
            self.run_command(user_input)
        elif user_input.lower() in self.terminate_tokens:
            self.terminate_chat()
        else:
            self.send_chat(user_input)    

    def send_chat(self, message):
        self.waiting_for_response = True
        self._add_message('user', message)
        self.trigger(self.EVENT_CHAT_SENT, message)

    def output_requested(self, message):
        self.trigger(self.EVENT_OUTPUT_REQUESTED, message)

    def start_command(self, message):
        self.trigger(self.EVENT_COMMAND_STARTED, message)

    def run_command(self, message):
        if self.running_command:   # Check if the command has already started
            return  # Exit early if the command has already started

        self.running_command = True  # Set the running command flag to True
        self.start_command(message)
    
    def terminate_chat(self):
        self.terminate = True
        print(format_text( "Chat terminated.",Color.BLUE))

    def terminate_command(self):
        self.running_command = False
    
    def chat_finished(self):
        self.waiting_for_response = False
        self._add_message('assistant',self.current_message)
        self.current_message = ""

