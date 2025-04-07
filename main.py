import discord
import os
from dotenv import load_dotenv
import yt_dlp
import asyncio
from discord.ext import commands
from handlers import *
from formatter import *
import datetime
import random
import sqlite3

load_dotenv() # load all the variables from the env file
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = commands.Bot(intents=intents)

player = Player() #start the player object
session = Session(None, None)

class Buttons(discord.ui.View):
    '''
    The player object, the main message that will display a "music player"
    this will be updated and treated like a UI from an app, with all the
    implied limitations from it being a discord message of course.
    Might not be the best looking thing ever but this is the only way
    I found to make every function that I wanted to work work.
    '''
    def __init__(self, status, *args, **kwargs):
        super().__init__(timeout=None)
        self.playerStatus = status
        self.is_paused = False

        for child in self.children:
            if child.custom_id == "back":
                self.buttonBack = child
            elif child.custom_id == "pause":
                self.buttonPause = child
            elif child.custom_id == "skip":
                self.buttonSkip = child
            elif child.custom_id == "loop":
                self.buttonLoop = child
            elif child.custom_id == "shuffle":
                self.buttonShuffle = child
            elif child.custom_id == "restart":
                self.buttonRestart = child
            elif child.custom_id == "stop":
                self.buttonStop = child
        self.updateButtons()

    def updateButtons(self):
        '''Update all button to disabled state based on player status'''    
        # If player is not active, disable all buttons
        if self.playerStatus == 0:
            self.buttonBack.disabled = True
            self.buttonPause.disabled = True
            self.buttonSkip.disabled = True
            self.buttonLoop.disabled = True
            self.buttonShuffle.disabled = True
            self.buttonRestart.disabled = True
            self.buttonStop.disabled = True
        else:
            self.buttonBack.disabled = False
            self.buttonPause.disabled = False
            self.buttonSkip.disabled = False
            self.buttonLoop.disabled = False
            self.buttonShuffle.disabled = False
            self.buttonRestart.disabled = False
            self.buttonStop.disabled = False

            # Update pause button label based on current state
            if self.is_paused:
                self.buttonPause.label = "Resume"
                self.buttonPause.emoji = u"\u25B6"  # Play symbol
                self.buttonPause.style = discord.ButtonStyle.success
            else:
                self.buttonPause.label = "Pause"
                self.buttonPause.emoji = u"\u23F8"  # Pause symbol
            
            # Update loop button style based on player's loop state
            if hasattr(player, 'loop') and player.loop:
                self.buttonLoop.style = discord.ButtonStyle.success
            else:
                self.buttonLoop.style = discord.ButtonStyle.secondary

    @discord.ui.button(label="Back", custom_id="back", row=0, style=discord.ButtonStyle.primary, emoji=u"\u23EE", disabled=True)
    async def prev_button_callback(self, button, interaction):
      if player.queueIndex > 0:
          # Simply setting trhe queue index back by 2 numbers since the song finishing will increase it by 1
          player.queueIndex -= 2
      
          # Just stop the current playback, the after_callback will handle starting the previous song
          if session.voice_client and (session.voice_client.is_playing() or session.voice_client.is_paused()):
              session.voice_client.stop()
          
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("Playing Previous Song", ephemeral=True, delete_after=2)
      else:
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("There is no song before this one", ephemeral=True, delete_after=2)
    
    @discord.ui.button(label="Pause", custom_id="pause", row=0, style=discord.ButtonStyle.primary, emoji=u"\u23F8", disabled=True)
    async def pause_button_callback(self, button, interaction):
      if session.voice_client and session.voice_client.is_playing():
          session.voice_client.pause()
          self.is_paused = True
          self.updateButtons()
          await editMessage(session.ctx, 1)  # Update message to show paused state
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("Content Paused", ephemeral=True, delete_after=2)
      elif session.voice_client and session.voice_client.is_paused():
          session.voice_client.resume()
          self.is_paused = False
          self.updateButtons()
          await editMessage(session.ctx, 1)  # Update message to show playing state
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("Content Resumed", ephemeral=True, delete_after=2)
      else:
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("No audio playing", ephemeral=True, delete_after=2)
  
    @discord.ui.button(label="Skip", custom_id="skip", row=0, style=discord.ButtonStyle.primary, emoji=u"\u23ED", disabled=True)
    async def skip_button_callback(self, button, interaction):
      if session.voice_client and (session.voice_client.is_playing() or session.voice_client.is_paused()):
        session.voice_client.stop()  # This will trigger the after_callback which calls songFinished
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Playing Next song", ephemeral=True, delete_after=2)
      else:
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("No audio playing to skip", ephemeral=True, delete_after=2)
  
    @discord.ui.button(label="Loop", custom_id="loop", row=1, style=discord.ButtonStyle.secondary, emoji=u"\U0001F501", disabled=True)
    async def loop_button_callback(self, button, interaction):
      # Toggle looping state
      player.loop = not player.loop
  
      if player.loop:
          button.style = discord.ButtonStyle.success
          loop_status = "Loop On"
      else:
          button.style = discord.ButtonStyle.secondary
          loop_status = "Loop Off"
  
      if player.status == 1:
          await editMessage(session.ctx, 1)
  
      await interaction.response.edit_message(view=self)
      await interaction.followup.send(loop_status, ephemeral=True, delete_after=2)
    
    @discord.ui.button(label="Shuffle", custom_id="shuffle", row=1, style=discord.ButtonStyle.secondary, emoji=u"\U0001F500", disabled=True)
    async def shuffle_button_callback(self, button, interaction):
      if len(player.queue) > player.queueIndex + 1:
          # Save current song
          current = player.queue[player.queueIndex]
      
          # Get remaining songs and shuffle them
          remaining = player.queue[player.queueIndex+1:]
          random.shuffle(remaining)
      
          # Reconstruct queue ignoring current song and all the previosuly played
          player.queue = player.queue[:player.queueIndex+1] + remaining
      
          if player.status == 1:
              await editMessage(session.ctx, 1)
          
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("Shuffled Queue", ephemeral=True, delete_after=2)
      else:
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("No songs in queue to shuffle", ephemeral=True, delete_after=2)
  
    @discord.ui.button(label="Restart", custom_id="restart", row=1, style=discord.ButtonStyle.secondary, emoji=u"\U0001F504", disabled=True)
    async def restart_button_callback(self, button, interaction):
      if session.voice_client and player.currentSong:
          # -1 to restart the song, it will go to 0 because of after_callback
          player.queueIndex -= 1
      
          # Just stop the current playback, the after_callback will handle starting the song again
          if session.voice_client and (session.voice_client.is_playing() or session.voice_client.is_paused()):
              session.voice_client.stop()
          
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("Restarting Current Song", ephemeral=True, delete_after=2)
      else:
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("No song playing to restart", ephemeral=True, delete_after=2)
  
    @discord.ui.button(label="Stop", custom_id="stop", row=2, style=discord.ButtonStyle.danger, emoji=u"\u23F9", disabled=True)
    async def stop_button_callback(self, button, interaction):
      if session.voice_client:
          # Reset player state
          player.currentSong = ""
          player.queue = []
          player.queueIndex = -1
          player.leftQueue = []
          player.status = 0
          player.lyrics = 0
          player.currentSongUrl = ""
          player.currentSongUploader = ""
          player.currentSongUploaderUrl = ""
          player.currentSongDuration = ""
          player.currentSongThumbnail = ""
      
          # Disconnect from voice
          await session.voice_client.disconnect()
      
          # Update the message
          self.playerStatus = 0
          self.updateButtons()
      
          await editMessage(session.ctx, 0)
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("Player Off", ephemeral=True, delete_after=2)
      else:
          await interaction.response.edit_message(view=self)
          await interaction.followup.send("Player already off", ephemeral=True, delete_after=2)

