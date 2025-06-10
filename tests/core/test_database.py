import unittest
import sqlite3
import os
import json
from src.core import database # Imports the database module
from src.core.character import Character # Imports the Character class

TEST_DB_NAME = "test_lore_weaver.db"

class TestDatabase(unittest.TestCase):
    def setUp(self):
        """Set up a temporary database for each test."""
        # Ensure a clean state by removing the test DB if it exists
        if os.path.exists(TEST_DB_NAME):
            os.remove(TEST_DB_NAME)
        self.conn = database.init_db(db_name=TEST_DB_NAME)
        self.assertIsNotNone(self.conn, "Database connection should not be None")

    def tearDown(self):
        """Clean up by closing the connection and removing the test database file."""
        if self.conn:
            self.conn.close()
        if os.path.exists(TEST_DB_NAME):
            os.remove(TEST_DB_NAME)

    def test_init_db_creates_tables(self):
        """Test if init_db correctly creates the 'characters' and 'user_credits' tables."""
        cursor = self.conn.cursor()
        # Check for characters table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='characters';")
        self.assertIsNotNone(cursor.fetchone(), "The 'characters' table should be created.")
        # Check for user_credits table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_credits';")
        self.assertIsNotNone(cursor.fetchone(), "The 'user_credits' table should be created.")

    def test_save_and_get_character(self):
        """Test saving a character and then retrieving it."""
        sample_char = Character(
            user_id=1, name="Testor", backstory="A brave tester.",
            abilities=["testing", "debugging"], desires=["stable code"], weaknesses=["off-by-one errors"]
        )
        database.save_character(self.conn, sample_char)

        retrieved_char = database.get_character(self.conn, 1)
        self.assertIsNotNone(retrieved_char, "Should retrieve a character.")
        self.assertEqual(retrieved_char.user_id, sample_char.user_id)
        self.assertEqual(retrieved_char.name, sample_char.name)
        self.assertEqual(retrieved_char.backstory, sample_char.backstory)
        self.assertEqual(retrieved_char.abilities, sample_char.abilities)
        self.assertEqual(retrieved_char.desires, sample_char.desires)
        self.assertEqual(retrieved_char.weaknesses, sample_char.weaknesses)

    def test_get_character_non_existent(self):
        """Test retrieving a non-existent character."""
        retrieved_char = database.get_character(self.conn, 999)
        self.assertIsNone(retrieved_char, "Should return None for a non-existent character.")

    def test_update_and_get_credits(self):
        """Test credit operations: adding to new user, updating existing, deducting."""
        user_id_1 = 10
        user_id_2 = 20

        # Test get_credits for non-existent user
        self.assertEqual(database.get_credits(self.conn, user_id_1), 0.0, "Credits for non-existent user should be 0.0.")

        # Test adding credits to a new user (also tests creation)
        database.update_credits(self.conn, user_id_1, 50.0)
        self.assertEqual(database.get_credits(self.conn, user_id_1), 50.0)

        # Test adding more credits to the same user
        database.update_credits(self.conn, user_id_1, 25.0)
        self.assertEqual(database.get_credits(self.conn, user_id_1), 75.0)

        # Test deducting credits
        database.update_credits(self.conn, user_id_1, -30.0)
        self.assertEqual(database.get_credits(self.conn, user_id_1), 45.0)

        # Test another user to ensure separation
        database.update_credits(self.conn, user_id_2, 100.0)
        self.assertEqual(database.get_credits(self.conn, user_id_2), 100.0)
        self.assertEqual(database.get_credits(self.conn, user_id_1), 45.0, "User 1 credits should remain unchanged.")

    def test_save_character_with_empty_lists(self):
        """Test saving and retrieving a character with empty lists for abilities, desires, weaknesses."""
        sample_char = Character(
            user_id=2, name="Minimalist", backstory="Less is more.",
            abilities=[], desires=[], weaknesses=[]
        )
        database.save_character(self.conn, sample_char)
        retrieved_char = database.get_character(self.conn, 2)
        self.assertIsNotNone(retrieved_char)
        self.assertEqual(retrieved_char.abilities, [])
        self.assertEqual(retrieved_char.desires, [])
        self.assertEqual(retrieved_char.weaknesses, [])


if __name__ == '__main__':
    unittest.main()
