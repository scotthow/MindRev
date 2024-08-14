from flask import (Flask, render_template, request, jsonify, redirect, url_for, 
                   Blueprint, current_app as app)
from flask_sqlalchemy import SQLAlchemy
from json import JSONEncoder
import os, sys, json, logging, random, re, time
from PIL import Image
from openai import OpenAI

from mindrev.utils import (
    MODEL, MODEL2, DULL_MODEL, GEMINI_AVAILABLE, GPT_AVAILABLE,
    logger, json_str_processing, track_tokens
)
from mindrev.settings import GAME_ID, DATA_DIR
from mindrev.game_creation.utils import save_universe_to_json
from mindrev.functions import rewrite_file_path, merge_dicts

# Game Creation Blueprint
game_creation_bp = Blueprint('game_creation', __name__)

###############################################################################
###############################################################################
# Game Creation Route

@game_creation_bp.route('/game-creation')
def game_creation():
    # Load the universe data from the JSON file
    
    file_path = f"{DATA_DIR}/universe.json"
    
    try:
        with open(file_path, 'r') as f:
            universe = json.load(f)
    except FileNotFoundError:
        universe = {
            "character_info": {
                "npc_1": {},
                "npc_2": {},
                "npc_3": {}
            }
        }
    
    return render_template('game_creation.html', universe=universe)


################################################################################
################################################################################
# Story Setting Generation

@game_creation_bp.route('/generate_story_setting', methods=['POST'])
@track_tokens # Decorator to track tokens
def generate_story_setting():

    _universe = {
    "character_info": {
        "npc_1": {
            "name": "",
            "gender": "",
            "profession": "",
            "expertise": "",
        },
        "npc_2": {
            "name": "",
            "gender": "",
            "profession": "",
            "expertise": "",
        },
        "npc_3": {
            "name": "",
            "gender": "",
            "profession": "",
            "expertise": "",
        }
    },
    "genre": "",
    "element": "",
    "educational_topic": "",
    "story_setting_event_name": "",
    "story_setting_event_desc": "",
    "story_setting_event_purp": ""
}
    data = request.json
    genre = data['genre'] # from the form
    element = data['element'] # from the form
    educational_topic = data['educationalTopic'] # from the form

    if not genre or not element or not educational_topic:
        return jsonify({'error': 'Missing required fields'}), 400

    # Update universe dict with genre, element, and educational topic
    _universe['genre'] = genre
    _universe['element'] = element
    _universe['educational_topic'] = educational_topic

    prompt = f"""
    You are a highly intelligent and creative former Hollywood scriptwriter and current game developer
    with a keen eye for detail and unrivaled ability to create compelling fictional educational games. 
    
    # Important information:
    Genre: {genre}
    Story Element: {element}
    Educational Topic: {educational_topic}

    Based on the given genre, story element, and educational topic, create a unique and intriguing story setting.

    Provide the following information in JSON format:
    1. Event Name: A catchy name for the social event where the mystery adventure takes place, incorporating elements from the {genre} genre and the {educational_topic}.
    2. Event Description: A brief description of the event, including its location and atmosphere. The description should reflect the {genre} genre, include aspects of the {element} story element, and incorporate the {educational_topic}.
    3. Event Purpose: The official reason for the gathering, which will bring the characters together. This should tie into the {genre} genre, the {element} story element, and the {educational_topic}.

    Output the JSON in the following format:
    {{
        "event_name": "...",
        "event_description": "...",
        "event_purpose": "..."
    }}
    """

    app.logger.debug(f"Prompt: {prompt}")

    try:
        response = MODEL2.generate_content(prompt).text
        story_setting = json_str_processing(response)
        app.logger.debug(f"Processed response: {story_setting}")
        app.logger.debug(f"Raw response: {response}")

    except Exception as e:
        app.logger.warning(f"MODEL2 failed: {str(e)}. Trying OPEN AI model.")
        try:
            app.logger.warning("OPEN AI model will be used. Account will be charged!")
            print("WARNING: OPEN AI model is being used. Account will be charged!")
            
            client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.5,
                top_p=0.5,
                messages=[
                    {"role": "system", "content": "You are a Professor of Creative Writing at the University of Chicago."},
                    {"role": "user", "content": prompt}
                ]
            )
            response = completion.choices[0].message.content
            story_setting = json_str_processing(response)
            app.logger.debug(f"Processed response: {story_setting}")
        except Exception as e:
            app.logger.warning(f"OPEN AI model failed: {str(e)}. Trying DULL_MODEL as a last resort.")
            try:
                response = MODEL.generate_content(prompt).text
                story_setting = json_str_processing(response)
                app.logger.debug(f"Processed response: {story_setting}")
            except Exception as e:
                app.logger.error(f"All attempts failed in generate_characters: {str(e)}")
                return jsonify({"error": str(e)}), 500
    
    # Update universe dict with story setting
    _universe['story_setting_event_name'] = story_setting['event_name']
    _universe['story_setting_event_desc'] = story_setting['event_description']
    _universe['story_setting_event_purp'] = story_setting['event_purpose']

    # Save updated universe dict as JSON file
    save_universe_to_json(_universe, DATA_DIR)

    # Return the story setting
    return jsonify(story_setting)

        ################################################################################
        ## Sub query
        # character_info = universe['character_info']
        # sub_prompt = f"""
        #     You are an expert in {educational_topic}. For each NPC in the following json 
        #     object, create a description of 3 areas of expertise within 
        #     {educational_topic}, i.e., subtopics within the educational topic.

        #     For each NPC, fill in their respective 'expertise' with your description. 
        #     DO NOT change the 'name' or 'profession' fields.

        #     # Output format: {{
        #         "character_info": {{
        #         "npc_1": {{
        #             "name": "",
        #             "profession": "",
        #             "expertise": "<fill in>",
        #         }},
        #         "npc_2": {{
        #             "name": "",
        #             "profession": "",
        #             "expertise": "<fill in>",
        #         }},
        #         "npc_3": {{
        #             "name": "",
        #             "profession": "",
        #             "expertise": "<fill in>",
        #                 }}
        #             }}
        #         }}

        #     # Json object: ```{character_info}```. 
        # """
        
        # # Response
        # character_expertise = MODEL2.generate_content(sub_prompt).text
        # character_expertise_to_universe = json_str_processing(character_expertise)

        # # Updating the universe with the new character_info
        # universe["character_info"].update(character_expertise_to_universe["character_info"])

        # Save universe dict as JSON file

