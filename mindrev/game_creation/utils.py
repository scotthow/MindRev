import os, json
from flask import current_app 


def save_universe_to_json(json_data, data_dir):
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    file_path = os.path.join(data_dir, 'universe.json')
    with open(file_path, 'w') as f:
        json.dump(json_data, f, indent=4)
    
    current_app.logger.debug(f"Universe saved to {file_path}")