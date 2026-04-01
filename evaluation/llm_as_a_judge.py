from strands import Agent
from strands.models import BedrockModel

from diskcache import Cache
from json_repair import repair_json


MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
TEMPERATURE = 0.2

CACHE = Cache("/tmp/.cache/Agent_Evaluator")

SYSTEM_PROMPT = """
You are tasked with the evaluation of answers returned by an AI Agent analysing satellite images.
You will receive the input User Question, the Expected Answer, and the Generated Answer.

The expected answer will be typically more succinct than the generated one.
You will have to check that the Generated Answer contains the information provided in the Expected Answer.

Return an overall score from 0 to 1:
* 0: if the Generated Answer does not contain the information provided in the Expected Answer.
* 1: if the Generated Answer contains the information provided in the Expected Answer.

If the Expected Answer is a number and the Generated Answer does not match it, degrade the score accordingly to the percentage error. For example, for a 25%% error return a 0.75 score.

You should return a single JSON object with the following format:
{
    "score": 0 to 1,
    "rationale": "rationale for the provided score"
}
""".strip()


class Agent_Evaluator:
    def __init__(self):
        self.agent = Agent(
            model = BedrockModel(
                model_id=MODEL_ID,
                temperature=TEMPERATURE,
            ),
            system_prompt=SYSTEM_PROMPT,
            tools=[
            ],
            callback_handler=None)

    def evaluate(self, question, expected_answer, generated_answer, cached=True):
        cache_key = str([
            ("model_id", MODEL_ID),
            ("temperature", TEMPERATURE),
            ("system_prompt", SYSTEM_PROMPT),
            ("question", question),
            ("expected", expected_answer),
            ("generated", generated_answer),
        ])
        if cached and cache_key in CACHE:
            return CACHE[cache_key]

        response = self.agent(f"User Question: {question}\nExpected Answer: {expected_answer}\nGenerated Answer: {generated_answer}")
        
        response_data = repair_json(str(response), return_objects=True)
        CACHE[cache_key] = response_data
        return response_data