@bot.event
async def on_ready():
    '''
    This will be called everytime the bot restarts/starts, it will check for
    existing players and reset them in order to show current playback status
    '''
    player.loop = False

    bot.add_view(Buttons(0))
    print('Bot {0.user} is running'.format(bot))
    print("-----------------------------------------")
    print("BOT ID: " + str(bot.user.id))
    print("DISCORD VERSION: " + str(discord.__version__))
    print(f'SERVER COUNT: {len(bot.guilds)}')
    for server in bot.guilds:
        print(server.name)
        info = getGuildInfos(server.id)
        try:
          playerChannel = bot.get_channel(info["channelID"])
          message = await playerChannel.fetch_message(info["messageID"])
          await message.edit(content="so lonely in here", embed=embedCreator(((248,200,248), ":cricket: Nothing Playing", "So lonely in here...")), view=Buttons(0))
        except Exception as e:
          print(e)
    print("-----------------------------------------")

async def handleVoice(ctx, leave=False):
  '''
  everything about disconnecting or reconnecting to a channel
  '''
  if leave:
    await ctx.voice_client.disconnect()
    return
  else:
    if not ctx.author.voice:
          await ctx.followup.send("You are not connected to a voice channel!")
          return
  
      # Get the voice channel
    voice_channel = ctx.author.voice.channel
  
    # First check if voice client exists before trying to access its properties
    if ctx.voice_client is None:
      # Connect to the voice channel if not connected
      voice_client = await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
      # Different voice channel case
      await ctx.followup.send("You are on a different voice channel!")
      return
    else:
      # Already connected to the same channel
      voice_client = ctx.voice_client
    return voice_client

