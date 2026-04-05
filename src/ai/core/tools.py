import os

import ollama
from chat import ChatRoles
from core.llms.ollama_model import OllamaModel
from color import Color, pformat_text
import json
import os




class ToolSelector(OllamaModel):
    """
    Selects the appropriate tool based on the user's request.
    """
    
    def __init__(self, model, config, system_prompt=None):
        """
        Initializes the ToolSelector.

        Args:
            model: The model to use.
            config: The configuration dictionary.
            system_prompt: The system prompt to use.
        """
        with  open(os.path.join(
            config['SYSTEM_PROMPT_FOLDER'],
            './prompt_templates/tool_selector.md'), 'r') as file:
            system_prompt = file.read()
        super().__init__(model, system_prompt)

    def  check_tool_request(self,text):
        """
        Checks if the text contains a tool request.

        Args:
            text (str): The text to check.

        Returns:
            bool: True if a tool request is found, False otherwise.
        """
        if("'tool':" in text or '"tool":' in text):
            pformat_text("Checking for tool request ...",Color.RED)
            new_messages = self.check_system_prompt([{'role':ChatRoles.USER,'content':text}])
            res = ollama.chat(model=self.model_name, messages=new_messages, stream=False) 
            result = json.loads(res['message']['content'])
        
            return result['tool'] is not None
        return False

class BaseTool:
    """
    Base class for all tools.
    """
    def __init__(self,tool, name,description, examples=None) -> None:
        """
        Initializes the BaseTool.

        Args:
            tool (str): The tool identifier.
            name (str): The name of the tool.
            description (str): The description of the tool.
            examples (str, optional): Examples of tool usage.
        """
        self.tool= tool
        self.name = name
        self.description = description
        self.examples = examples

    def run(data):
        """
        Runs the tool with the given data.

        Args:
            data: The data to process.
        """
        raise NotImplementedError("Hey, don't forget to implement the run")
    
    def __repr__(self) -> str:
        """
        Returns a string representation of the tool.
        """
        return f"""
Tool id : {self.tool}
Tool Name: {self.name}
Tool Description: {self.description}
Tool Examples: {self.examples}
---"""

class FileLister(BaseTool):
    """
    Tool for listing files in a directory.
    """

    def __init__(self):
        """
        Initializes the FileLister tool.
        """
        super().__init__(
            "list_dir",
            "Directory Lister",
            "List all files and folder in a directory",
             "{'tool':'list_dir','data':'directory_to_get_files'}")

    def run(self, directory):
        """
        Runs the file lister tool.

        Args:
            directory (str): The directory to list files from.
        """
        self.list_files(directory)

    def list_files(self, extension=None):
        """
        Lists files in the directory, optionally filtering by extension.

        Args:
            extension (str, optional): The file extension to filter by.

        Returns:
            list: A list of filenames.
        """

        if extension and not extension.startswith('.'):

            extension = '.' + extension


        files = []

        for filename in os.listdir(self.directory):

            if os.path.isfile(os.path.join(self.directory, filename)):

                if not extension or filename.endswith(extension):

                    files.append(filename)

        return files


import requests
import json
from os import environ

class OpenWeatherAPI(BaseTool):
    """
    Tool for interacting with the OpenWeatherMap API.
    """
    def __init__(self, api_key=None):
        """
        Initializes the OpenWeatherAPI tool.

        Args:
            api_key (str, optional): The API key for OpenWeatherMap.
        """
        super().__init__(
            "weather_search",
            "Open Weather api",
            "gets weather forecast for current weather in any location",
            "{'tool':'weather_search','data':'location_to_check'}")
        self.api_key = api_key or environ.get("OPENWEATHER_API_KEY")

    def run(self,city):
        """
        Runs the weather search tool.

        Args:
            city (str): The city to get the weather for.
        """
        self.get_current_weather(city)
        
    def get_current_weather(self, city):
        """
        Gets the current weather for a city.

        Args:
            city (str): The city name.

        Returns:
            dict: The weather data.
        """
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={self.api_key}"
        response = requests.get(url)
        data = json.loads(response.text)
        return data

    def get_forecast(self, city, days):
        """
        Gets the weather forecast for a city.

        Args:
            city (str): The city name.
            days (int): The number of days to forecast.

        Returns:
            list: A list of forecast data.
        """
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&appid={self.api_key}"
        response = requests.get(url)
        data = json.loads(response.text)
        forecast_data = []
        for i in range(len(data["list"])):
            if i % 8 == 0:   # Get the forecast every 3 hours
                forecast_data.append({
                     "date": data["list"][i]["dt_txt"],
                     "temperature": data["list"][i]["main"]["temp"],
                     "condition": data["list"][i]["weather"][0]["description"]
                 })
        return forecast_data
