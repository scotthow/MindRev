
import os, sys, random
from flask import current_app

###############################################################################
# Global Variables

# Game ID (temp)
GAME_ID = "game-001" # temp, will be determined

# Get current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
print(f"Parent directory: {parent_dir}")

# Make dirs if they don't exist
os.makedirs(f'{parent_dir}/data', exist_ok=True)
os.makedirs(f"{parent_dir}/data/game_data/{GAME_ID}", exist_ok=True)
os.makedirs(f"{parent_dir}/data/game_data/{GAME_ID}/memory", exist_ok=True)
os.makedirs(f'{parent_dir}/data/logs', exist_ok=True)

# Set data dir
DATA_DIR = os.path.join(parent_dir, 'data', 'game_data', GAME_ID)

game_type_path = "scripts/default"
genre_list = ["politics", "artificial intelligence", "health technology", "finance"]
element_list = ["romance", "revenge", "dark comedy"]
ed_topic = "Natural Language Processing"
characters = [
    ("Ava Armitage", "Venture Capitalist", "Biotechnology"),
    ("Soren Sepulveda", "College Professor", "Natural Language Processing"),
    ("Kai Zhang", "Software Developer", "Reinforcement Learning")
]
player_name = "Blank"

def init_app(app):
    with app.app_context():
        # app.config['GAME_ID'] = GAME_ID
        # app.config['DATA_DIR'] = os.path.join(app.root_path, 'data', 'game_data', GAME_ID)
        app.config['game_type_path'] = game_type_path
        app.config['genre'] = random.choice(genre_list)
        app.config['element'] = random.choice(element_list)
        app.config['ed_topic'] = ed_topic
        app.config['characters'] = characters
        app.config['player_name'] = player_name

    return app
