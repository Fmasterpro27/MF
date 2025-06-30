import discord
from discord.ext import commands
from discord.ui import Button, View
import sqlite3
import random
import datetime
import json
from typing import Optional

def init_db():
    conn = sqlite3.connect('terms_acceptance.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accepted_terms
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  display_name TEXT,
                  account_created TEXT,
                  accept_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pending_commands
                 (user_id INTEGER PRIMARY KEY,
                  target_user_id INTEGER,
                  server_id INTEGER)''')
    conn.commit()
    conn.close()

init_db()

class AcceptTermsView(View):
    def __init__(self, target_user: Optional[discord.Member] = None):
        super().__init__(timeout=None)
        self.target_user = target_user
        
    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green, custom_id="accept_terms")
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        conn = sqlite3.connect('terms_acceptance.db')
        c = conn.cursor()
        
        # Record acceptance
        c.execute("INSERT OR REPLACE INTO accepted_terms VALUES (?, ?, ?, ?, ?)",
                 (interaction.user.id, 
                  str(interaction.user),
                  interaction.user.display_name,
                  interaction.user.created_at.isoformat(),
                  datetime.datetime.now().isoformat()))
        
        # Check for pending command
        c.execute("SELECT target_user_id, server_id FROM pending_commands WHERE user_id=?", (interaction.user.id,))
        pending = c.fetchone()
        
        if pending:
            target_user_id, server_id = pending
            # Delete the pending command
            c.execute("DELETE FROM pending_commands WHERE user_id=?", (interaction.user.id,))
            
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(
            "✅ Terms accepted! Processing your command...",
            ephemeral=True
        )
        
        # If there was a pending command, execute it
        if pending:
            guild = self.bot.get_guild(server_id)
            target_user = guild.get_member(target_user_id)
            if guild and target_user:
                # Get the original command context
                ctx = await self.bot.get_context(interaction.message)
                ctx.author = interaction.user
                # Run the command
                await self.autoplay_command(ctx, target_user)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.red, custom_id="decline_terms")
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        conn = sqlite3.connect('terms_acceptance.db')
        c = conn.cursor()
        c.execute("DELETE FROM pending_commands WHERE user_id=?", (interaction.user.id,))
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(
            "❌ Terms declined. Command cancelled.",
            ephemeral=True
        )

class Autoplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.autoplay_users = set()
        self.allowed_servers = ["your server id"]  # Your server IDs
        
        with open('data/responses.json', 'r') as f:
            data = json.load(f)
            self.responses = random.sample(data['responses'], k=len(data['responses']))
            
        self.bot.add_view(AcceptTermsView())  # Persistent view

    async def check_terms_acceptance(self, user_id):
        conn = sqlite3.connect('terms_acceptance.db')
        c = conn.cursor()
        c.execute("SELECT 1 FROM accepted_terms WHERE user_id=?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None

    async def autoplay_command(self, ctx, user: discord.Member):
        """The actual autoplay command logic"""
        if user.id in self.autoplay_users:
            self.autoplay_users.remove(user.id)
            await ctx.send(f'Autoplay disabled for {user.display_name}')
        else:
            self.autoplay_users.add(user.id)
            await ctx.send(f'Autoplay enabled for {user.display_name}')

    @commands.command(name='autoplay')
    async def autoplay(self, ctx, user: discord.Member):
        if ctx.guild.id not in self.allowed_servers:
            return await ctx.send("❌ This bot is not authorized for this server.")
            
        if await self.check_terms_acceptance(ctx.author.id):
            # Terms already accepted, execute immediately
            await self.autoplay_command(ctx, user)
        else:
            # Store the pending command
            conn = sqlite3.connect('terms_acceptance.db')
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO pending_commands VALUES (?, ?, ?)",
                     (ctx.author.id, user.id, ctx.guild.id))
            conn.commit()
            conn.close()
            
            # Show terms acceptance
            embed = discord.Embed(
                title="⚠️ TERMS OF USE",
                description=(
                    "**This bot is for private use only!**\n\n"
                    "By using this bot you agree:\n"
                    "- This is for fun only\n"
                    "- Not for public servers\n"
                    "- No harassment allowed\n"
                    "- All activity is logged\n\n"
                    f"Pending command: `autoplay {user.display_name}`\n"
                    "You must accept these terms to continue."
                ),
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed, view=AcceptTermsView(target_user=user))

    @commands.Cog.listener()
    async def on_message(self, message):
        if (not message.guild or 
            message.guild.id not in self.allowed_servers or
            message.author.bot):
            return
            
        if message.author.id in self.autoplay_users:
            await message.reply(random.choice(self.responses), mention_author=True)

async def setup(bot):
    await bot.add_cog(Autoplay(bot))
