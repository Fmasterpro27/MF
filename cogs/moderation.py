import discord
from discord.ext import commands
import sqlite3
import datetime
from discord.ui import Button, View

class AcceptTerms(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green, custom_id="accept_terms")
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        conn = sqlite3.connect('terms_acceptance.db')
        c = conn.cursor()
        
        # Record acceptance with user details
        c.execute("INSERT OR REPLACE INTO accepted_terms VALUES (?, ?, ?, ?, ?)",
                 (interaction.user.id, 
                  str(interaction.user),
                  interaction.user.display_name,
                  interaction.user.created_at.isoformat(),
                  datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(
            "✅ Terms accepted! You can now use the autoplay commands.",
            ephemeral=True
        )

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.red, custom_id="decline_terms")
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "❌ You must accept the terms to use this bot.",
            ephemeral=True
        )

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_servers = [server id]  # Your server IDs

    async def cog_check(self, ctx):
        if ctx.guild.id not in self.allowed_servers:
            await ctx.send("❌ This bot is not authorized for this server.")
            return False
        return True

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban a user with DM notification"""
        try:
            # Send DM to banned user
            embed = discord.Embed(
                title=f"You were banned from {ctx.guild.name}",
                description=f"Reason: {reason}\n\n"
                          f"Moderator: {ctx.author.display_name}",
                color=discord.Color.red()
            )
            await member.send(embed=embed)
        except discord.Forbidden:
            pass  # User has DMs disabled

        # Execute ban
        await member.ban(reason=reason)
        await ctx.send(f"✅ {member.display_name} has been banned.")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kick a user with DM notification"""
        try:
            # Send DM to kicked user
            embed = discord.Embed(
                title=f"You were kicked from {ctx.guild.name}",
                description=f"Reason: {reason}\n\n"
                          f"Moderator: {ctx.author.display_name}",
                color=discord.Color.orange()
            )
            await member.send(embed=embed)
        except discord.Forbidden:
            pass  # User has DMs disabled

        
        await member.kick(reason=reason)
        await ctx.send(f"✅ {member.display_name} has been kicked.")

    @commands.command()
    async def showterms(self, ctx):
        """Display the bot's terms of service"""
        with open('terms.txt', 'r') as f:
            terms = f.read()
        
        embed = discord.Embed(
            title="Bot Terms of Service",
            description=terms,
            color=discord.Color.blue()
        )
        embed.set_footer(text="You must accept these terms to use the bot.")
        embed.timestamp = datetime.datetime.now()

        if not await self.check_terms_acceptance(ctx.author.id):
            embed.add_field(
                name="⚠️ Terms Acceptance Required",
                value="You must accept the terms to use this bot.",
                inline=False
            )
            await ctx.send(embed=embed, view=AcceptTerms())
        else:
            await ctx.send(embed=embed)

    async def check_terms_acceptance(self, user_id):
        conn = sqlite3.connect('terms_acceptance.db')
        c = conn.cursor()
        c.execute("SELECT 1 FROM accepted_terms WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None

async def setup(bot):
    await bot.add_cog(Moderation(bot))
