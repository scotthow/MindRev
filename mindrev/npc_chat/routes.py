from flask import (Flask, render_template, request, jsonify, redirect, url_for, 
                   Blueprint, current_app as app)
from flask_sqlalchemy import SQLAlchemy
from json import JSONEncoder
import os, sys, json, logging, random, re, time
from PIL import Image
from openai import OpenAI
from mindrev.utils import (
    MODEL, MODEL2, DULL_MODEL, GEMINI_AVAILABLE, GPT_AVAILABLE, GAME_ID,
    logger, json_str_processing, track_tokens
)
from mindrev.functions import rewrite_file_path, merge_dicts

# NPC Chat

class NPCEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, NPC):
            return {attr: getattr(obj, attr) for attr in obj.__slots__}
        return super().default(obj)

class NPC:
    __slots__ = ('name', 'gender', 'image_file', 'profession', 'expertise', 'job_title', 
                 'backstory', 'secret', 'relationships', 'personality', 'speaking_style', 
                 'hobby', 'artifact', 'fallback_responses')

    def __init__(self, npc_data):
        for attr in self.__slots__:
            setattr(self, attr, npc_data.get(attr, ''))
        self.image_file = f"{npc_data.get('image', '')}"
        self.fallback_responses = {
            "hello": ["Hi.", "Can't talk right now.", "Nope."]
        }

    def respond(self, message):
        if GEMINI_AVAILABLE:
            try:
                prompt = self._generate_prompt(message)
                response = MODEL2.generate_content(prompt)
                return response.text
            except Exception as e:
                logger.error(f"Error using Gemini model: {str(e)}")
                if GPT_AVAILABLE:
                    print('SWITCHING TO GPT')
                    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
                    completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    temperature=0.5,
                    top_p=0.5,
                    messages=[
                        {"role": "system", "content": "You are an Creative Writing Professor at the University of Chicago."},
                        {"role": "user", "content": prompt}
                        ]
                    )
                    return completion.choices[0].message.content
        else:
            return self.fallback_response(message)

    def _generate_prompt(self, message):
        # print(f"INFO: {', '.join(f'{attr}: {getattr(self, attr)}' for attr in self.__slots__ if attr not in ['name', 'fallback_responses', 'image_file'])})")
        return f"""
        # Context
        You are {self.name}, a non-person Character (NPC) in a fictional interactive game where the player must seek clues to solve a crime and win the game.
        Remember these background details about your life: {', '.join(f'{attr}: {getattr(self, attr)}' for attr in self.__slots__ if attr not in ['name', 'fallback_responses', 'image_file'])}
        
        # IMPORTANT: Make sure all of your responses follow these guidelines:

        ## Conversational Guidelines:
        - You are allowed to use information outside the context if it is necessary to answer the questions regarding your job, profession, and expertise.
        - Keep your answers clear and concise. Avoid offering help. Never say 'How may I assist you today?' or 'How can I help you?'.
        - If asked about the killer and/or the victim and/or the suspect, respond with aloofness and innocence. Act as if you have no \
          idea why the player is asking such a ridiculous question.
        - Always stay in character. Do not break character. You are NOT a chatbot. You are a character in a game. You are not aware of the game.
        - You are interacting with the player. The history of your conversation with the player is given in the Relevant Conversation History section \
           below. Before you respond, compare the player's conversation history with their current query and adjust your response accordingly.
        - Review the conversation history before responding. Respond based on the player query and conversation history!!!
        - If the conversation history is empty, assume you are talking to a stranger. 
        - NEVER return a timestamp in your response. The timestamp is only for you to keep track of the conversation history.
        - NEVER ask "How may I assist you today?" or "How may I be of assistance", or anything similar.
        - NEVER let it known what your role in the game is. 
        - NEVER use `[your name]` or `[your character name]` in your response.
        - NEVER use subtext in your response. Always be direct and clear in your responses.

        # Conversation History with the Player:
        ``
        # Phsychological Profile:
        Keep your responses informational but short. Keep in character, remember to use your tone of speaking and personality when your response to this message: `{message}`
        """
    def fallback_response(self, message):
        message = message.lower()
        for key, responses in self.fallback_responses.items():
            if key in message:
                return random.choice(responses)
        return "I'm sorry. I'm very busy, we'll chat later."

def load_npcs_from_json(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return {npc_data['name']: NPC(npc_data) for npc_data in data['character_info'].values()}
    except Exception as e:
        # logger.error(f"Error loading NPCs from JSON: {str(e)}")
        return {}

# Game Creation Blueprint
npc_chat_bp = Blueprint('npc_chat', __name__)

@npc_chat_bp.route('/npc-chat', methods=['GET', 'POST'])
def npc_chat():
    npcs = load_npcs_from_json("data/game_data/game-001/universe_with_events.json")
    if request.method == 'POST':
        data = request.json
        npc = npcs.get(data.get('npc_name'))
        if not npc:
            return jsonify({"error": "Invalid NPC name"}), 400
        return jsonify({"response": npc.respond(data.get('message'))})
    return render_template('npc_chat.html', npcs={name: NPCEncoder().default(npc) for name, npc in npcs.items()})
