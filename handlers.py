import sqlite3
import os
import requests
import discord
import yt_dlp
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import datetime
import re
load_dotenv()


class MyView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)
        self.button1 = None
        self.button2 = None
        self.lyrics_status = 0
        for child in self.children:
            if child.label == "Button 1":
                self.button1 = child
            elif child.label == "Button 2":
                self.button2 = child

    @discord.ui.button(label="Button 1", custom_id="button-1", row=0, style=discord.ButtonStyle.primary)
    async def first_button_callback(self, button, interaction):
        self.button1.disabled = True
        self.button2.disabled = False
        self.button2.label = "Button 2"  # Reset label if needed
        if self.lyrics_status == 0:
           self.lyrics_status = 1
           lyrics_ui = "(on)"
        else:
           self.lyrics_status = 0
           lyrics_ui = "(off)"
        self.button1.label = "Lyrics" + lyrics_ui

        await interaction.response.edit_message(content="lol", view=self)

    @discord.ui.button(label="Button 2", custom_id="button-2", row=1, style=discord.ButtonStyle.primary)
    async def second_button_callback(self, button, interaction):
        self.button2.disabled = True
        self.button2.label = "No more pressing!"
        self.button1.disabled = False
        self.button1.label = "Button 1"  # Reset label if needed

        await interaction.response.edit_message(content="lel", view=self)




###########################################################################
######################FUNCTIONS############################################
###########################################################################

def checkSession(guildID):
  '''
  Checks if the session for this guild exists/was ever created
  '''
  connection = sqlite3.connect('database/guilds.db')
  cursor = connection.cursor()
  cursor.execute('''
    CREATE TABLE IF NOT EXISTS guilds (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    channel_id INTEGER,
    message_id INTEGER
    )
  ''')
  connection.commit()
  cursor.execute("SELECT * FROM guilds WHERE guild_id = ?", (guildID,))
  rows = cursor.fetchall()
  connection.close()
  if len(rows) == 0:
    return 0
  else:
    return 1

#--------------------------------------------------------------------------------------#

def updateSession(guildID, channelID, messageID):
  '''
  This function creates or updates a database entry the first time the play 
  message is called by a user in that specific server. This will be the only 
  message ever used to talk by the bot and it will be constantly updated when needed
  '''
  connection = sqlite3.connect('database/guilds.db')
  cursor = connection.cursor()
  

  if checkSession(guildID) == 0:
    cursor.execute("INSERT INTO guilds (guild_id, channel_id, message_id) VALUES (?, ?, ?)", (guildID, channelID, messageID,))
    connection.commit()
  else:
    cursor.execute("UPDATE guilds SET channel_id = ?, message_id = ? WHERE guild_id = ?", (channelID, messageID, guildID,))
    connection.commit()
  
  
  connection.close()
  return None
  
#--------------------------------------------------------------------------------------#

def getGuildInfos(guildID):
  '''
  This function is just for retriving basic information about a guild and its player
  '''
  connection = sqlite3.connect('database/guilds.db')
  cursor = connection.cursor()
  cursor.execute("SELECT * FROM guilds WHERE guild_id = ?", (guildID,))
  rows = cursor.fetchall()
  connection.close()
  return {"guildID": rows[0][1], "channelID": rows[0][2], "messageID": rows[0][3]}
  
#--------------------------------------------------------------------------------------#

def findLyrics(input):
  '''
  This function is used to retrive lyrics from LRCLib.com free and open-source API
  If available, the lyrics will be extracted with timestamps and will be synchronized
  by the beautifier later
  '''
  input = re.sub(r'\(.*\)', '', input)
  api_url = f"https://lrclib.net/api/search?q={input}"
  response = requests.get(api_url)
  response = response.json()
  if len(response) == 0:
    return "Lyrics not found"
  elif response[0]['syncedLyrics'] != None:
    return (response[0]['syncedLyrics'], True)
  else:
    return response[0]['plainLyrics']


#--------------------------------------------------------------------------------------#

