# src/bot/cogs/adventure.py
import discord
import logging
from discord.ext import commands
from discord.commands import SlashCommandGroup, Option
from discord.ui import Modal, InputText, View, Button, button # Ensure button is imported if used as decorator

from src.utils import config
from src.core import database
from src.core.character import Character
from src.core import story_engine

logger = logging.getLogger(__name__)

# In-memory store for active adventures (user_id -> adventure_state)
# adventure_state could be a dictionary: {'character': Character, 'history': list, 'message_id': int, 'view_instance': AdventureView}
active_adventures = {} # In-memory store for active games
INITIAL_CREDITS = 5.00 # Default credits for new users

class CharacterCreationModal(Modal):
    """
    A Discord UI Modal for guiding users through character creation.
    It collects name, backstory, abilities, desires, and weaknesses.
    On submission, it saves the character and attempts to start the adventure.
    """
    def __init__(self, db_conn: sqlite3.Connection, cog_ref: commands.Cog, *args, **kwargs) -> None:
        super().__init__(title="Create Your Character", *args, **kwargs)
        self.db_conn = db_conn # Database connection
        self.cog_ref = cog_ref # Reference to the Adventure cog instance for callbacks

        # Define input fields for the modal
        self.add_item(InputText(label="Character Name", placeholder="E.g., Eldrin Stonebeard", max_length=100, required=True))
        self.add_item(InputText(label="Backstory", style=discord.InputTextStyle.long,
                                placeholder="A few sentences about your character's past, their motivations, and what makes them unique.",
                                max_length=1000, required=True))
        self.add_item(InputText(label="Abilities (comma-separated)",
                                placeholder="E.g., Master swordsman, Knows basic fire magic, Speaks with animals",
                                max_length=200, required=False))
        self.add_item(InputText(label="Desires (comma-separated)",
                                placeholder="E.g., To find a lost artifact, To earn respect, To protect the innocent",
                                max_length=200, required=False))
        self.add_item(InputText(label="Weaknesses (comma-separated)",
                                placeholder="E.g., Greedy, Afraid of spiders, Overly trusting",
                                max_length=200, required=False))

    async def callback(self, interaction: discord.Interaction):
        """
        Handles the submission of the character creation modal.
        It creates the Character object, saves it to the database,
        and then triggers the adventure flow.
        """
        # Defer first, as character creation and initial story might take time.
        # thinking=True shows a loading state to the user for ephemeral responses.
        await interaction.response.defer(ephemeral=True, thinking=True)

        user_id = interaction.user.id
        name = self.children[0].value
        backstory = self.children[1].value
        # Ensure that even if fields are empty, we process them as empty lists.
        abilities_str = self.children[2].value or ""
        desires_str = self.children[3].value or ""
        weaknesses_str = self.children[4].value or ""

        abilities = [a.strip() for a in abilities_str.split(',') if a.strip()]
        desires = [d.strip() for d in desires_str.split(',') if d.strip()]
        weaknesses = [w.strip() for w in weaknesses_str.split(',') if w.strip()]

        if not name or not backstory: # Name and Backstory are essential
            logger.warning(f"Character creation attempt by user {user_id} failed due to missing name or backstory.")
            await interaction.followup.send("Character Name and Backstory are required fields. Please try again.", ephemeral=True)
            return

        new_char = Character(
            user_id=user_id,
            name=name,
            backstory=backstory,
            abilities=abilities,
            desires=desires,
            weaknesses=weaknesses
        )
        try:
            database.save_character(self.db_conn, new_char)

            database.save_character(self.db_conn, new_char)
            logger.info(f"Character '{name}' (User ID: {user_id}) created successfully via modal.")

            if self.cog_ref:
                # This will send its own "Character created... Starting adventure..." message.
                await self.cog_ref.initiate_adventure_flow(interaction, new_char, is_new_creation=True)
            else:
                logger.warning(f"Cog reference not found in CharacterCreationModal for user {user_id}. Cannot auto-start adventure.")
                await interaction.followup.send("Character created, but could not automatically start the adventure. Please try `/start_adventure` manually.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error saving character or starting adventure for user {user_id}: {e}", exc_info=True)
            await interaction.followup.send(f"There was an error creating your character: {e}. Please try again.", ephemeral=True)


