import os

import ollama
from chat import ChatRoles
from llm import LLMBot
from color import Color,pformat_text
import json
import os




class ToolSelector(LLMBot):
    
    def __init__(self, model, system_prompt=None):
        with  open('./prompt_templates/tool_selector.md', 'r') as file:
            system_prompt = file.read()
        super().__init__(model, system_prompt)

    def  check_tool_request(self,text):
        if("'tool':" in text or '"tool":' in text):
            pformat_text("Checking for tool request ...",Color.RED)
            new_messages = self.check_system_prompt([{'role':ChatRoles.USER,'content':text}])
            res = ollama.chat(model=self.model_name, messages=new_messages, stream=False) 
            result = json.loads(res['message']['content'])
        
            return result['tool'] is not None
        return False

class BaseTool:
    def __init__(self,tool, name,description, examples=None) -> None:
        self.tool= tool
        self.name = name
        self.description = description
        self.examples = examples

    def run(data):
        raise NotImplementedError("Hey, don't forget to implement the run")
    
    def __repr__(self) -> str:
        return f"""
TOOL : {self.tool}
TOOL Name: {self.name}
TOOL Description: {self.description}
TOOL Examples: {self.examples}
---"""

class FileLister(BaseTool):

    def __init__(self):
        super().__init__(
            "list_dir"
            "Directory Lister",
            "List all files and folder in a directory",
             "{'tool':'list_dir','data':'directory_to_get_files'}")

    def run(self, directory):
        self.list_files(directory)

    def list_files(self, extension=None):

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
    def __init__(self, api_key=None):
        super().__init__(
            "weather_search"
            "Open Weather api",
            "gets weather forecast for current weather in any location",
            "{'tool':'weather_search','data':'location_to_check'}")
        self.api_key = api_key or environ.get("OPENWEATHER_API_KEY")

    def run(self,city):
        self.get_current_weather(city)
        
    def get_current_weather(self, city):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={self.api_key}"
        response = requests.get(url)
        data = json.loads(response.text)
        return data

    def get_forecast(self, city, days):
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

        
All_TOOLS = [
    FileLister(),
    OpenWeatherAPI()
]

def all_tools_info():
    result = ""
    for tool in All_TOOLS:
        result += str(tool)
    return result