def extractSongs(link):
  '''
  This function is used to check if the song the user wants to play comes
  from a spotify link of a track/playlist or a youtube playlist.
  '''
  sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=os.getenv('SPOTIFY_ID'), client_secret=os.getenv('SPOTIFY_SECRET')))
  if "spotify.com/track" in link:
     try:

        track_id = link.split("track/")[1].split("?")[0] #Handles links

        track = sp.track(track_id)
        track_name = track['name']
        track_artist = track['artists'][0]['name']

        return f"{track_name} {track_artist}"

     except spotipy.exceptions.SpotifyException as e:
        print(f"Error: {e}")
        return None
     except Exception as general_e:
        print(f"An unexpected error occured: {general_e}")
        return None
  
  elif "spotify.com/album" in link:
    album_id = link.split("album/")[1].split("?")[0]
    album = sp.album_tracks(album_id)
    tracks = []
    for track in album["items"]:
      track_name = track["name"] + " " + track['artists'][0]['name']
      tracks.append(track_name)
    return tracks
    
  elif "spotify.com/playlist" in link:
    playlist_id = link.split("playlist/")[1].split("?")[0]
    playlist = sp.playlist_tracks(playlist_id)
    tracks = []
    for track in playlist["items"]:
      track_name = track["track"]["name"] + " " + track["track"]['artists'][0]['name']
      tracks.append(track_name)
    return tracks
  
  elif "&list=" in link and "youtube.com" in link or "?list=" in link and "youtube.com" in link:
    ydl_opts = {
        'extract_flat': True,  # Extract URLs without downloading
        'quiet': True,        # Suppress console output
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            playlist_info = ydl.extract_info(link, download=False)
            video_titles = [entry['title'] for entry in playlist_info['entries']]
            tracks = [track for track in video_titles]
            return tracks
        except Exception as e:
            print(f"Error: {e}")
            return None
  
  elif "youtube.com" in link:
    ydl_opts = {
        'extract_flat': True,  # Extract URLs without downloading
        'quiet': True,        # Suppress console output
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            song_info = ydl.extract_info(link, download=False)
            video_title = song_info['title']
            return video_title
        except Exception as e:
            print(f"Error: {e}")
            return None
  else:
    return link


###########################################################################
######################CLASSESS#############################################
###########################################################################

class Session():
  '''
  A class used to retrive current session data in order to keep the player
  clean and not spam multiple message for songs, queues etc...
  The bot sends one message the first time the play command is called and then
  only uses that message unless deleted, in that case it will be recreated
  
  CURRENTLY "UNUSED", MIGHT MAKE SOMETHING IN THE FUTURE
  '''
  def __init__(self, ctx, voice_client):
    
    self.ctx = ctx
    self.voice_client = voice_client

#--------------------------------------------------------------------------------------#

class Player():
  '''
   This class is the player
  '''
  def __init__(self):  
    self.currentSong = ""
    self.currentSongUrl = ""
    self.currentSongUploader = ""
    self.currentSongUploaderUrl = ""
    self.currentSongDuration = ""
    self.currentSongThumbnail = ""
    self.queue = []
    self.queueIndex = -1
    self.leftQueue = []
    self.status = 0
    self.lyrics = 0
    self.ctx = None
  
  
#--------------------------------------------------------------------------------------#
 
#--------------------------------------------------------------------------------------#    

#--------------------------------------------------------------------------------------#
yt_dlp_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'ignoreerrors': True
}
ffmpeg_options = {
	"before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin",
    "options": "-vn",
}
class YTDLSource(discord.PCMVolumeTransformer):
    '''
    I didn't make most of this function. Only the player parts. It is a function
    I found in many different stackoverflow posts for handling ytdl and FFMpeg streaming.
    '''
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        
        # Store information about the song
        self.title = data.get('title')
        self.url = data.get('webpage_url')
        self.uploader = data.get('uploader')
        self.uploader_url = data.get('channel_url')
        self.thumbnail = max(data.get('thumbnails'), key=lambda t: t.get('width', 0) * t.get('height', 0))["url"]
        self.duration = str(datetime.timedelta(seconds=int(data.get('duration'))))
        
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        
        # Download the song information and audio stream
        with yt_dlp.YoutubeDL(yt_dlp_options) as ydl:
            # Get information about the video without downloading the whole file
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=not stream))
            
            if 'entries' in data:
                # Take first item from a playlist
                data = data['entries'][0]
                
            filename = data['url'] if stream else ydl.prepare_filename(data)
            # Create the audio source for Discord
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