class AdventureView(View):
    def __init__(self, character: Character, history: list, db_conn, cog_ref, timeout=300): # Increased timeout
        super().__init__(timeout=timeout)
        self.character = character
        self.history = history
        self.db_conn = db_conn
        self.cog_ref = cog_ref # Reference to the Adventure cog
        self.message: discord.Message | None = None # Will be set after the view is sent to store the message context

    async def on_timeout(self):
        """
        Called when the view times out (no interaction for the specified duration).
        Disables buttons and updates the message to indicate timeout.
        Removes the adventure from the active_adventures tracking.
        """
        logger.info(f"AdventureView timed out for user {self.character.user_id}, message ID {self.message.id if self.message else 'Unknown'}")
        self.clear_items() # Disable all buttons
        if self.message: # If the message reference exists
            try:
                embed = self.message.embeds[0] if self.message.embeds else discord.Embed(title="Adventure Timed Out")
                embed.description = (embed.description or "") + "\n\nThis adventure has timed out. Use `/start_adventure` to begin a new one."
                embed.color = discord.Color.dark_grey()
                for item in self.children: item.disabled = True # Explicitly disable
                await self.message.edit(embed=embed, view=self)
            except discord.NotFound:
                logger.warning(f"AdventureView: Message {self.message.id} not found on timeout for user {self.character.user_id}.")
            except discord.HTTPException as e:
                logger.error(f"HTTPException during AdventureView timeout for user {self.character.user_id}, message {self.message.id}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Generic error during AdventureView timeout for user {self.character.user_id}, message {self.message.id}: {e}", exc_info=True)

        user_id = self.character.user_id
        if user_id in active_adventures:
            if active_adventures[user_id].get('message_id') == (self.message.id if self.message else None):
                del active_adventures[user_id]
                logger.info(f"Adventure for user {user_id} (msg: {self.message.id if self.message else 'N/A'}) timed out and successfully removed from active_adventures.")


    async def handle_choice(self, interaction: discord.Interaction, choice_text: str):
        """
        Processes a player's choice made by clicking a button in the AdventureView.

        This method:
        1. Validates the interaction (correct user, active adventure).
        2. Checks user credits against estimated cost.
        3. Updates adventure history with the user's choice.
        4. Calls the story engine to generate the next segment.
        5. Deducts API call cost from user credits.
        6. Updates the original message with the new story segment and choices.
        7. Handles insufficient credits or other errors.

        Args:
            interaction: The discord.Interaction from the button press.
            choice_text: The label of the button pressed, representing the user's choice.
        """
        user_id = interaction.user.id # Get user_id early for logging
        logger.info(f"Handling choice for user {user_id} (Character: {self.character.name}). Choice: '{choice_text}'")
        await interaction.response.defer() # Acknowledge interaction, work will be done in followup

        user_id = interaction.user.id

        if user_id != self.character.user_id:
            await interaction.followup.send("This is not your adventure to control!", ephemeral=True)
            return

        # Check if this view instance is still the active one for the user
        if active_adventures.get(user_id, {}).get('message_id') != interaction.message.id:
            await interaction.followup.send("This adventure instance is outdated. Please use the latest one or start a new adventure if needed.", ephemeral=True)
            self.clear_items()
            for item in self.children: item.disabled = True
            try:
                await interaction.message.edit(view=self) # Disable buttons on old message
            except discord.HTTPException as e:
                logger.warning(f"Failed to edit outdated adventure message for user {user_id}: {e}", exc_info=True)
            return

        current_credits = database.get_credits(self.db_conn, user_id)
        # Use the cost from the story engine's mock response for now
        # TODO: This might need a more sophisticated way to estimate cost if it varies wildly.
        estimated_cost = story_engine.calculate_cost("","") # Using the placeholder calculate_cost

        if current_credits < estimated_cost:
            logger.warning(f"User {user_id} has insufficient credits ({current_credits}) for action costing ~{estimated_cost}.")
            await interaction.followup.send(f"You need at least {estimated_cost:.2f} credits to make a choice, but you only have {current_credits:.2f}. Your adventure ends here.", ephemeral=True)
            self.clear_items()
            for item in self.children: item.disabled = True
            try:
                await interaction.message.edit(view=self)
            except discord.HTTPException as e:
                 logger.warning(f"Failed to edit message on insufficient credits for user {user_id}: {e}", exc_info=True)
            # Original implementation of API cost deduction and history update
            # is generally sound. Logging calls are already present.
            # Ensure all paths through this function handle interaction responses or followups.
            # If an error occurs before interaction.response.defer() or followup, it might hang.
            # However, defer() is called early.

            # Reviewing for error message clarity:
            # - "This is not your adventure to control!" - Clear.
            # - "This adventure instance is outdated..." - Clear.
            # - Insufficient credits message - Clear.
            # - "A Discord error occurred..." - Generic but okay for HTTPExceptions.
            # - "An error occurred: {e}" - Provides the specific error to user, which might be too much technical detail.
            #   Consider a more generic "An unexpected error occurred. Please try again or contact support." for users,
            #   while the detailed error is logged for admins/devs.
            #   For now, let's leave it as is, as it's an internal tool, but for public, this would change.
            if user_id in active_adventures: del active_adventures[user_id] # End active adventure
            return

        self.history.append({'role': 'user', 'parts': [choice_text]})
        logger.debug(f"User {user_id} history updated with choice. History length: {len(self.history)}")

        try:
            story_result = story_engine.generate_story_segment(config.GEMINI_API_KEY, self.character, self.history)
            new_story_text = story_result['story_text']
            new_choices = story_result['choices']
            actual_api_cost = story_result['api_call_cost']
            logger.info(f"Story segment generated for user {user_id}. Cost: {actual_api_cost}. New story hint: '{new_story_text[:50]}...'")

            database.update_credits(self.db_conn, user_id, -actual_api_cost)
            remaining_credits = database.get_credits(self.db_conn, user_id)

            self.history.append({'role': 'model', 'parts': [new_story_text]})

            if user_id in active_adventures:
                 active_adventures[user_id]['history'] = self.history

            embed = discord.Embed(title=f"{self.character.name}'s Adventure", description=new_story_text, color=discord.Color.blurple())
            embed.set_footer(text=f"Credits remaining: {remaining_credits:.2f} | Choice cost: {actual_api_cost:.4f}")

            new_view = AdventureView(self.character, self.history, self.db_conn, self.cog_ref)
            for idx, choice_item in enumerate(new_choices): # Max 5 buttons for a view
                if idx < 5: # Ensure we don't add more than 5 buttons
                    new_view.add_item(ChoiceButton(label=choice_item[:80], custom_id=f"choice_{user_id}_{idx}_{interaction.message.id}"))

            await interaction.message.edit(embed=embed, view=new_view)
            new_view.message = interaction.message
            if user_id in active_adventures : active_adventures[user_id]['view_instance'] = new_view

            if remaining_credits < estimated_cost and remaining_credits > 0: # Check for next turn
                logger.info(f"User {user_id} has {remaining_credits:.2f} credits, potentially not enough for next action costing ~{estimated_cost}.")
                await interaction.followup.send("Warning: You may not have enough credits for your next choice!", ephemeral=True)
            elif remaining_credits <= 0:
                logger.info(f"User {user_id} ran out of credits. Adventure ending.")
                await interaction.followup.send("You have run out of credits! Your adventure ends here.", ephemeral=True)
                new_view.clear_items()
                for item in new_view.children: item.disabled = True
                await interaction.message.edit(view=new_view)
                if user_id in active_adventures: del active_adventures[user_id] # End active adventure

        except discord.HTTPException as e:
            logger.error(f"Discord API error during handle_choice for user {user_id}: {e}", exc_info=True)
            await interaction.followup.send("A Discord error occurred while processing your choice. Please try again.", ephemeral=True)
            self.clear_items() # Disable buttons on error
            if interaction.message:
                try: await interaction.message.edit(view=self)
                except Exception: pass
        except Exception as e:
            logger.error(f"Generic error during story generation or button handling for user {user_id}: {e}", exc_info=True)
            # Send a more generic error to the user for non-Discord errors
            await interaction.followup.send("An unexpected error occurred while processing your choice. The developers have been notified. Please try again later.", ephemeral=True)
            self.clear_items() # Disable buttons on error
            for item in self.children: item.disabled = True
            if interaction.message:
                try: await interaction.message.edit(view=self)
                except Exception: pass


