import json, os, re, ast, functools, tiktoken, inspect
from typing import Callable, Any
from flask import jsonify, Response
from datetime import datetime


def json_str_processing_v1(input_str, gen_ai_model):
  input_str = input_str[input_str.find('{'):]
  input_str = input_str[:input_str.rfind('}')] + '}'
  input_str = input_str.replace("',", '",').replace(",'", ',"').replace("{'", '{"').replace("'}", '"}')
  input_str = input_str.replace(" '", ' "').replace("':", '":').replace(":'", ':"').replace(".'", '."').replace("\\'", "'")
  input_str = input_str.replace("['", '["').replace("']", '"]')
  try:
    final_json = json.loads(input_str)
  except:
    json_prompt = f'''Correct the syntax of the below json:
    {input_str}

    Use double quotation marks to enclose keys and string elements.
    if correct, output original json.

    output json:{{}}'''
    json_corrected = gen_ai_model.generate_content(json_prompt).text
    # print(json_corrected)
    json_corrected = json_corrected[json_corrected.find('{'):]
    json_corrected = json_corrected[:json_corrected.rfind('}')] + '}'
    final_json = json.loads(json_corrected)
  return final_json


def merge_json(json, json_key):
    """
    Can also do the following, but the current is more efficient and robust:

    for k, v in universe['character_info'].items():
    new_v = v | personality_info[k]
    universe['character_info'][k] = new_v
    
    """
    # Merge the Dictionaries
    for key, val in json_key.items():
        if key in json["character_info"]:
            json["character_info"][key].update(val)
        else:
            json["character_info"][key] = val
    
    return json

def reorganize_json(file_path):
    # Read JSON data from file
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    # Extract player name and NPC name
    player_name = "player"
    npc_name = next(key for key in data[0].keys() if key != "player" and key != "timestamp")
    
    # Separate histories
    npc_history = []
    player_history = []
    for item in data:
        timestamp = datetime.fromisoformat(item['timestamp'])
        npc_history.append((timestamp, item[npc_name].split('\n')[0]))
        player_history.append((timestamp, item['player']))
    
    # Sort histories by timestamp (most recent first)
    npc_history.sort(reverse=True)
    player_history.sort(reverse=True)
    
    # Format output
    output = "# Conversation History:\n\n"
    output += f"{npc_name} history:\n"
    for timestamp, response in npc_history:
        output += f"{timestamp}: {response}\n"
    output += f"\n{player_name} history:\n"
    for timestamp, response in player_history:
        output += f"{timestamp}: {response}\n"

    # Save the output to a file
    output_file_path = f"game_data/game1/memory/chat_history_{npc_name}.txt"
    with open(output_file_path, 'w') as output_file:
        output_file.write(output)

    return output, output_file_path


def reorganize_json_v1(file_path):
    """
    Reorganize the JSON data from the file and save the output to a text file. For
    human and LLM readability. 
    """
    # Read JSON data from file
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    # Extract player name and NPC name
    player_name = "player"
    npc_name = next(key for key in data[0].keys() if key != "player" and key != "timestamp")
    
    # Separate histories
    npc_history = []
    player_history = []
    for item in data:
        timestamp = datetime.fromisoformat(item['timestamp'])
        npc_history.append((timestamp, item[npc_name].split('\n')[0]))
        player_history.append((timestamp, item['player']))
    
    # Sort histories by timestamp (most recent first)
    npc_history.sort(reverse=True)
    player_history.sort(reverse=True)
    
    # Format output
    output = "# Conversation History:\n\n"
    output += f"{npc_name} history:\n"
    for timestamp, response in npc_history:
        output += f"{timestamp}: {response}\n"
    output += f"\n{player_name} history:\n"
    for timestamp, response in player_history:
        output += f"{timestamp}: {response}\n"

    # Save the output to a file
    output_file_path = f"game_data/game1/chat_history_{npc_name}.txt"
    with open(output_file_path, 'w') as output_file:
        output_file.write(output)

    return output, output_file_path


def rewrite_file_path(file_path):
    # Split the input path into its components
    components = file_path.split('/')
    
    # Extract the file name
    file_name_with_extension = components[-1]
    
    # Remove the extension from the file name
    file_name = file_name_with_extension.split('.')[0]
    
    # Create the new path
    new_path = f"static/images/{file_name}.jpg"
    
    return new_path

def merge_dicts(dict1, dict2):
    """
    Recursively merge two dictionaries.
    """
    for key, value in dict2.items():
        if isinstance(value, dict):
            dict1[key] = merge_dicts(dict1.get(key, {}), value)
        else:
            dict1[key] = value
    return dict1