################################################################################
################################################################################
# Character Generation

@game_creation_bp.route('/generate_characters', methods=['POST'])
@track_tokens # Decorator to track tokens
def generate_characters():
    app.logger.debug("generate_characters function called")

    # Read from universe.json
    with open(os.path.join(DATA_DIR, "universe.json"), 'r') as f:
        universe = json.load(f)

    character_info = universe['character_info']
    educational_topic = universe['educational_topic']

    # Get all available videos
    male_video_dir = os.path.join(app.static_folder, 'videos', 'male')
    female_video_dir = os.path.join(app.static_folder, 'videos', 'female')

    male_videos = [f for f in os.listdir(male_video_dir) if f.endswith('.mp4')]
    female_videos = [f for f in os.listdir(female_video_dir) if f.endswith('.mp4')]

    # Create a pool of available videos with their full paths
    available_videos = {
        'male': [os.path.join('videos', 'male', video) for video in male_videos],
        'female': [os.path.join('videos', 'female', video) for video in female_videos]
    }

    # Function to extract first name from filename
    def extract_name(filename):
        return os.path.splitext(filename)[0].split('_')[0]

    # Function to get used videos from the text file
    def get_used_videos():
        used_videos_file = os.path.join('data', 'game_data', 'game-001', 'used_videos.txt')

        # Check if the file exists
        if not os.path.exists(used_videos_file):
            os.makedirs(os.path.dirname(used_videos_file), exist_ok=True)
            open(used_videos_file, 'w').close()  # Create an empty file
            return set()

        # If the file exists, check the number of rows, if the num of rows is more than 10, clear the file, else return the used videos
        with open(used_videos_file, 'r+') as f:
            lines = f.readlines()
            if len(lines) > 10:
                f.seek(0)
                f.truncate()  # Clear the file content
                return set()
            else:
                return set(line.strip() for line in lines)

    # Function to add a used video to the text file
    def add_used_video(video):
        used_videos_file = os.path.join('data', 'game_data', 'game-001', 'used_videos.txt')
        with open(used_videos_file, 'a') as f:
            f.write(f"{video}\n")

    used_videos = get_used_videos()

    # Remove used videos from available videos
    for gender in ['male', 'female']:
        available_videos[gender] = [video for video in available_videos[gender] if os.path.basename(video) not in used_videos]

    updated_character_info = {}

    # Randomly choose the gender for the first NPC
    first_gender = random.choice(['male', 'female'])
    genders = [first_gender, 'female' if first_gender == 'male' else 'male', first_gender]

    for i, npc in enumerate(character_info.keys()):
        gender = genders[i]

        if available_videos[gender]:
            # Choose a random video from the available set
            chosen_video = random.choice(available_videos[gender])
            name = extract_name(os.path.basename(chosen_video))
            
            # Remove the chosen video from the available set and add it to used videos
            available_videos[gender].remove(chosen_video)
            add_used_video(os.path.basename(chosen_video))
        else:
            # If no videos are available, use the specified default video
            if gender == 'male':
                chosen_video = os.path.join('videos', 'male', 'Ben_Davis_M20_001.mp4')
            else:
                chosen_video = os.path.join('videos', 'female', 'Abigal_Loevinger_002.mp4')
            name = extract_name(os.path.basename(chosen_video))

        updated_character_info[npc] = {
            "name": name,
            "gender": gender.capitalize(),
            "video": chosen_video,
            "image": rewrite_file_path(chosen_video),
            "profession": "<fill in>",
            "expertise": "<fill in>",
        }

    # Update the universe dictionary
    universe["character_info"] = updated_character_info

    # Generate profession and expertise using the LLM
    prompt = f"""
    You are an expert in {educational_topic}. For each NPC in the following json 
    object, fill in the following information:

    1. Profession: The profession or role of the NPC.
    2. Expertise: A brief description of the NPC's expertise. The expertise will 
    depend on the profession and be related to {educational_topic}. For example,
    if the NPC is a professor, the expertise could be in a specific area or subfield 
    of {educational_topic}. If the NPC is venture capitalist, the expertise could be 
    in investment strategies for AI companies using {educational_topic} technology.

    # Output format: {{
        "character_info": {{
        "npc_1": {{
            "profession": "<fill in>",
            "expertise": "<fill in>",
        }},
        "npc_2": {{
            "profession": "<fill in>",
            "expertise": "<fill in>",
        }},
        "npc_3": {{
            "profession": "<fill in>",
            "expertise": "<fill in>",
            }}
        }}
    }}

    # Json object: ```{json.dumps(updated_character_info)}```. 
    """

    try:
        app.logger.debug("Generating character information using MODEL2")
        character_expertise = MODEL2.generate_content(prompt).text
        character_expertise_to_universe = json_str_processing(character_expertise)
        # app.logger.debug(f"Raw character expertise: {character_expertise}")
        # character_expertise_to_universe = json_str_processing(character_expertise)
        # app.logger.debug(f"Processed character expertise: {character_expertise_to_universe}")
    except Exception as e:
        app.logger.warning(f"MODEL2 failed: {str(e)}. Trying OPEN AI model.")
        try:
            app.logger.warning("OPEN AI model will be used. Account will be charged!")
            print("WARNING: OPEN AI model is being used. Account will be charged!")
            
            client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.5,
                top_p=0.5,
                messages=[
                    {"role": "system", "content": "You are an English Professor at the University of Chicago."},
                    {"role": "user", "content": prompt}
                ]
            )

            character_expertise = completion.choices[0].message.content
            character_expertise_to_universe = json_str_processing(character_expertise)
            # app.logger.debug(f"Raw character expertise from OPEN AI: {character_expertise}")
            # character_expertise_to_universe = json_str_processing(character_expertise)
            # app.logger.debug(f"Processed character expertise from OPEN AI: {character_expertise_to_universe}")
        except Exception as e:
            app.logger.warning(f"OPEN AI model failed: {str(e)}. Trying DULL_MODEL as a last resort.")
            try:
                character_expertise = MODEL.generate_content(prompt).text
                character_expertise_to_universe = json_str_processing(character_expertise)
                # app.logger.debug(f"Raw character expertise from DULL_MODEL: {character_expertise}")
                # character_expertise_to_universe = json_str_processing(character_expertise)
                # app.logger.debug(f"Processed character expertise from DULL_MODEL: {character_expertise_to_universe}")
            except Exception as e:
                app.logger.error(f"All attempts failed in generate_characters: {str(e)}")
                return jsonify({"error": str(e)}), 500
            
    # Update only profession and expertise
    for npc, info in character_expertise_to_universe["character_info"].items():
        if npc in universe["character_info"]:
            universe["character_info"][npc].update({
                "profession": info["profession"],
                "expertise": info["expertise"]
            })

    app.logger.debug(f"Updated universe: {universe}")

    # Save updated universe dict as JSON file
    save_universe_to_json(universe, DATA_DIR)

    return jsonify(universe["character_info"])


