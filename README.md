# Lore Weaver: A Gemini-Powered D&D Discord Bot

## 1. Project Overview

Lore Weaver is an interactive storytelling bot for Discord that leverages the power of Google's Gemini 1.5 Pro to create dynamic, choice-driven Dungeons & Dragons-style adventures. Users create a unique character and embark on a narrative journey crafted in real-time by the AI Story Engine. The focus is on immersive, high-quality fiction over complex mechanics for the Minimum Viable Product (MVP).

**Core Technologies:**
*   **Backend:** Python 3.10+
*   **Discord API Wrapper:** `py-cord`
*   **AI Story Engine:** Google Gemini 1.5 Pro
*   **Database:** SQLite (for simple, local persistence of user data)
*   **Configuration:** `python-dotenv`

---

## 2. Core Features (MVP)

### 2.1. Interactive Storytelling Engine
*   The bot uses a sophisticated prompt (the "Story Engine Persona") to have Gemini act as a "Genius Author."
*   Gameplay is turn-based. The bot presents a rich narrative segment and concludes with 4-5 distinct choices for the user.
*   All interactions are presented in clean, readable Discord embeds.

### 2.2. Step-by-Step Character Creation
*   New users will trigger a character creation flow upon their first adventure.
*   This will be handled through a Discord Modal (pop-up form) for a clean user experience.
*   The user must define the following attributes for their character:
    *   `Character Name`
    *   `Backstory` (A few sentences to give the AI context)
    *   `Abilities` (e.g., "silver-tongued talker," "unnaturally strong," "sees ancient spirits")
    *   `Desires` (e.g., "to find a legendary lost sword," "to earn the respect of their clan")
    *   `Weaknesses` (e.g., "a crippling fear of spiders," "arrogant and overconfident")

### 2.3. Persistent Contextual Conversations
*   To ensure narrative coherence, the bot will maintain the full story context.
*   When a user clicks a button to make a choice, the bot will compile the *entire* adventure history (all previous story segments and choices made) and send it to the Gemini API along with the new choice.
*   **Note:** This is the most token-intensive part of the bot. This must be considered for the credit system. The 2000-character Discord message limit is for bot *output*, but our input context to Gemini can be much larger.

---

## 3. User Flow

1.  **Start Adventure:** A new user types the `/start_adventure` command.
2.  **Onboarding & Credit:** The bot checks if the user exists in the database.
    *   If **new**, they are granted their initial `$5.00` credit balance.
    *   If **existing**, the bot proceeds.
3.  **Character Check:** The bot checks if the user has a character.
    *   If **no**, it initiates the Character Creation modal. Upon submission, the character is saved to the database.
    *   If **yes**, it loads the existing character.
4.  **Adventure Begins:** The bot sends the character's details along with the master prompt to Gemini to generate the opening scene and the first set of choices (as buttons).
5.  **Gameplay Loop:**
    *   The user reads the story embed and clicks a button corresponding to their choice.
    *   The bot acknowledges the button press (e.g., with a thinking indicator).
    *   It constructs the full conversation history and sends it to the Gemini API.
    *   It calculates the token cost of the API call (input + output).
    *   It deducts the cost from the user's credit balance.
    *   It receives the new story segment and choices from the API.
    *   It edits the original message or sends a new one with the updated story and new buttons.
    *   The loop continues until the user runs out of credit or the story reaches a conclusion.

---

## 4. Monetization & Credit System

The bot's operation is funded by a user credit system due to the cost of the Gemini 1.5 Pro API.

*   **Pricing Model (Gemini 1.5 Pro):**
    *   **Input:** $1.25 / 1M tokens (for prompts <= 200k tokens)
    *   **Output:** $10.00 / 1M tokens (for prompts <= 200k tokens)
*   **User Wallet:**
    *   Every new user starts with a `$5.00` credit.
    *   The bot will display the user's remaining balance with each new story segment.
    *   A `/balance` command will be available.
*   **Admin Controls:**
    *   An admin (defined by `ADMIN_USER_ID` in the `.env` file) can add credits to any user.
    *   **Command:** `/add_credits <user_id> <amount>` (e.g., `/add_credits 1234567890 10.00`)

---

## 5. Future Roadmap (Post-MVP)

*   **Structured Data:** Implement logic to have Gemini output structured JSON for things like `{"item_added": "Rusty Key", "xp_gained": 50}` which the bot can parse and apply to the user's state.
*   **Inventory & Stats:** A full character sheet with inventory, stats (STR, DEX, etc.), and XP tracking.
*   **World & Scenario CRUD:** Allow admins to create, read, update, and delete different starting scenarios or worlds for users to choose from.
*   **Cost-Effective Modes:** Potentially use Gemini 1.5 Flash for less critical interactions or for a "low-fi" adventure mode to conserve user credits.

---

## 6. Setup & Configuration

Create a `.env` file in the root directory with the following variables:
DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_google_ai_studio_api_key_here
ADMIN_USER_ID=your_personal_discord_user_id_here


---

## 7. Support the Project

This project is a labor of love. If you enjoy your adventures with Lore Weaver, consider supporting its development and operational costs!

[**Buy me a coffee!**](https://buymeacoffee.com/womp_womp_?status=1)
