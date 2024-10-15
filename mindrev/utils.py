import os, json, time, random, re, logging, ast, functools, inspect, tiktoken
from typing import Callable, Any
from flask import jsonify, Response
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from datetime import datetime 
from openai import OpenAI

from mindrev.settings import GAME_ID

################################################################################
# File setup

MEMORY_FILE = f'data/game_data/{GAME_ID}/memories.json'

################################################################################
# Set up logging

today = datetime.today().strftime('%Y-%m-%d:%H:%M:%S')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a file handler to save logs to a text file
file_handler = logging.FileHandler(f'data/logs/model_utils_{today}.log')
file_handler.setLevel(logging.INFO)

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

################################################################################
# Model configuration

import google.generativeai as genai
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
genai.configure(api_key=GOOGLE_API_KEY)

safety_settings = [
{
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_ONLY_HIGH"
},
{
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_ONLY_HIGH"
},
{
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE"
},
{
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
},
]

creative_config = {
"temperature": 0.8,
"top_p": 1,
"top_k": 6,
# "max_output_tokens": 4096,
}

dull_config = {
"temperature": 0,
"top_p": 1,
"top_k": 1,
"max_output_tokens": 100,
}

model_config = {
"temperature": 0.2,
"top_p": 1,
"top_k": 1,
"max_output_tokens": 100,
}

# Attempt to import and configure Gemini API 
try:
    import google.generativeai as genai
    genai.configure(api_key=GOOGLE_API_KEY)
    MODEL = genai.GenerativeModel(model_name="gemini-1.5-flash-latest", generation_config=model_config, safety_settings=safety_settings)
    MODEL2 = genai.GenerativeModel(model_name="gemini-1.5-pro-exp-0801", generation_config=creative_config, safety_settings=safety_settings)
    DULL_MODEL = genai.GenerativeModel(model_name="gemini-1.0-pro-latest", generation_config=dull_config, safety_settings=safety_settings)
    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("Failed to import google.generativeai")
    GEMINI_AVAILABLE = False
except Exception as e:
    logger.warning(f"Failed to configure Gemini API: {str(e)}.")
    GEMINI_AVAILABLE = False

EMBED_MODEL = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
GPT_AVAILABLE = True


################################################################################
# Utility functions

def json_str_processing(input_str):
  input_str = input_str[input_str.find('{'):]
  input_str = input_str[:input_str.rfind('}')] + '}'
  input_str = input_str.replace("',", '",').replace(",'", ',"').replace("{'", '{"').replace("'}", '"}')
  input_str = input_str.replace(" '", ' "').replace("':", '":').replace(":'", ':"').replace(".'", '."').replace("\\'", "'")
  input_str = input_str.replace("['", '["').replace("']", '"]')
  try:
    final_json = json.loads(input_str)
  except:
    generation_config= {
      "temperature": 0,
      "top_p": 1,
      "top_k": 1,
      # "max_output_tokens": 4096,
      }
    model = genai.GenerativeModel(model_name="gemini-1.0-pro-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings)
    json_prompt = f'''Correct the syntax of the below json:
    {input_str}

    Use double quotation marks to enclose keys and string elements.
    if correct, output original json.

    output json:{{}}'''
    json_corrected = model.generate_content(json_prompt).text
    print(json_corrected)
    json_corrected = json_corrected[json_corrected.find('{'):]
    json_corrected = json_corrected[:json_corrected.rfind('}')] + '}'
    final_json = json.loads(json_corrected)
  return final_json
 

def gen_response(prompt, model):
    for i in range(10):
        print(i+1, 'th try')
        try:
            return model.generate_content(prompt).text
        except:
            print("Generation Failed: going to sleep (45s)")
            time.sleep(45)
        else:
            break
    else:
        return "{'Error': 'API Temporarily Unavailable! Try Again Later!'}"
    


# Alt version - SBH
def extract_trust_level(response, trust_level):
    # Find the position of "Trust level:" in the response
    start_index = response.find("Trust level:")
    if start_index != -1:
        # Extract the part of the response starting from "Trust level:"
        trust_level_part = response[start_index:]
        # Use regular expression to find the float number
        match = re.search(r"\d+\.\d+", trust_level_part)
        if match:
            return float(match.group(0))
    return trust_level


def track_tokens(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Tokenizer
        tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

        # Extract prompts from function
        prompts = extract_prompts(func, *args, **kwargs)

        # Tokenize input (including all prompts)
        input_tokens = sum(len(tokenizer.encode(prompt)) for prompt in prompts)

        # Call the original function
        result = func(*args, **kwargs)

        # Handle different return types
        if isinstance(result, (dict, list)):
            output_text = json.dumps(result)
        elif isinstance(result, Response):
            output_text = result.get_data(as_text=True)
        else:
            output_text = str(result)

        # Tokenize output
        output_tokens = len(tokenizer.encode(output_text))

        # Sum tokens for this call
        total_tokens = input_tokens + output_tokens

        # File path and log entry
        os.makedirs(f"data/game_data/{GAME_ID}", exist_ok=True)
        file_path = f"data/game_data/{GAME_ID}/plot_gen_tokens_used.txt"
        log_entry = f"{func.__name__},{input_tokens},{output_tokens},{total_tokens}\n"

        # Append to the log file
        with open(file_path, "a") as f:
            f.write(log_entry)

        return result

    return wrapper

def extract_prompts(func: Callable[..., Any], *args, **kwargs) -> list:
    # Get the function's source code
    source = inspect.getsource(func)

    # Find all string assignments that might be prompts
    prompt_candidates = re.findall(r'(\w*prompt\w*)\s*=\s*f?"""[\s\S]*?"""', source)

    formatted_prompts = []

    for prompt_var in prompt_candidates:
        # Extract the prompt template
        prompt_match = re.search(rf'{prompt_var}\s*=\s*f?"""([\s\S]*?)"""', source)
        if prompt_match:
            prompt_template = prompt_match.group(1)

            # Format the prompt with args and kwargs
            try:
                formatted_prompt = prompt_template.format(**kwargs)
                formatted_prompts.append(formatted_prompt)
            except KeyError as e:
                # If formatting fails, append the template as is
                formatted_prompts.append(prompt_template)

    return formatted_prompts