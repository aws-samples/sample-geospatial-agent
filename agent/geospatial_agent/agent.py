import os
import base64
import tempfile

import boto3
from strands import Agent
from strands.models import BedrockModel
from strands import tool

from jinja2 import Template

from geospatial_agent.bedrock_models import MODELS, DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE
from geospatial_agent.document_code import get_documentation
from geospatial_agent.python_environment import PythonInterpreter
from geospatial_agent.geospatial import (
    get_satellite_data,
    Index, ComputedIndex, compute_NDVI, compute_NDWI, compute_NBR, compute_dNBR,
    generate_overlay,
    convert_lwir11_to_celsius
)

FILE_SHARING_BUCKET = os.environ.get('CLIENT_FILE_SHARING_BUCKET_NAME', 'client-file-sharing-430302394720-us-east-1')
PRESIGNED_URL_EXPIRATION = 3600  # 1 hour

s3_client = boto3.client('s3')

IMPORTED_CODE = [
    get_satellite_data, 
    Index, ComputedIndex, compute_NDVI, compute_NDWI, compute_NBR, compute_dNBR,
    generate_overlay,
    convert_lwir11_to_celsius
]
CODE_NAMES = ', '.join(c.__name__ for c in IMPORTED_CODE)
CODE_DOCUMENTATION = "\n".join([get_documentation(c) for c in IMPORTED_CODE])

SYSTEM_PROMPT_TEMPLATE = Template("""You are an expert geospatial analyst proficient in python and its geospatial analysis libraries.
You can use the python_repl tool to execute python code to fetch and analyse images from Landsat and Sentinel-2.
The Python interpreter state resets completely with each new user message, but it persists across multiple tool invocations within a single response.
You can perform multi-step computation within a single turn, but do not assume that results from a previous turn are still in memory.

The python environment of the python_repl tool is initialised with the following code (you do not need to rewrite this code):
```python
{{CODE_PREAMBLE}}
```

Do not try to show any matplotlib images: the python_repl tool executes the code in a sub-process without a GUI.
If you need to generate a file use this temporary directory: {{TEMP_DIR}}
The user has no access to this directory.
If you want to show an image to the user invoke the `visualize_image` tool.

You can use the following code:
{{CODE_DOCUMENTATION}}
""")

CODE_PREAMBLE = Template("""
# Geospatial library
from geospatial_agent.geospatial import {{CODE_NAMES}}

# Data and Time
import numpy as np
from datetime import date, datetime, timedelta

# Visualization Libraries
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# Area Of Interest coordinates for the analysis
AOI_COORDINATES = {{AOI_COORDINATES}}
""")


@tool
def visualize_image(image_path: str):
    """
    Load the given PNG image at `image_path` and visualize it on the user client application.
    
    Args:
        image_path: the path of the PNG image to be visualized.
    """
    pass


@tool
def visualize_map_raster_layer(
        image_path: str,
        folium_bounds: list[list[float]]):
    """
    Load a raster PNG from `image_path` and add it as an image overlay to
    the client folium map at the given `folium_bounds`.
    
    Args:
        image_path: the path of the PNG image to be visualized.
        folium_bounds: The bounds of the layer in folium format. [[south, west], [north, east]]
    """
    pass


@tool
def share_file_with_client(file_path: str):
    """
    Share a big file with the client through S3.
    
    Args:
        file_path: the path of the file to be saved on S3 and shared with the client.
    """
    pass


# UI tools used to communicate with the client application, and not providing an actual response.
UI_TOOLS = {'visualize_image', 'visualize_map_raster_layer'}


class GeospatialAgent:
    def __init__(self, coordinates, session_id, history=None, model_id=DEFAULT_MODEL_ID) -> None:
        self.session_id = session_id
        self.cost = MODELS[model_id]['cost']

        self.tmp_dir = tempfile.mkdtemp(prefix='data_analyst_', dir='/tmp')
        code_preamble = CODE_PREAMBLE.render(
            CODE_NAMES=CODE_NAMES,
            AOI_COORDINATES=coordinates)
        self.python_repl = PythonInterpreter(code_preamble)
        self.tool_uses = {}

        messages = []
        if history is not None:
            for role, msg in history:
                messages.append({
                    'role': role,
                    'content': [{
                        'text': msg
                    }]
        	})

        self.agent = Agent(
            model=BedrockModel(
                model_id=model_id,
                temperature=DEFAULT_TEMPERATURE,
            ),
            tools=[
                self.python_repl.get_tool(),
                visualize_image,
                visualize_map_raster_layer,
                share_file_with_client
            ],
            system_prompt=SYSTEM_PROMPT_TEMPLATE.render(
                CODE_PREAMBLE=code_preamble,
                CODE_DOCUMENTATION=CODE_DOCUMENTATION,
                TEMP_DIR=self.tmp_dir
            ),
            callback_handler=None,
            messages=messages
        )
    
    def __on_demand_cost(self, metrics):
        return metrics['accumulated_usage']['inputTokens'] * self.cost['on_demand']['input'] + metrics['accumulated_usage']['outputTokens'] * self.cost['on_demand']['output']

    def __post_process_result(self, response):
        metrics = response.metrics.get_summary()
        return {
            'response': str(response),
            'metrics': {
                'agent': {
                    'total_cycles': metrics['total_cycles'],
                    'total_duration': metrics['total_duration'],
                    'on_demand_cost': self.__on_demand_cost(metrics)
                }
            }
        }

    async def stream_async(self, user_message):
        async for event in self.agent.stream_async(user_message):
            if 'result' in event:
                yield {
                    'msg_type': 'result',
                    'result': self.__post_process_result(event['result'])
                }
            elif 'message' in event:
                for content in event['message']['content']:
                    if 'text' in content:
                        yield {"msg_type": "text", "text": content['text']}
                    
                    elif 'toolUse' in content:
                        toolUse = content['toolUse']
                        self.tool_uses[toolUse['toolUseId']] = toolUse['name']
                        toolUse["msg_type"] = "toolUse"

                        if toolUse['name'] in UI_TOOLS:
                            with open(toolUse['input']['image_path'], 'rb') as f:
                                toolUse['image'] = base64.b64encode(f.read()).decode('utf-8')
                        
                        if toolUse['name'] == 'share_file_with_client':
                            file_key = f"{self.session_id}/{os.path.basename(toolUse['input']['file_path'])}"
                            
                            # Save file on S3
                            with open(toolUse['input']['file_path'], 'rb') as f:
                                s3_client.put_object(Bucket=FILE_SHARING_BUCKET, Key=file_key, Body=f)
                            
                            # Create pre-signed S3 URL
                            toolUse['pre_signed_s3_url'] = s3_client.generate_presigned_url(
                                'get_object',
                                Params={'Bucket': FILE_SHARING_BUCKET, 'Key': file_key},
                                ExpiresIn=PRESIGNED_URL_EXPIRATION
                            )

                        yield toolUse
                    
                    elif 'toolResult' in content:
                        toolResult = content['toolResult']
                        toolResult['name'] = self.tool_uses[toolResult['toolUseId']]
                        
                        if toolResult['name'] in UI_TOOLS:
                            continue

                        toolResult["msg_type"] = "toolResult"
                        yield toolResult
