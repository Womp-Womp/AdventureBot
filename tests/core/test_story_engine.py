import unittest
from src.core import story_engine
from src.core.character import Character

class TestStoryEngine(unittest.TestCase):

    def setUp(self):
        """Set up a sample character for use in tests."""
        self.sample_character = Character(
            user_id=1,
            name="Testerina",
            backstory="A hero dedicated to ensuring code quality.",
            abilities=["debug", "assert", "refactor"],
            desires=["100% test coverage"],
            weaknesses=["off-by-one errors", "heisenbugs"]
        )
        self.mock_api_key = "test_api_key"

    def test_generate_story_segment_initial_turn(self):
        """Test generating a story segment for the first turn (empty history)."""
        history = []
        result = story_engine.generate_story_segment(self.mock_api_key, self.sample_character, history)

        self.assertIn("story_text", result)
        self.assertIsInstance(result["story_text"], str)
        self.assertTrue(len(result["story_text"]) > 0, "Story text should not be empty.")

        self.assertIn("choices", result)
        self.assertIsInstance(result["choices"], list)
        self.assertTrue(len(result["choices"]) >= 1, "Should provide at least one choice.") # Mock provides 4-5
        for choice in result["choices"]:
            self.assertIsInstance(choice, str)

        self.assertIn("api_call_cost", result)
        self.assertIsInstance(result["api_call_cost"], float)

        self.assertIn("prompt_debug", result)
        self.assertIsInstance(result["prompt_debug"], str)
        self.assertIn(self.sample_character.name, result["prompt_debug"], "Character name should be in the debug prompt.")
        self.assertIn(self.sample_character.backstory, result["prompt_debug"], "Character backstory should be in the debug prompt.")
        for ability in self.sample_character.abilities:
            self.assertIn(ability, result["prompt_debug"])
        self.assertIn("This is the beginning of your adventure.", result["prompt_debug"], "Initial turn prompt should indicate beginning.")

    def test_generate_story_segment_subsequent_turn(self):
        """Test generating a story segment with existing history."""
        history = [
            {'role': 'model', 'parts': ["You stand before a crumbling ruin."]},
            {'role': 'user', 'parts': ["I enter the ruin."]}
        ]
        result = story_engine.generate_story_segment(self.mock_api_key, self.sample_character, history)

        self.assertIn("story_text", result)
        self.assertTrue(len(result["story_text"]) > 0)
        # Check if the mocked response for subsequent turns is different (as per current story_engine.py logic)
        self.assertIn("Following your decision to 'I enter the ruin.'", result["story_text"], "Story should reflect last user action.")


        self.assertIn("choices", result)
        self.assertTrue(len(result["choices"]) > 0)

        self.assertIn("api_call_cost", result)

        self.assertIn("prompt_debug", result)
        self.assertIn("I enter the ruin.", result["prompt_debug"], "Last user action should be in the prompt.")
        self.assertNotIn("This is the beginning of your adventure.", result["prompt_debug"], "Subsequent turn prompt should not indicate beginning.")

    def test_parse_choices_from_response(self):
        """Test the placeholder choice parsing logic."""
        # This test is for the placeholder and might need adjustment if parsing logic becomes complex
        sample_response_text_dash = "Here's what happens next...\n- Choice A\n- Choice B\n- Choice C"
        choices_dash = story_engine.parse_choices_from_response(sample_response_text_dash)
        self.assertEqual(choices_dash, ["Choice A", "Choice B", "Choice C"])

        sample_response_text_numbered = "The story continues.\n1. Option 1\n2. Option 2"
        choices_numbered = story_engine.parse_choices_from_response(sample_response_text_numbered)
        self.assertEqual(choices_numbered, ["Option 1", "Option 2"])

        sample_response_text_empty = "No choices here."
        choices_empty = story_engine.parse_choices_from_response(sample_response_text_empty)
        self.assertEqual(len(choices_empty), 2) # Default choices
        self.assertTrue("parsing failed" in choices_empty[0])

    def test_calculate_cost(self):
        """Test the placeholder cost calculation."""
        # This test is for the placeholder
        cost = story_engine.calculate_cost("prompt", "response")
        self.assertIsInstance(cost, float)
        # Based on current mock: round(0.005 + (len(prompt_text) / 1000 * 0.001) + (len(response_text) / 1000 * 0.002), 4)
        raw_calculated_cost = 0.005 + (6/1000*0.001) + (8/1000*0.002)
        expected_rounded_cost = round(raw_calculated_cost, 4)
        self.assertAlmostEqual(cost, expected_rounded_cost, places=4)


if __name__ == '__main__':
    unittest.main()