################################################################################
################################################################################
# Generate Personas

@game_creation_bp.route('/generate_character_details', methods=['POST'])
@track_tokens # Decorator to track tokens
def generate_character_details():

    # Read from universe.json
    with open(os.path.join(DATA_DIR, "universe.json"), 'r') as f:
        universe = json.load(f)

    # Consider this in the prompt when needed: {json.dumps(universe, indent=2)}

    prompt = f"""
    You are an expert in creating compelling characters for murder mystery games. 
    Based on the following universe information, generate detailed character profiles:

    {universe}

    For each character, fill in the missing information:
     - Backstory (Private details that makes a compelling character)
     - Secret (A revelation that would be personally damaging to this character. This secret could lead to a 
     costly divorce and/or major loss of reputation and/or criminal prosecution. This secret should be 
     the motivation for a serious crime and/or wrongdoing.
     - Relationships (Explain how each character knows the other two characters in two sentences)
     - Job Title (Job title and company of each character, where the company may be the same or different for each)
     - Personality (Describe the personality traits of each character)
     - Speaking tone and style (Provide details on how they speak, especially with newly met strangers.)
     - Hobby (A hobby that the character is fascinated with, related to their background and/or secret)
     - Artifact (An item of significance to the character, related to their background and/or secret)

    Provide the information in the following JSON format:
    {{
        "character1_name": {{
            "job_title": "...",
            "backstory": "...",
            "secret": "...",
            "relationships": "...",
            "personality": "...",
            "speaking_style": "...",
            "hobby": "...",
            "artifact": "..."
        }},
        "character2_name": {{
            ...
        }},
        "character3_name": {{
            ...
        }}
    }}
    """

    try:
        response = MODEL2.generate_content(prompt).text
        character_details = json_str_processing(response)
        if character_details is None:
            print("Failed to parse character details JSON")
    except Exception as e:
        try:
            app.logger.warning(f"MODEL2 failed: {str(e)}. Trying DULL_MODEL model.")
            response = MODEL.generate_content(prompt).text
            character_details = json_str_processing(response)
        except Exception as e:
            try:
                app.logger.warning(f"DULL_MODEL failed: {str(e)}. Trying MODEL2 once more.")
                # Wait 45 seconds before trying again
                time.sleep(45)
                response = MODEL.generate_content(prompt).text
                character_details = json_str_processing(response)
            except Exception as e:
                app.logger.warning(f"MODEL2 failed: {str(e)}. Models failed.")
                return jsonify({"error": str(e)}), 500

    # Merge new character details with existing information
    for i, (npc_name, details) in enumerate(character_details.items(), start=1):
        npc_key = f'npc_{i}'
        if npc_key in universe['character_info']:
            universe['character_info'][npc_key] = merge_dicts(universe['character_info'][npc_key], details)
        else:
            universe['character_info'][npc_key] = details

    # Save updated universe dict as JSON file
    save_universe_to_json(universe, DATA_DIR)

    return jsonify(universe['character_info'])
    

