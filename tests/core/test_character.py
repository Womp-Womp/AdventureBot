import unittest
from src.core.character import Character

class TestCharacter(unittest.TestCase):
    def test_character_creation(self):
        user_id = 123
        name = "Eldrin"
        backstory = "A mighty warrior from the northern mountains."
        abilities = ["Sword fighting", "Ice magic"]
        desires = ["Find the Sunstone", "Protect his village"]
        weaknesses = ["Arachnophobia", "Cannot resist a good ale"]

        char = Character(
            user_id=user_id,
            name=name,
            backstory=backstory,
            abilities=abilities,
            desires=desires,
            weaknesses=weaknesses
        )

        self.assertEqual(char.user_id, user_id)
        self.assertEqual(char.name, name)
        self.assertEqual(char.backstory, backstory)
        self.assertEqual(char.abilities, abilities)
        self.assertIsInstance(char.abilities, list)
        self.assertEqual(char.desires, desires)
        self.assertIsInstance(char.desires, list)
        self.assertEqual(char.weaknesses, weaknesses)
        self.assertIsInstance(char.weaknesses, list)

    def test_character_creation_empty_lists(self):
        char = Character(
            user_id=456,
            name="Lyra",
            backstory="A mysterious bard.",
            abilities=[],
            desires=[],
            weaknesses=[]
        )
        self.assertEqual(char.user_id, 456)
        self.assertEqual(char.name, "Lyra")
        self.assertEqual(char.abilities, [])
        self.assertEqual(char.desires, [])
        self.assertEqual(char.weaknesses, [])

if __name__ == '__main__':
    unittest.main()
