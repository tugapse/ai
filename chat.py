from events import Events

class Chat(Events):
    EVENT_CHAT_SENT = 'chat_sent'
    EVENT_COMMAND_STARTED = 'command_started'
    EVENT_OUTPUT_REQUESTED = 'output_requested'

    def __init__(self):
        super().__init__()
        self.terminate = False
        self.terminate_tokens = ['stop', 'quit']
        self.running_command = False
        self.waiting_for_response = False

    def loop(self):
        while not self.terminate:
            if self.running_command:
                user_input = input('')
                self.output_requested(user_input)
                continue  # Skip the rest of the loop and go to next iteration
            elif self.waiting_for_response:
                continue
            else:
                user_input = input('Enter a command: ')

            
            if user_input.startswith('/'):
                self.run_command(user_input)
            elif user_input.lower() in self.terminate_tokens:
                self.terminate_chat()
            else:
                self.send_chat(user_input)    

    def send_chat(self, message):
        self.waiting_for_response = True
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
        print("Chat terminated.")

    def terminate_command(self):
        self.running_command = False
    
    def chat_finished(self):
        self.waiting_for_response = False