################################################################################
################################################################################
# Event Generation

@game_creation_bp.route('/generate_events', methods=['POST'])
@track_tokens # Decorator to track tokens
def generate_events():
    read_file = 'universe.json'
    write_file = 'universe_with_events.json'

    # Read from universe.json
    with open(os.path.join(DATA_DIR, read_file), 'r') as f:
        universe = json.load(f)

    # Event Creation
    event_prompt = f""" \
    You are a highly intelligent and creative former Hollywood scriptwriter and current expert narrative designer for a gaming company with a keen eye for detail and unrivaled ability to weave compelling stories into interactive games.

    Your task is to develop 3 sets of fictional events between NPCs (non-playable characters) prior to a final confrontation.

    Here are the exact rules to follow when creating the events: \
    - Generate a series of 3 events (Series A) between NPC1 and NPC2.
    - Generate a series of 3 events (Series B) between NPC1 and NPC3.
    - Generate a series of 3 events (Series C) between NPC2 and NPC3.
    - The sequence of three events should escalate progressively, with each event intensifying in seriousness and gravity, leading seamlessly into the next.
    - The third event in each series of three should carry sufficient gravity and intensity to convincingly serve as a motive for murder.
    - Keep each NPC morally ambiguous. The player of the game must believe that each NPC is capable of being either the killer or the victim.
    - Remember, the third (final) event in each series should present an irresolvable conflict and incentive for murder.
    - However, the NPC with the npc_role of 'killer' should have the strongest incentive to kill by the end of the third (final) event.
    - The events must relate directly to the genre of {universe['genre']} and have elements of {universe['element']}.
    - IMPORTANT: You must use all of the existing NPC background details to generate the events. You will find background details for each NPC (NPC1, NPC2, NPC3) in the following python dictionary object: ```{universe['character_info']}```.
    - IMPORTANT: rely heavily on the `expertise` for both NPC1 and NPC2 to craft the events in Series A.
    - IMPORTANT: rely heavily on the `expertise` for both NPC1 and NPC3 to craft the events in Series B.
    - IMPORTANT: rely heavily on the `expertise` for both NPC2 and NPC3 to craft the events in Series C.

    output in json format:
    {{"series_a": {{"event_1": {{"story": "", "char_list": ["npc_1", "npc_2"]}}, "event_2": {{...}}, "event_3": {{...}}}}, "series_b": {{...}}, ...}}
    """

    events_details = MODEL2.generate_content(event_prompt).text
    events_info = json_str_processing(events_details)

    event_rubric = """
        Rubric for creating a set of fictional events between 2 characters in a story:

        1. Innovativeness (25 points)
        - Originality in plotlines and twists
        - Unexpected plot developments that surprise and engage audience
        - Subversion of common tropes and stereotypes
        - Clever and purposeful subversion that adds depth to the narrative
        - Avoidance of overused or predictable plot devices
        - Stimulation of critical thinking and problem-solving

        2. Avoidance of Melodramatics (25 points)
        - Realistic character reactions and emotions
        - Characters respond to events and revelations in a believable manner
        - Avoidance of exaggerated or overblown emotional responses
        - Grounded and nuanced storytelling
        - Narrative events and plot twists are earned and justified by the story
        - Avoidance of contrived or artificially heightened drama

        3. Compelling Characters (25 points)
        - Complex and multi-dimensional personalities
        - Memorable characters with believable and evolving motivations, flaws, and growth
        - Avoidance of one-dimensional archetypes and stereotypes
        - Well-crafted backstories and character arcs
        - Histories that inform and enrich character actions and decisions

        4. Immersive and Cohesive Setting (25 points)
        - Rich, detailed, and consistent world-building
        - Consistent and logical world-building that maintains suspension of disbelief
        - Integration of setting with narrative and educational content
        - Environments that reinforce and enhance the educational themes
        - Coherence and logical flow of events
        - Consistent and believable cause-and-effect relationships

        Total: 100 points

        Scoring:
        - 90-100: Exemplary
        - 80-89: Excellent
        - 70-79: Good
        - 60-79: Fair
        - Below 60: Needs improvement
        """

    def critic_feedback_events(model, rubric, events_info):
        prompt = f'''
        
        ## SYSTEM:
        You are a highly intelligent and creative former Hollywood scriptwriter and current expert narrative designer for a gaming company with a keen eye for detail and unrivaled ability to weave compelling stories into interactive games.

        Your task is to evaluate and give feedback on the following series of events.

        When a user submits a piece of writing, give it a grade (in points) based on
        its potential to be made into a unique and compelling text-based interactive
        game. Follow the given events rubric as the criteria for your evaluation and
        grade.

        Your response/feedback should include three sections for each series of
        events, for example:

        - Series A:
            - Strengths
            - Recommendations for Improvement
            - Overall Score
        - Series B:
            - Strengths
            - Recommendations for Improvement
            - Overall Score
        - Series C:
            - Strengths
            - Recommendations for Improvement
            - Overall Score

        Events rubric: ```{rubric}```

        ## USER:

        Series A:
        - Event1: {events_info['series_a']['event_1']['story']}
        - Event2: {events_info['series_a']['event_2']['story']}
        - Event3: {events_info['series_a']['event_3']['story']}

        Series B:
        - Event1: {events_info['series_b']['event_1']['story']}
        - Event2: {events_info['series_b']['event_2']['story']}
        - Event3: {events_info['series_b']['event_3']['story']}

        Series C:
        - Event1: {events_info['series_c']['event_1']['story']}
        - Event2: {events_info['series_c']['event_2']['story']}
        - Event3: {events_info['series_c']['event_3']['story']}

        '''

        feedback = model.generate_content(prompt)
        return feedback.text

    critiq_results = critic_feedback_events(DULL_MODEL, event_rubric, events_info)

    def refine_draft_events(model, feedback, draft):
        prompt = f"""
        ## SYSTEM
        You are a highly intelligent and creative former Hollywood scriptwriter and current expert narrative designer for a gaming company with a keen eye for detail and unrivaled ability to weave compelling stories into interactive games.

        Your task is to develop 3 sets of fictional events between NPCs (non-playable characters) prior to a final confrontation.
        
        Here are the exact rules to follow when creating the events: \
        - Generate a series of 3 events (Series A) between NPC1 and NPC2.
        - Generate a series of 3 events (Series B) between NPC1 and NPC3.
        - Generate a series of 3 events (Series C) between NPC2 and NPC3.
        - The sequence of three events should escalate progressively, with each event intensifying in seriousness and gravity, leading seamlessly into the next.
        - The third event in each series of three should carry sufficient gravity and intensity to convincingly serve as a motive for murder.
        - You must use the existing NPC details to generate the events. You will find information for each NPC (NPC1, NPC2, NPC3) in the following python dictionary object: ```{universe['character_info']}```.
        - Keep each NPC morally ambiguous. The player of the game must believe that each NPC is capable of being either the killer or the victim.
        - Remember, the third (final) event in each series should present an irresolvable conflict and incentive for murder.
        - However, the NPC with the npc_role of 'killer' should have the strongest incentive to kill by the end of the third (final) event.
        - The events must relate directly to the genre of {universe['genre']} and have elements of {universe['element']}.
        - IMPORTANT: rely heavily on the `expertise` for both NPC1 and NPC2 to craft the events in Series A.
        - IMPORTANT: rely heavily on the `expertise` for both NPC1 and NPC3 to craft the events in Series B.
        - IMPORTANT: rely heavily on the `expertise` for both NPC2 and NPC3 to craft the events in Series C.

        ## USER
        Review the following draft and incorporate the following feedback to revise and refine the draft ensuring that the instructions provided above are being met.

        Feedback: ```{feedback}```
        Draft (json object): ```{draft}```

        OUTPUT in json format:
        {{"series_a": {{"event_1": {{"story": "", "char_list": ["npc_1", "npc_2"]}}, "event_2": {{...}}, "event_3": {{...}}}}, "series_b": {{...}}, ...}}
        """

        final_draft = model.generate_content(prompt)
        return final_draft.text

    try:
        revised_results = refine_draft_events(MODEL2, critiq_results, events_info)
        revised_events_info = json_str_processing(revised_results)
    except Exception as e:
            app.logger.warning(f"MODEL2 failed: {str(e)}. Trying DULL_MODEL.")
            try:
                revised_results = refine_draft_events(MODEL, critiq_results, events_info)
                revised_events_info = json_str_processing(revised_results)
            except Exception as e:
                app.logger.warning(f"DULL_MODEL failed: {str(e)}. Trying DULL_MODEL.")
                try:
                    # Wait 45 seconds before trying again
                    time.sleep(45)
                    revised_results = refine_draft_events(MODEL, critiq_results, events_info)
                    revised_events_info = json_str_processing(revised_results)
                except Exception as e:
                    app.logger.error(f"All attempts failed in generate_events: {str(e)}")
                    return jsonify({"error": str(e)}), 500

    universe['events'] = revised_events_info

    # Save to json
    with open(os.path.join(DATA_DIR, write_file), 'w') as f:
        json.dump(universe, f, indent=4)

    return jsonify({"message": "Events generated successfully", "events": revised_events_info})

