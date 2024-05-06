
class Events:
    """
    This class manages events in an AI system.
    
    Attributes:
        terminate (bool): Flag indicating whether the event loop should be terminated.
        running_command (bool): Flag tracking the status of a command being executed.
        events (dict): Dictionary of registered events, where each key is an event name and
            the value is a list of listeners for that event.
    """

    def __init__(self):
        """
        Initializes the Events class with default values.
        
        Returns:
            None
        """
        self.terminate = False
        self.running_command = False  # new flag to track command running status
        self.events = {}  # dictionary of registered events

    def _register_event(self, event_name: str):
        """
        Registers an event with the system.
        
        Args:
            event_name (str): The name of the event to be registered.
        
        Returns:
            None
        """
        if event_name not in self.events:
            self.events[event_name] = []

    def _unregister_event(self, event_name: str):
        """
        Unregisters an event with the system.
        
        Args:
            event_name (str): The name of the event to be unregistered.
        
        Returns:
            None
        """
        if event_name in self.events:
            del self.events[event_name]

    def trigger(self, event_name: str, data=None):
        """
        Triggers an event with the system.
        
        Args:
            event_name (str): The name of the event to be triggered.
            data (any): Optional data to be passed to listeners for this event.
        
        Returns:
            None
        """
        if event_name in self.events:
            for listener in self.events.get(event_name, []):
                listener(data)

    def add_event(self, event_name: str, listener):
        """
        Adds a listener to an event.
        
        Args:
            event_name (str): The name of the event to which the listener should be added.
            listener: A function that will be called when the event is triggered.
        
        Returns:
            None
        """
        self._register_event(event_name)
        self.events[event_name].append(listener)

    def remove_event(self, event_name: str, listener):
        """
        Removes a listener from an event.
        
        Args:
            event_name (str): The name of the event from which the listener should be removed.
            listener: A function that was previously added to this event.
        
        Returns:
            None
        """
        if event_name in self.events and listener in self.events.get(event_name, []):
            self.events[event_name].remove(listener)