class ChoiceButton(Button):
    """
    A simple UI Button subclass for representing a player's choice in the adventure.
    The custom_id is used for tracking and differentiation if needed, though label is used for action here.
    """
    def __init__(self, label: str, custom_id: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        """
        Callback triggered when this button is pressed.
        It delegates the choice handling to the parent AdventureView's `handle_choice` method.
        """
        view: AdventureView = self.view
        if view:
            await view.handle_choice(interaction, self.label)
        else:
            logger.error(f"ChoiceButton callback invoked without a valid view. Custom ID: {self.custom_id}, User: {interaction.user.id}")
            await interaction.response.send_message("Error: Could not process choice (view not found).", ephemeral=True)


class Adventure(commands.Cog):
    """
    The main cog for handling the text-based adventure game commands and interactions.
    This includes character creation, starting/resetting adventures, managing player choices,
    and credit balance operations.
    """
    def __init__(self, bot: discord.Bot):
        """
        Initializes the Adventure cog.

        Args:
            bot: The instance of the Discord bot.
        """
        self.bot = bot
        if hasattr(bot, 'db_connection') and bot.db_connection:
            self.db_conn = bot.db_connection
            logger.info("Adventure Cog initialized and using db_connection from bot object.")
        else:
            logger.warning("Adventure Cog: db_connection not found on bot, re-initializing for cog.")
            self.db_conn = database.init_db()

    async def cog_before_invoke(self, ctx: discord.ApplicationContext):
        """
        A special method that is called before any command in this cog is invoked.
        Ensures the database connection is active and the user exists in the credits table.
        """
        if self.db_conn is None:
            logger.warning("Adventure Cog: DB connection was None, re-initializing in cog_before_invoke.")
            self.db_conn = database.init_db()

        user_id = ctx.author.id
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT balance FROM user_credits WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            logger.info(f"User {user_id} not found in credits table during cog_before_invoke. Adding with 0.0 credits.")
            database.update_credits(self.db_conn, user_id, 0.0)

    async def initiate_adventure_flow(self, interaction_or_ctx: discord.Interaction | discord.ApplicationContext,
                                      character: Character, is_new_creation: bool = False):
        """
        Starts or continues the adventure for a given character.

        This function generates the initial story segment (or next segment if resuming, though
        resume is not fully implemented here) and presents it to the user with choices.
        It handles interactions originating from both modal submissions (new character)
        and slash commands (existing character).

        Args:
            interaction_or_ctx: The interaction or application context that triggered this flow.
            character: The Character object for whom the adventure is being initiated.
            is_new_creation: True if this flow is triggered immediately after character creation.
        """
        user_id = interaction_or_ctx.user.id
        logger.info(f"Initiating adventure flow for user {user_id} (Character: {character.name}). New creation: {is_new_creation}")
        history = [] # For MVP, always start with fresh history. Resume can be added later.

        send_method = None

        if isinstance(interaction_or_ctx, discord.Interaction) and is_new_creation: # Modal callback
            logger.debug(f"Modal callback for user {user_id}. Sending character created confirmation.")
            # Send initial confirmation for character creation then the main adventure message to channel
            await interaction_or_ctx.followup.send(f"Character '{character.name}' created successfully! Starting your adventure...", ephemeral=True)
            send_method = interaction_or_ctx.channel.send
        elif isinstance(interaction_or_ctx, discord.ApplicationContext): # Slash command context
            if not interaction_or_ctx.interaction.response.is_done():
                 logger.debug(f"Deferring ApplicationContext for user {user_id} in initiate_adventure_flow.")
                 await interaction_or_ctx.defer()
            send_method = interaction_or_ctx.respond
        else:
            logger.error(f"initiate_adventure_flow called with unexpected type: {type(interaction_or_ctx)} for user {user_id}")
            return

        try:
            logger.debug(f"Generating initial story segment for user {user_id}.")
            story_result = story_engine.generate_story_segment(config.GEMINI_API_KEY, character, history)
            story_text = story_result['story_text']
            choices = story_result['choices']
            logger.info(f"Initial story segment generated for user {user_id}. Story hint: '{story_text[:50]}...'")

            current_credits = database.get_credits(self.db_conn, user_id)
            history.append({'role': 'model', 'parts': [story_text]})

            embed = discord.Embed(title=f"{character.name}'s Adventure Begins!", description=story_text, color=discord.Color.green())
            embed.set_footer(text=f"Credits remaining: {current_credits:.2f}")

            view = AdventureView(character, history, self.db_conn, self)
            message_identifier_for_buttons = interaction_or_ctx.id

            for idx, choice_item in enumerate(choices):
                if idx < 5:
                    view.add_item(ChoiceButton(label=choice_item[:80], custom_id=f"choice_{user_id}_{idx}_{message_identifier_for_buttons}"))

            message_sent = await send_method(embed=embed, view=view, ephemeral=False)

            actual_message = None
            if message_sent is None:
                 actual_message = await interaction_or_ctx.original_response()
            elif isinstance(message_sent, discord.InteractionMessage):
                actual_message = message_sent
            elif isinstance(message_sent, discord.Message):
                actual_message = message_sent

            if actual_message:
                view.message = actual_message
                active_adventures[user_id] = {
                    'character': character, 'history': history,
                    'message_id': actual_message.id, 'view_instance': view
                }
                logger.info(f"Adventure flow initiated for user {user_id}. Message ID: {actual_message.id}")
            else:
                logger.error(f"Could not determine message ID to store for user {user_id} after initiate_adventure_flow.")

        except discord.HTTPException as e:
            logger.error(f"Discord API error initiating adventure flow for user {user_id}: {e}", exc_info=True)
            error_send_method = interaction_or_ctx.followup.send if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.respond
            await error_send_method(f"A Discord error occurred while starting the adventure: {e}. Please try again later.", ephemeral=True)
        except Exception as e:
            logger.error(f"Generic error initiating adventure flow for user {user_id}: {e} (Type: {type(e)})", exc_info=True)
            error_send_method = interaction_or_ctx.followup.send if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.respond
            try:
                await error_send_method("An unexpected error occurred while starting your adventure. The developers have been notified.", ephemeral=True)
            except Exception as e2:
                 logger.error(f"Further error sending error message to user {user_id}: {e2}", exc_info=True)


    @commands.slash_command(name="start_adventure", description="Begin your text-based adventure!")
    async def start_adventure(self, ctx: discord.ApplicationContext):
        """
        Command to start a new adventure or resume an existing one (currently starts new).
        Checks for existing character, initiates creation if none.
        Grants initial credits to new players.
        """
        user_id = ctx.author.id
        logger.info(f"/start_adventure invoked by user {user_id} ({ctx.author.name}).")

        # Check for an already active adventure for this user
        if user_id in active_adventures:
            try:
                adventure_data = active_adventures[user_id]
                msg_id = adventure_data.get('message_id')
                view_instance = adventure_data.get('view_instance')

                # If view is still active (not timed out / finished)
                if msg_id and view_instance and not view_instance.is_finished():
                    channel = self.bot.get_channel(ctx.channel_id) or ctx.channel
                    if channel:
                        old_message = await channel.fetch_message(msg_id)
                        logger.info(f"User {user_id} tried to start an adventure but already has one active: {old_message.jump_url}")
                        await ctx.respond(f"You have an adventure already in progress: {old_message.jump_url}\nUse `/reset_adventure` if you want to start over.", ephemeral=True)
                        return
                else:
                    logger.debug(f"Removing stale active_adventures entry for user {user_id} during /start_adventure check.")
                    del active_adventures[user_id]
            except discord.NotFound: # If message was deleted
                logger.info(f"Previous adventure message not found for user {user_id}. Allowing new adventure.")
                del active_adventures[user_id]
            except Exception as e: # Other errors
                logger.error(f"Error checking active adventure for {user_id}: {e}", exc_info=True)
                if user_id in active_adventures: del active_adventures[user_id] # Clean up if error

        # Grant initial credits if user has no credit record yet
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT balance FROM user_credits WHERE user_id = ?", (user_id,))
        credit_row = cursor.fetchone()

        if not credit_row:
             logger.info(f"New user {user_id} for credits. Granting initial {INITIAL_CREDITS:.2f} credits.")
             database.update_credits(self.db_conn, user_id, INITIAL_CREDITS)
             try:
                await ctx.author.send(f"Welcome, adventurer! I've granted you an initial {INITIAL_CREDITS:.2f} credits to start your journey.")
             except discord.Forbidden: # User might have DMs disabled
                logger.warning(f"Could not DM user {user_id} about initial credits.")
                await ctx.send(f"Welcome, adventurer! I've granted you an initial {INITIAL_CREDITS:.2f} credits. (I tried to DM you this too!)",ephemeral=True)

        # Check for existing character
        char = database.get_character(self.db_conn, user_id)
        if not char:
            logger.info(f"No character found for user {user_id}. Sending character creation modal.")
            modal = CharacterCreationModal(db_conn=self.db_conn, cog_ref=self)
            await ctx.send_modal(modal)
        else:
            logger.info(f"Character found for user {user_id} ('{char.name}'). Initiating adventure flow.")
            await self.initiate_adventure_flow(ctx, char)

    @commands.slash_command(name="reset_adventure", description="[DANGER] Deletes your character and resets your adventure.")
    async def reset_adventure(self, ctx: discord.ApplicationContext):
        """
        Command to delete the user's current character and clear any active adventure state.
        Requires confirmation due to its destructive nature.
        """
        user_id = ctx.author.id
        logger.info(f"/reset_adventure invoked by user {user_id} ({ctx.author.name}). Sending confirmation.")

        confirm_view = View(timeout=30) # Short timeout for confirmation
        yes_button = Button(label="Yes, delete my character!", style=discord.ButtonStyle.danger, custom_id=f"confirm_reset_{user_id}")
        no_button = Button(label="No, keep my character.", style=discord.ButtonStyle.secondary, custom_id=f"cancel_reset_{user_id}")

        async def reset_confirmed_callback(interaction: discord.Interaction):
            if interaction.user.id != user_id: # Ensure correct user confirms
                logger.warning(f"User {interaction.user.id} tried to confirm reset for user {user_id}.")
                await interaction.response.send_message("This is not your confirmation button!", ephemeral=True)
                return

            logger.info(f"Reset confirmed by user {user_id}. Deleting character and active adventure.")
            await interaction.response.defer(ephemeral=True, thinking=True) # Acknowledge, work in followup

            # Delete character from DB
            db_cursor = self.db_conn.cursor()
            db_cursor.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))
            self.db_conn.commit()
            logger.info(f"Character data deleted from DB for user {user_id}.")

            # Clear from active adventures and try to delete old message
            if user_id in active_adventures:
                try:
                    old_message_id = active_adventures[user_id].get('message_id')
                    if old_message_id:
                        channel = interaction.channel or self.bot.get_channel(ctx.channel_id) # Use interaction's channel if available
                        if channel:
                             old_message = await channel.fetch_message(old_message_id)
                             await old_message.delete()
                             logger.info(f"Old adventure message {old_message_id} deleted for user {user_id}.")
                except discord.NotFound:
                    logger.info(f"Old adventure message {old_message_id} for user {user_id} not found during reset (already deleted?).")
                except discord.HTTPException as e:
                    logger.error(f"Discord API error deleting old adventure message {old_message_id} for user {user_id}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Could not delete old adventure message {old_message_id} for user {user_id} during reset: {e}", exc_info=True)
                del active_adventures[user_id]
                logger.info(f"Active adventure cleared for user {user_id}.")

            await interaction.followup.send("Your character has been deleted. Use `/start_adventure` to create a new one.", ephemeral=True)
            confirm_view.clear_items() # Disable buttons on original message
            for item in confirm_view.children: item.disabled = True
            try: await ctx.edit(view=confirm_view) # Edit original confirmation message
            except discord.HTTPException as e: logger.warning(f"Failed to edit original reset confirmation message for user {user_id}: {e}", exc_info=True)


        async def reset_cancelled_callback(interaction: discord.Interaction):
            if interaction.user.id != user_id:
                await interaction.response.send_message("This is not your confirmation button!", ephemeral=True)
                return
            logger.info(f"Reset cancelled by user {user_id}.")
            confirm_view.clear_items() # Disable buttons
            for item in confirm_view.children: item.disabled = True
            await interaction.response.edit_message(content="Character reset cancelled.", view=confirm_view)

        yes_button.callback = reset_confirmed_callback
        no_button.callback = reset_cancelled_callback
        confirm_view.add_item(yes_button)
        confirm_view.add_item(no_button)

        await ctx.respond("Are you sure you want to delete your character and reset your adventure? This action cannot be undone.", view=confirm_view, ephemeral=True)


    @commands.slash_command(name="balance", description="Check your current credit balance.")
    async def balance(self, ctx: discord.ApplicationContext):
        """Displays the invoking user's current credit balance."""
        user_id = ctx.author.id
        credits = database.get_credits(self.db_conn, user_id)
        logger.info(f"/balance invoked by user {user_id}. Balance: {credits:.2f}")
        await ctx.respond(f"You currently have {credits:.2f} credits.", ephemeral=True)

    @commands.slash_command(name="add_credits", description="[Admin] Add credits to a user.")
    @commands.check(lambda ctx: str(ctx.author.id) == str(config.ADMIN_USER_ID))
    async def add_credits(self, ctx: discord.ApplicationContext,
                          user: Option(discord.Member, "The user to add credits to"),
                          amount: Option(float, "The amount of credits to add")):
        """
        Admin command to add credits to a specified user.
        Restricted to the ADMIN_USER_ID defined in the configuration.
        """
        logger.info(f"/add_credits invoked by admin {ctx.author.id} for user {user.id}, amount {amount}.")
        if amount <= 0:
            logger.warning(f"Admin {ctx.author.id} tried to add non-positive amount of credits: {amount}")
            await ctx.respond("Please provide a positive amount of credits.", ephemeral=True)
            return

        database.update_credits(self.db_conn, user.id, amount)
        await ctx.respond(f"Successfully added {amount:.2f} credits to {user.mention}. Their new balance is {database.get_credits(self.db_conn, user.id):.2f}.", ephemeral=True)

    @add_credits.error
    async def add_credits_error(self, ctx: discord.ApplicationContext, error: Exception):
        """Error handler for the /add_credits command."""
        if isinstance(error, commands.CheckFailure):
            logger.warning(f"User {ctx.author.id} failed admin check for /add_credits.")
            await ctx.respond("You do not have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in /add_credits command by {ctx.author.id}: {error}", exc_info=True)
            await ctx.respond("An error occurred while processing the command. Please check the logs.", ephemeral=True)


def setup(bot: discord.Bot):
    """Standard setup function for a cog, called by discord.py when loading the extension."""
    adventure_cog = Adventure(bot)
    bot.add_cog(adventure_cog)
    logger.info("Adventure Cog loaded successfully.")