################################################################################
################################################################################
# Quest Generation

@game_creation_bp.route('/quests', methods=['POST'])
# @track_tokens # Decorator to track tokens ### not quite working right for this function
def generate_quests():
    read_file = "universe_with_events.json"
    write_file = "universe_with_quests.json"

    # Read from universe.json
    with open(os.path.join(DATA_DIR, read_file), 'r') as f:
        universe = json.load(f)

    events = universe['events']

    # Add new keys to each event
    for series in events.values():
        for event in series.values():
            event['story_prompt'] = ""
            event['question'] = ""
            event['answer'] = ""
            event['additional_info'] = ""

    # prompt = f'''
    # # System
    # You are a highly intelligent and creative former Hollywood scriptwriter and current \
    # expert narrative designer for a gaming studio with a keen eye for detail and unrivaled \
    # ability to weave compelling stories into interactive digital games.

    # # User
    # Step by step, do the following:

    # For each event in each sets of events, {list(events.keys())}, in the Json object below, fill in \
    # the events "story_prompt", "question", "answer", and "additional_info" fields based on the information in the events "story" field.

    # ## Step 1:
    # Write a subtle prompt directed towards the player for the purpose of eliciting additional information \
    # from an interactive NPC. Elude to the information in the "story" field; do not explicitly refer to any \
    # of the information in the "story" field. You want to help the player but still make it challenging for \
    # them to know the details of the event. The event may refer to one or more NPCs, therefore choose \
    # only one NPC as the target of your prompt. State the subtle prompt in a way that is similar to the \
    # following examples: "<NPC name> was overheard mentioning something about <something interesting>. It \
    # might be wise to ask <a seemingly innocuous question that is loosely related to the event>." 

    # ## Step 2:
    # Write a question that the player can ask the NPC to elicit the information needed to progress the story. \
    # The question should directly reference the information in the "story" field. For example, if the "story" \
    # field states that "Ava, intrigued by the potential of Soren's Natural Language Processing research \
    # to analyze clinical trial data, proposes funding his research in exchange for exclusive rights to the \
    # technology", the question could be "After seeing Soren's research, what was Ava's proposal?" Always \
    # structure the question in a way that is similar to the following examples: "What did <NPC name> do after \
    # <something happened>?", or "What did <NPC name> say about <something interesting>?"

    # ## Step 3:
    # Write the answer to the question in the "answer" field. The answer should be short and concise, \
    # and directly reference the information in the "story" field. Always structure the answer in a way \
    # that is similar to the following examples: "<NPC name> <did something>", or "<NPC name> said <something>."

    # ## Step 4:
    # Based on the NPC you have chosen to ask the question to, fill in the "additional_info" field with the following:
    # Use the Json object below to look up details for each NPC. Find the information in the respective NPC's \
    # "special_items" field. Use one of the special items (they are separated by semicolons) to fill in the \
    # "additional_info" field with a new subtle prompt that will lead the player to the next event.

    # ### Json object:
    # Events: ```{events}```
    # Character Info: ```{universe['character_info']}```

    # # Output instructions:
    # Output in Json format, maintaining the structure of the input events. Ensure all string values are properly escaped.
    # The output should be a valid JSON object with the following structure:
    # {{
    #     "series_a": {{
    #         "event_1": {{"story_prompt": "...", "question": "...", "answer": "...", "additional_info": "..."}},
    #         "event_2": {{...}},
    #         "event_3": {{...}}
    #     }},
    #     "series_b": {{...}},
    #     "series_c": {{...}}
    # }}
    # '''

    prompt = f'''
        # System
        You are an expert educational game designer specializing in creating interactive learning experiences. Your task is to develop engaging educational challenges based on a series of events in a narrative.

        # User
        Step by step, do the following:

        For each event in each sets of events, {list(events.keys())}, in the Json object below, fill in \
        the events "story_prompt", "question", "answer", and "additional_info" fields based on the information in the events "story" field.

        ## Step 1:
        Write a subtle prompt directed towards the player for the purpose of eliciting additional information from an interactive NPC. Elude to the information in the "story" field; do not explicitly refer to any of the information in the "story" field. You want to help the player but still make it challenging for them to know the details of the event. The event may refer to one or more NPCs, therefore choose only one NPC as the target of your prompt. State the subtle prompt in a way that is similar to the following examples: "<NPC name> was overheard mentioning something about <something interesting>. It might be wise to ask <a seemingly innocuous question that is loosely related to the event>." 

        ## Step 2: Analyze the Event
        Carefully read the "story" field for each event and identify the key educational elements, such as:
        - Scientific concepts
        - Technical skills
        - Business strategies

        ## Step 2: Create an Educational Task
        Based on the key elements identified, design a task that requires the player to demonstrate understanding or apply knowledge related to the event. The task should be challenging yet achievable, encouraging critical thinking and problem-solving.

        ## Step 3: Formulate the Question
        Write a clear, concise question that presents the educational task to the player. This will be the value for the "question" key. The question should:
        - Directly relate to the event's content
        - Require more than simple recall
        - Encourage analysis or application of concepts

        ## Step 4: Provide the Answer
        Craft a comprehensive answer that resolves the task and demonstrates understanding of the event's key elements. This will be the value for the "answer" key. The answer should:
        - Directly address the question
        - Explain the reasoning behind the solution
        - Connect back to the original event

        ## Step 5: Additional Learning Opportunity
        In the "additional_info" field, provide a brief follow-up task or question that extends the learning from the main task. This task should guide the player to elicit information from another NPC. This could involve:
        - A related concept to explore
        - A hypothetical scenario to consider
        - A real-world application of the learned concept

        ### JSON object:
        Events: ```{events}```
        Character Info: ```{universe['character_info']}```

        # Output Instructions:
        Output in JSON format, maintaining the structure of the input events. Ensure all string values are properly escaped.
        The output should be a valid JSON object with the following structure:
        {{
            "series_a": {{
                "event_1": {{"story_prompt": "...", "question": "...", "answer": "...", "additional_info": "..."}},
                "event_2": {{...}},
                "event_3": {{...}}
            }},
            "series_b": {{...}},
            "series_c": {{...}}
        }}
    '''

    try:
        try:
            new_events_ = MODEL2.generate_content(prompt).text
            app.logger.debug(f"Raw response from MODEL2: {new_events_}")
        except Exception as e:
            app.logger.warning(f"MODEL2 failed: {str(e)}. Trying DULL_MODEL.")
            try:
                new_events_ = MODEL.generate_content(prompt).text
                app.logger.debug(f"Raw response from DULL_MODEL: {new_events_}")
            except Exception as e:
                app.logger.warning(f"DULL_MODEL failed. Trying MODEL2 again.")
                try:
                    # Wait 30 seconds before trying again
                    time.sleep(60)
                    new_events_ = MODEL2.generate_content(prompt).text
                except Exception as e:
                    app.logger.error(f"All attempts failed in generate_characters: {str(e)}")
                    return jsonify({"error": str(e)}), 500

        # Check if the response is empty
        if not new_events_.strip():
            raise ValueError("Empty response from model")

        # Try to find JSON content in the response
        json_start = new_events_.find('{')
        json_end = new_events_.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON content found in the response")

        json_content = new_events_[json_start:json_end]
        new_events = json.loads(json_content)
        
        # Validate the structure of new_events
        if not isinstance(new_events, dict) or not all(series in new_events for series in ['series_a', 'series_b', 'series_c']):
            raise ValueError("Generated events do not have the expected structure")

        # Update only the new fields
        for series_key, series in new_events.items():
            for event_key, new_event in series.items():
                if event_key in events[series_key]:
                    events[series_key][event_key].update({
                        'story_prompt': new_event.get('story_prompt', ''),
                        'question': new_event.get('question', ''),
                        'answer': new_event.get('answer', ''),
                        'additional_info': new_event.get('additional_info', '')
                    })

        universe['events'] = events

        # Save to json
        with open(os.path.join(DATA_DIR, write_file), 'w') as f:
            json.dump(universe, f, indent=4)

        return jsonify({"message": "Quests generated successfully", "events": events})
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON parsing error in generate_quests: {str(e)}")
        app.logger.error(f"Problematic JSON: {json_content}")
        return jsonify({"error": f"An error occurred while parsing the generated quests: {str(e)}"}), 500
    except ValueError as e:
        app.logger.error(f"Value error in generate_quests: {str(e)}")
        app.logger.error(f"Raw response: {new_events_}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.error(f"Error in generate_quests: {str(e)}")
        return jsonify({"error": f"An error occurred while generating quests: {str(e)}"}), 500