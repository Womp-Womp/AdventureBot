# src/core/database.py
import sqlite3
import json
import logging
from src.core.character import Character # Assuming Character class is in src.core.character

logger = logging.getLogger(__name__)
DB_NAME = "lore_weaver.db" # Default database name

def init_db(db_name: str = DB_NAME) -> sqlite3.Connection | None:
    """
    Initializes the SQLite database. Connects to the database file (creating it
    if it doesn't exist) and ensures the necessary tables ('characters', 'user_credits')
    are created.

    Args:
        db_name: The name of the database file to connect to.
                 Defaults to DB_NAME ("lore_weaver.db").

    Returns:
        An active sqlite3.Connection object if successful, or None if an error occurs
        (though it currently raises the error).

    Raises:
        sqlite3.Error: If any SQLite error occurs during connection or table creation.
    """
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Create characters table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            backstory TEXT,
            abilities TEXT,
            desires TEXT,
            weaknesses TEXT
        )
    ''')

        # Create user_credits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_credits (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0.0
            )
        ''')
        conn.commit()
        logger.info(f"Database '{db_name}' initialized successfully with tables 'characters' and 'user_credits'.")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database initialization error for '{db_name}': {e}", exc_info=True)
        raise # Re-raise the exception so main.py can catch it and exit

def save_character(conn: sqlite3.Connection, character: Character) -> None:
    """
    Saves a character's data to the 'characters' table in the database.
    If a character with the same user_id already exists, it replaces their data.
    Character abilities, desires, and weaknesses (lists of strings) are stored
    as JSON strings.

    Args:
        conn: The active SQLite database connection.
        character: The Character object to save.
    """
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO characters (user_id, name, backstory, abilities, desires, weaknesses)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            character.user_id,
            character.name,
            character.backstory,
            json.dumps(character.abilities),
            json.dumps(character.desires),
            json.dumps(character.weaknesses)
        ))
        conn.commit()
        logger.info(f"Character saved/updated for user_id: {character.user_id}, name: {character.name}")
    except sqlite3.Error as e:
        logger.error(f"Database error in save_character for user_id {character.user_id if character else 'Unknown'}: {e}", exc_info=True)
        # Optionally re-raise or handle more gracefully, e.g., return False on failure

def get_character(conn: sqlite3.Connection, user_id: int) -> Character | None:
    """
    Retrieves a character's data from the 'characters' table by their user_id.
    Converts JSON string fields (abilities, desires, weaknesses) back into Python lists.

    Args:
        conn: The active SQLite database connection.
        user_id: The Discord user ID of the character to retrieve.

    Returns:
        A Character object if found, otherwise None.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name, backstory, abilities, desires, weaknesses FROM characters WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            logger.debug(f"Character data found for user_id: {user_id}")
            return Character(
                user_id=user_id,
                name=row[0],
                backstory=row[1],
                abilities=json.loads(row[2] or '[]'), # Handle null from DB
                desires=json.loads(row[3] or '[]'),   # Handle null from DB
                weaknesses=json.loads(row[4] or '[]') # Handle null from DB
            )
        logger.debug(f"No character data found for user_id: {user_id}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error in get_character for user_id {user_id}: {e}", exc_info=True)
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in get_character for user {user_id}: {e}", exc_info=True)
        return None


def update_credits(conn: sqlite3.Connection, user_id: int, amount: float) -> None:
    """
    Updates a user's credit balance in the 'user_credits' table.
    If the user does not exist, a new record is created for them with the given amount.
    The amount can be positive (to add credits) or negative (to deduct credits).

    Args:
        conn: The active SQLite database connection.
        user_id: The Discord user ID whose credits are to be updated.
        amount: The amount to add or deduct from the user's balance.
    """
    cursor = conn.cursor()
    try:
        # Check if user exists
        cursor.execute("SELECT balance FROM user_credits WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        action = "updated"
        if row:
            new_balance = row[0] + amount
            cursor.execute("UPDATE user_credits SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        else:
            # User does not exist, insert new record
            cursor.execute("INSERT INTO user_credits (user_id, balance) VALUES (?, ?)", (user_id, amount))
            action = "created"
        conn.commit()
        logger.info(f"User credits {action} for user_id: {user_id}. Amount: {amount:+f}. New balance: {get_credits(conn, user_id):.2f}")
    except sqlite3.Error as e:
        logger.error(f"Database error in update_credits for user_id {user_id}: {e}", exc_info=True)

def get_credits(conn: sqlite3.Connection, user_id: int) -> float:
    """
    Retrieves a user's current credit balance from the 'user_credits' table.

    Args:
        conn: The active SQLite database connection.
        user_id: The Discord user ID to retrieve credits for.

    Returns:
        The user's credit balance as a float. Returns 0.0 if the user is not found
        or if an error occurs.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance FROM user_credits WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        balance = row[0] if row else 0.0
        logger.debug(f"Retrieved credit balance for user_id {user_id}: {balance:.2f}")
        return balance
    except sqlite3.Error as e:
        logger.error(f"Database error in get_credits for user_id {user_id}: {e}", exc_info=True)
        return 0.0

if __name__ == '__main__':
    # Basic logging setup for standalone testing
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                        handlers=[logging.StreamHandler()])
    logger.info("Starting database.py standalone test...")

    db_conn = init_db(db_name="test_lore_weaver.db") # Use a test DB for standalone runs
    if not db_conn:
        logger.critical("Failed to initialize test database. Exiting.")
        exit()

    logger.info("Test database initialized.")

    # Test Character
    test_char_data = Character(
        user_id=123, name="Test User", backstory="A brave tester.",
        abilities=["testing", "debugging"], desires=["flawless code"], weaknesses=["off-by-one errors"]
    )
    logger.info(f"Saving character: {test_char_data.name}")
    save_character(db_conn, test_char_data)

    logger.info(f"Retrieving character ID: {test_char_data.user_id}")
    retrieved_char = get_character(db_conn, test_char_data.user_id)
    if retrieved_char:
        logger.info(f"Retrieved Character: {retrieved_char.name}, Abilities: {retrieved_char.abilities}")
    else:
        logger.warning("Character not found after saving.")

    # Test Credits
    logger.info(f"Getting credits for user ID: {test_char_data.user_id}")
    initial_credits = get_credits(db_conn, test_char_data.user_id)
    logger.info(f"Initial credits: {initial_credits}")

    logger.info(f"Adding 10.0 credits to user ID: {test_char_data.user_id}")
    update_credits(db_conn, test_char_data.user_id, 10.0)

    logger.info(f"Deducting 3.5 credits from user ID: {test_char_data.user_id}")
    update_credits(db_conn, test_char_data.user_id, -3.5)

    # Test non-existent user for credits
    non_existent_user_id = 999
    logger.info(f"Getting credits for non-existent user ID: {non_existent_user_id}")
    get_credits(db_conn, non_existent_user_id)

    logger.info(f"Adding 5.0 credits to non-existent user ID: {non_existent_user_id}")
    update_credits(db_conn, non_existent_user_id, 5.0)

    logger.info("Standalone test finished. Closing database connection.")
    db_conn.close()
    # Clean up test database file (optional)
    # import os
    # os.remove("test_lore_weaver.db")
    # logger.info("Test database file removed.")