async def editMessage(ctx, kind):
    match kind:
        case 0:
            embed=embedCreator(((248,200,248), ":cricket: Nothing Playing", "So lonely in here..."))
            buttons = Buttons(0)
        case 1:
            lyrics=beautifyLyrics(findLyrics(player.currentSong))
            embedTitle = ((248,200,248), "Lyrics", lyrics)
            #embedTitle = ((248,200,248), "Now Playing", f"[{player.currentSong}]({player.currentSongUrl})")
            embedField1 = ("field", ":headphones: Track", f"{player.queueIndex + 1}/{len(player.queue)} [{player.currentSong}]({player.currentSongUrl})", False)
            embedField2 = ("field", "Duration", f"{player.currentSongDuration}", True)
            embedField3 = ("field", "Uploader", f"[{player.currentSongUploader}]({player.currentSongUploaderUrl})", True)
            if player.queueIndex > 0:
              previousSong = f"-# {player.queue[player.queueIndex-1]}  \n"
            else:
              previousSong = ""
            if player.queueIndex == len(player.queue)-1:
              nextSong = ""
            else:
              nextSong = f"\n-# {player.queue[player.queueIndex+1]}"
            embedField4 = ("field", "Queue", f"{previousSong}> **{player.queue[player.queueIndex]}** {nextSong}", True)
            embedImage = ("image", player.currentSongThumbnail)
            embedFooter = ("footer", f"Loop: {'On' if hasattr(player, 'loop') and player.loop else 'Off'}", "")
            embed = embedCreator(embedTitle, embedField1, embedField2, embedField3, embedField4, embedImage, embedFooter)
            buttons = Buttons(1)
            if hasattr(session, 'voice_client') and session.voice_client and session.voice_client.is_paused():
                buttons.is_paused = True
                buttons.updateButtons()

    info = getGuildInfos(session.ctx.guild.id)
    playerChannel = bot.get_channel(info["channelID"])
    try:
        message = await playerChannel.fetch_message(info["messageID"])
        await message.edit(content="", embed=embed, view=buttons)
        print("player updated")
    except Exception as e:
        message = await ctx.send("Main Player", embed=embed, view=buttons)
        print("New player created")
        print(f"A new player was created because: {e}")
        updateSession(ctx.guild.id, ctx.channel.id, message.id)

