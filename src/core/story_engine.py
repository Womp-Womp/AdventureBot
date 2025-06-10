# src/core/story_engine.py
import os
# import google.generativeai as genai # Will be used for actual API calls
import logging
from src.core.character import Character # Assuming Character class is in src.core.character
import json # For potential structured output later

logger = logging.getLogger(__name__)

STORY_ENGINE_PERSONA = (
    "You are a Genius Storyteller and Dungeon Master, crafting a rich and engaging "
    "Dungeons & Dragons style text-based adventure.\n"
    "Your writing is evocative, descriptive, and tailored to the player's character.\n"
    "You will always present a narrative segment and then offer 4-5 distinct, actionable "
    "choices for the player to take.\n"
    "Format the choices clearly, perhaps as a numbered or bulleted list.\n"
    "Ensure the story flows logically from the character's actions and the established context.\n"
    "The player's character details are provided below. Use them to personalize the story."
)

MOCKED_API_KEY = "mock_gemini_api_key" # Placeholder

def generate_story_segment(api_key: str, character: Character, history: list[dict]) -> dict:
    """
    Generates the next story segment and choices, currently using a mocked response
    instead of a real API call to the Gemini API.

    This function constructs a detailed prompt incorporating the character's attributes
    and the conversation history to provide context for story generation. It then
    simulates an API response, providing story text, choices, and a mocked cost.

    Args:
        api_key (str): The API key for the Gemini service (currently not used by the mock).
        character (Character): The player's Character object, containing details like
                               name, backstory, abilities, etc.
        history (list[dict]): A list of dictionaries representing the conversation history.
                              Each dictionary should have 'role' ('user' or 'model') and
                              'parts' (a list containing the message content).
                              Example: `[{'role': 'user', 'parts': ['I open the chest.']}]`

    Returns:
        dict: A dictionary containing the following keys:
            'story_text' (str): The generated narrative segment for the current turn.
            'choices' (list[str]): A list of 4-5 string options for the player to choose from.
            'api_call_cost' (float): A simulated cost for this "API call".
            'prompt_debug' (str): The full text of the prompt that would be sent to the AI.
                                  Useful for debugging prompt engineering.
    """
    prompt_parts = [STORY_ENGINE_PERSONA]
    prompt_parts.append("\n--- Character Information ---")
    prompt_parts.append(f"Name: {character.name}")
    prompt_parts.append(f"Backstory: {character.backstory}")
    prompt_parts.append(f"Abilities: {', '.join(character.abilities)}")
    prompt_parts.append(f"Desires: {', '.join(character.desires)}")
    prompt_parts.append(f"Weaknesses: {', '.join(character.weaknesses)}")

    prompt_parts.append("\n--- Adventure History ---")
    if not history:
        prompt_parts.append("This is the beginning of your adventure.")
    else:
        for turn in history:
            content = "".join(str(p) for p in turn.get('parts', [])) if isinstance(turn.get('parts'), list) else str(turn.get('parts', ''))
            prompt_parts.append(f"{turn.get('role', 'unknown').capitalize()}: {content}")

    current_situation_header = "\n--- Current Situation ---"
    if history and history[-1]['role'] == 'user':
        last_user_action_parts = history[-1].get('parts', [])
        last_user_action = "".join(str(p) for p in last_user_action_parts) if isinstance(last_user_action_parts, list) else str(last_user_action_parts)
        prompt_parts.append(current_situation_header)
        prompt_parts.append(f"The player chose: '{last_user_action}'. Now, continue the story and provide new choices.")
    elif not history:
        prompt_parts.append(current_situation_header)
        prompt_parts.append(f"This is the very beginning of {character.name}'s adventure. Start the story and provide the first set of choices.")
    else: # History exists, but last turn was not user (e.g. multiple model turns, though unlikely in this flow)
        prompt_parts.append(current_situation_header)
        prompt_parts.append("Continue the story based on the last event and provide new choices.")


    prompt_parts.append("\n--- Your Task ---")
    prompt_parts.append("Generate the next part of the story and provide 4-5 distinct choices as a list.")

    full_prompt = "\n".join(prompt_parts)
    logger.debug(f"Generated prompt for Gemini API for character {character.user_id} ({character.name}):\n{full_prompt}")

    # Mocked response:
    logger.info(f"Generating (mocked) story segment for character {character.user_id} ({character.name}). History length: {len(history)}")
    # Default response for initial generation (no history)
    mocked_story_text = (f"The wind howls around {character.name} as they stand at the crossroads. "
                         "To the north, a dark forest looms. To the east, a glittering city can be seen in the distance. "
                         "A weathered signpost points west, its carvings too faded to read. South, the road back from whence you came.")

    mocked_choices = [
        "Venture into the dark forest to the north.",
        "Head towards the glittering city in the east.",
        "Inspect the weathered signpost to the west.",
        "Cautiously retreat south along the road you came from.",
        "Scan the surroundings for any immediate threats or points of interest."
    ]
    mocked_api_call_cost = 0.01 # Simulated cost

    # If there's history, especially a user's last action, tailor the mock response a bit.
    try:
        # This block simulates what would be an actual API call.
        # If genai were used:
        # model = genai.GenerativeModel('gemini-pro') # Or your chosen model
        # response = model.generate_content(full_prompt)
        # mocked_story_text = response.text
        # mocked_choices = parse_choices_from_response(response.text)
        # mocked_api_call_cost = calculate_cost(full_prompt, response.text)
        # logger.info("Successfully received response from (mocked) Gemini API.")

        if history and history[-1]['role'] == 'user':
            last_action_parts = history[-1].get('parts', ["your previous action"])
            # Ensure last_action_parts is a list of strings before join, or handle if it's already a string
            if isinstance(last_action_parts, list):
                last_action = "".join(str(p) for p in last_action_parts)
            else: # It might already be a string if 'parts' was not a list
                last_action = str(last_action_parts)

            mocked_story_text = (f"Following your decision to '{last_action}', you find yourself facing a new scenario. "
                                 f"The air is thick with anticipation. What will {character.name} do next?")
            mocked_choices = [
                f"Press on cautiously after deciding '{last_action}'.",
                "Examine the strange glowing rune on the wall more closely.",
                "Call out to see if anyone is nearby in this new area.",
                "Prepare a defensive spell or stance, wary of what's to come."
            ]
        logger.info(f"Mocked story segment generated for user {character.user_id}. Story starts: '{mocked_story_text[:50]}...'")
    except Exception as e: # Placeholder for actual API call exception handling
        logger.error(f"Error generating story segment for character {character.user_id}: {e}", exc_info=True)
        # Fallback response in case of error
        mocked_story_text = "An unexpected silence falls. It seems the threads of fate are tangled. (Error generating story)"
        mocked_choices = ["Try to wait a moment and see if anything changes.", "Check your connection to the ethereal plane (debug)."]
        mocked_api_call_cost = 0.001 # Minimal cost for error

    return {
        "story_text": mocked_story_text,
        "choices": mocked_choices,
        "api_call_cost": mocked_api_call_cost,
        "prompt_debug": full_prompt
    }

