# src/core/character.py

class Character:
    """
    Represents a player character in the Lore Weaver bot.

    Attributes:
        user_id (int): The Discord user ID associated with this character.
        name (str): The character's name.
        backstory (str): A brief history or background of the character.
        abilities (list[str]): A list of skills or special talents the character possesses.
        desires (list[str]): The character's primary goals or motivations.
        weaknesses (list[str]): The character's flaws or vulnerabilities.
    """
    def __init__(self, user_id: int, name: str, backstory: str, abilities: list[str], desires: list[str], weaknesses: list[str]):
        """
        Initializes a new Character instance.

        Args:
            user_id: The Discord user ID.
            name: The character's name.
            backstory: The character's background story.
            abilities: A list of the character's abilities.
            desires: A list of the character's desires.
            weaknesses: A list of the character's weaknesses.
        """
        self.user_id = user_id
        self.name = name
        self.backstory = backstory
        self.abilities = abilities if abilities is not None else []
        self.desires = desires if desires is not None else []
        self.weaknesses = weaknesses if weaknesses is not None else []

    def save(self, db_connection):
        """
        Saves the character's data to the database.
        (Placeholder - actual implementation is in database.py:save_character)

        Args:
            db_connection: An active database connection object.
        """
        # This method is a conceptual placeholder.
        # The actual saving logic is handled by database.save_character(conn, character_object).
        # Retaining for potential future use if Character methods directly interact with DB.
        pass

    def load(self, db_connection, user_id: int):
        """
        Loads a character's data from the database by user_id.
        (Placeholder - actual implementation is in database.py:get_character)

        Args:
            db_connection: An active database connection object.
            user_id: The user_id of the character to load.

        Returns:
            A Character object or None if not found.
        """
        # This method is a conceptual placeholder.
        # The actual loading logic is handled by database.get_character(conn, user_id).
        pass

if __name__ == '__main__':
    # Example Usage (for manual testing or demonstration)
    print("--- Character Class Demonstration ---")
    example_char = Character(
        user_id=12345,
        name="Elara Meadowlight",
        backstory="A skilled herbalist from a secluded village, searching for a rare flower to cure her ailing mentor.",
        abilities=["Expert in identifying magical plants", "Basic healing spells", "Can speak with animals"],
        desires=["Find the Moonpetal flower", "Protect her village from a creeping darkness"],
        weaknesses=["Distrustful of city folk", "Overly cautious"]
    )
    print(f"Character Created: {example_char.name}")
    print(f"User ID: {example_char.user_id}")
    print(f"Backstory: {example_char.backstory}")
    print(f"Abilities: {', '.join(example_char.abilities)}")
    print(f"Desires: {', '.join(example_char.desires)}")
    print(f"Weaknesses: {', '.join(example_char.weaknesses)}")

    print("\n--- Character with empty lists ---")
    empty_list_char = Character(user_id=67890, name="Silent Sam", backstory="Mysterious.", abilities=None, desires=None, weaknesses=None)
    print(f"Character: {empty_list_char.name}, Abilities: {empty_list_char.abilities}")