async def songFinished(ctx, voice_client, error=False):
    print("Song finished function called")
    # Make sure voice_client exists and is connected
    if ctx.voice_client and ctx.voice_client.is_connected():
        print("Song finished")
    
        # Handle looping if enabled
        if hasattr(player, 'loop') and player.loop and player.queueIndex >= 0:
            # Don't increment the index, just restart the current song, same as the restart button above
            player.queueIndex -= 1
        
        await startMusic(session.ctx, voice_client)
    else:
        print("Voice client not connected")

async def startMusic(ctx, voice_client):
   '''
   This function starts the music by calling the ytld class in handlers.py
   and handling incrementing songs after one finished, also updating the 
   player
   '''
   player.queueIndex += 1
   if player.queueIndex == len(player.queue):
     print("Songs Finished")
     player.currentSong = ""
     player.queue = []
     player.queueIndex = -1
     player.leftQueue = []
     player.status = 0
     player.lyrics = 0
     player.currentSongUrl = ""
     player.currentSongUploader = ""
     player.currentSongUploaderUrl = ""
     player.currentSongDuration = ""
     player.currentSongThumbnail = ""
     player.ctx = None
     await handleVoice(ctx, leave=True)
     await editMessage(ctx, 0)
     return
   try:
     # Get the audio source from the URL
     ytdlc = await YTDLSource.from_url(player.queue[player.queueIndex], loop=bot.loop, stream=True)
 
     def after_callback(error):
       print(f"After callback triggered, error: {error}")    
       asyncio.run_coroutine_threadsafe(songFinished(ctx, voice_client, error=error), bot.loop)                
     voice_client.stop()
     voice_client.play(ytdlc, after=after_callback)
     player.currentSong = ytdlc.title
     player.currentSongUrl = ytdlc.url
     player.currentSongUploader = ytdlc.uploader
     player.currentSongUploaderUrl = ytdlc.uploader_url
     player.currentSongDuration = ytdlc.duration
     player.currentSongThumbnail = ytdlc.thumbnail
     player.status = 1
     await editMessage(session.ctx, 1)
   except Exception as e:
     await ctx.followup.send(f"An error occurred: {str(e)}", ephemeral=True, delete_after=8)
     return

@bot.slash_command(name="play", description="play music!", guild_ids=[697189706995335219])
@discord.option("song", type=discord.SlashCommandOptionType.string)
async def playMusic(ctx: discord.ApplicationContext, song: str, from_queue=False):
    '''
    The main function, this will handle mostly the queue and pass the songs to play
    to the right function.
    '''
    await ctx.defer(ephemeral=True)
    toPlay = extractSongs(song)
    session.ctx = ctx
    if type(toPlay) == list:
        try:
            for track in toPlay:
                if len(player.queue) >= 500:
                    await ctx.followup.send(f"The queue has reached 500 songs of length, no more songs will be added from the playlist", ephemeral=True, delete_after=8)
                    break
                player.queue.append(track)
        except Exception as e:
            await ctx.followup.send(f"An error occurred: {str(e)}", ephemeral=True, delete_after=8)
            return
    else:
        if len(player.queue) >= 500:
            await ctx.followup.send(f"The queue has reached 500 songs of length, please reset the player with the stop button to add more", ephemeral=True, delete_after=8)
            return
        player.queue.append(toPlay)

    if player.status == 0:
        voice = await handleVoice(ctx, False)
        session.voice_client = voice
        await startMusic(ctx, voice)
        await session.ctx.followup.send("Updated main command", ephemeral=True, delete_after=2)
    else:
        await editMessage(ctx, 1)
        await ctx.followup.send(f"Added to queue", ephemeral=True, delete_after=2)


bot.run(os.getenv('BOT_TOKEN'))
