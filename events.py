class Events:
    def __init__(self): 
        self.terminate = False
        self.running_command = False  # new flag to track command running status
        self.events = {}  # dictionary of registered events

    def _register_event(self, event_name): 
        if event_name not in self.events:
            self.events[event_name] = []

    def _unregister_event(self, event_name): 
        if event_name in self.events:
            del self.events[event_name]

    def trigger(self, event_name, data=None): 
        if event_name in self.events:
            for listener in self.events.get(event_name, []):  
                listener(data)

    def add_event(self, event_name, listener): 
        self._register_event(event_name)
        self.events[event_name].append(listener)

    def remove_event(self, event_name, listener): 
        if event_name in self.events and listener in self.events.get(event_name, []):
            self.events[event_name].remove(listener)