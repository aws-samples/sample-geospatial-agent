from copy import deepcopy
import sys
import json
import uuid
from typing import Iterator, Optional
import base64
from io import BytesIO
from pathlib import Path
from os import makedirs

import boto3
from botocore.config import Config
from PIL import Image
from evaluation import TESTS_IMG


UI_TOOLS = {'visualize_image', 'visualize_map_raster_layer'}


def get_stack_outputs() -> dict:
    """Retrieve CDK stack outputs."""
    cfn = boto3.client('cloudformation')
    
    # Find the webapp stack
    stacks = cfn.list_stacks(StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE'])
    webapp_stack = next(
        (s['StackName'] for s in stacks['StackSummaries'] if 'webapp' in s['StackName'].lower()),
        None
    )
    
    if not webapp_stack:
        raise ValueError("WebApp stack not found")
    
    response = cfn.describe_stacks(StackName=webapp_stack)
    outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
    
    return outputs


def authenticate(user_pool_id: str, client_id: str, identity_pool_id: str, username: str, password: str) -> dict:
    """Authenticate with Cognito and return AWS credentials."""
    cognito_idp = boto3.client('cognito-idp')
    
    # Authenticate with username/password
    auth_response = cognito_idp.initiate_auth(
        ClientId=client_id,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )
    
    id_token = auth_response['AuthenticationResult']['IdToken']
    
    # Get identity credentials
    region = boto3.session.Session().region_name
    identity_client = boto3.client('cognito-identity')
    
    identity_id = identity_client.get_id(
        IdentityPoolId=identity_pool_id,
        Logins={
            f'cognito-idp.{region}.amazonaws.com/{user_pool_id}': id_token
        }
    )['IdentityId']
    
    credentials = identity_client.get_credentials_for_identity(
        IdentityId=identity_id,
        Logins={
            f'cognito-idp.{region}.amazonaws.com/{user_pool_id}': id_token
        }
    )['Credentials']
    
    return credentials


class ResponseHandler:
    def __init__(self, debug_img_folder: Optional[str] = None) -> None:
        self.debug_img_folder = debug_img_folder
        if debug_img_folder:
            makedirs(TESTS_IMG / debug_img_folder, exist_ok=True)
        self.response_text = None
        self.agent_metrics = None
    
    def handle_tool_use(self, name: str, input: dict, image_str: Optional[str] = None):
        if self.debug_img_folder and name in UI_TOOLS and image_str:
            image = Image.open(BytesIO(base64.b64decode(image_str)))
            filename = Path(input['image_path']).name
            image.save(TESTS_IMG / self.debug_img_folder / filename, 'PNG')

    def handle_result(self, result: dict):
        self.response_text = result['response']
        self.agent_metrics = result['metrics']['agent']


class AgentClient:
    def __init__(self, username, password) -> None:
        outputs = get_stack_outputs()

        self.agent_runtime_arn = outputs['AgentRuntimeArn']

        credentials = authenticate(
            outputs['CognitoUserPoolId'],
            outputs['CognitoClientIdStaticUI'],
            outputs['CognitoIdentityPoolId'],
            username,
            password
        )
        self.client = boto3.client(
            'bedrock-agentcore',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretKey'],
            aws_session_token=credentials['SessionToken'],
            config=Config(read_timeout=600)
        )
    
    def invoke_agent(self, prompt: str, coordinates: list, history: Optional[list]) -> Iterator[dict]:
        response = self.client.invoke_agent_runtime(
            agentRuntimeArn=self.agent_runtime_arn,
            runtimeSessionId=str(uuid.uuid4()),
            contentType='application/json',
            accept='text/event-stream',
            payload=json.dumps({
                "message": prompt,
                "coordinates": coordinates,
                "history": history
            }).encode('utf-8')
        )
        
        for line in response["response"].iter_lines(chunk_size=10):
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
            yield json.loads(line)

    def _handle_msg_type(self, handler, msg_type):
        method_name = f"handle_{msg_type}"
        return hasattr(handler, method_name)

    def handle_agent_messages(self, handler, prompt: str, coordinates: list, history: Optional[list]=None):
        if self._handle_msg_type(handler, 'user_message'):
            history = deepcopy(handler.history)
            handler.handle_user_message(prompt)
        else:
            history = None
        
        for event in self.invoke_agent(prompt, coordinates, history):
            msg_type = event.get('msg_type')
            
            if msg_type == 'text' and self._handle_msg_type(handler, 'text_message'):
                handler.handle_text_message(event.get('text'))
            
            elif msg_type == 'toolUse' and self._handle_msg_type(handler, 'tool_use'):
                handler.handle_tool_use(
                    event.get('name'),
                    event.get('input'),
                    event.get('image'))
            
            elif msg_type == 'toolResult' and self._handle_msg_type(handler, 'tool_result'):
                handler.handle_tool_result(event.get('name'), [content['text'] for content in event['content']])
            
            elif msg_type == 'result' and self._handle_msg_type(handler, 'result'):
                handler.handle_result(event.get('result'))
            
            elif event.get('error'):
                print(f"Error: {event.get('message', event.get('error'))}", file=sys.stderr)

    def get_response(self,
                     prompt: str,
                     coordinates: list,
                     debug_img_folder: Optional[str] = None) -> ResponseHandler:
        handler = ResponseHandler(debug_img_folder)
        self.handle_agent_messages(handler, prompt, coordinates)
        return handler