def parse_choices_from_response(response_text: str) -> list[str]:
    """
    (Placeholder) Parses distinct choices from the AI's response text.

    This function attempts to extract bulleted or numbered list items from the
    provided text, assuming these represent player choices. This is a simplified
    implementation and would need to be made more robust for production use with
    a real AI model, potentially relying on more structured output or advanced
    parsing techniques.

    Args:
        response_text (str): The raw text output from the AI model.

    Returns:
        list[str]: A list of parsed choices. If parsing fails or no choices are
                   found, returns a list with default placeholder choices.
    """
    choices = []
    # Simple parsing: look for lines starting with common list markers.
    for line in response_text.split('\n'):
        line_stripped = line.strip()
        if line_stripped.startswith("- ") or \
           (len(line_stripped) > 2 and line_stripped[0].isdigit() and line_stripped[1] == '.' and line_stripped[2] == ' '):
            # Extract text after marker (e.g., "- " or "1. ")
            choice_text = line_stripped[2:] if line_stripped.startswith("- ") else line_stripped[3:]
            if choice_text: # Avoid adding empty strings if line was just the marker
                 choices.append(choice_text.strip())

    if not choices:
        logger.warning(f"Could not parse distinct choices from response: '{response_text[:100]}...'")
        # Provide default choices to prevent errors downstream if parsing fails
        return ["Default choice 1 (parsing failed)", "Default choice 2 (parsing failed)"]

    logger.debug(f"Parsed choices: {choices}")
    return choices


def calculate_cost(prompt_text: str, response_text: str) -> float:
    """
    (Placeholder) Calculates an estimated cost for an API call based on prompt
    and response lengths.

    This is a simplified mock calculation. A real implementation would likely involve
    counting tokens more accurately according to the specific API's pricing model.

    Args:
        prompt_text (str): The text of the prompt sent to the API.
        response_text (str): The text of the response received from the API.

    Returns:
        float: The estimated (mocked) cost of the API call, rounded to 4 decimal places.
    """
    # Example: 0.5 cent base + 0.1 cent per 1k prompt chars + 0.2 cent per 1k response chars
    cost = 0.005 + (len(prompt_text) / 1000 * 0.001) + (len(response_text) / 1000 * 0.002)
    logger.debug(f"Calculated (mocked) API cost: {cost:.4f} for prompt length {len(prompt_text)} and response length {len(response_text)}")
    return round(cost, 4)

if __name__ == '__main__':
    # Basic logging setup for standalone testing
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                        handlers=[logging.StreamHandler()])
    logger.info("Starting story_engine.py standalone test...")

    sample_char = Character(
        user_id=12345,
        name="Lyra",
        backstory="A wandering minstrel with a mysterious past.",
        abilities=["Plays enchanting melodies", "Quick-witted", "Knows ancient lore"],
        desires=["To find the lost Song of the Ancients"],
        weaknesses=["Afraid of heights", "Cannot resist a good puzzle"]
    )

    logger.info("--- Generating initial story segment ---")
    initial_segment = generate_story_segment(MOCKED_API_KEY, sample_char, [])
    logger.info(f"Story: {initial_segment['story_text']}")
    logger.info("Choices:")
    for i, choice_text in enumerate(initial_segment['choices']): # Renamed choice to choice_text to avoid conflict
        logger.info(f"{i+1}. {choice_text}")
    logger.info(f"Cost: ${initial_segment['api_call_cost']:.4f}")
    # logger.debug(f"DEBUG PROMPT:\n{initial_segment['prompt_debug']}")

    logger.info("\n--- Generating next story segment after a choice ---")
    game_history = [
        {'role': 'model', 'parts': [initial_segment['story_text']]}, # Model's previous turn
        # User chooses the first choice from the initial segment
        {'role': 'user', 'parts': [initial_segment['choices'][0]]}
    ]
    next_segment = generate_story_segment(MOCKED_API_KEY, sample_char, game_history)
    logger.info(f"Story: {next_segment['story_text']}")
    logger.info("Choices:")
    for i, choice_text in enumerate(next_segment['choices']): # Renamed choice to choice_text
        logger.info(f"{i+1}. {choice_text}")
    logger.info(f"Cost: ${next_segment['api_call_cost']:.4f}")
    # logger.debug(f"DEBUG PROMPT:\n{next_segment['prompt_debug']}")
    logger.info("Standalone test finished.")
