import discord
import re


def embedCreator(body, *args):
  embed = discord.Embed(
        color=discord.Colour.from_rgb(body[0][0],body[0][1],body[0][2]),
        title=body[1],
        description=body[2]
  )
  for arg in args:
    match arg[0]:
      case "footer":
        embed.set_footer(text=arg[1], icon_url=arg[2])
      case "author":
        embed.set_author(name=arg[1], icon_url=arg[2], url=arg[3])
      case "thumbnail":
        embed.set_thumbnail(url=arg[1])
      case "image":
        embed.set_image(url=arg[1])
      case "field":
        embed.add_field(name=arg[1], value=arg[2], inline=arg[3])
  return embed
  
def beautifyLyrics(lyrics):
    if type(lyrics) == tuple:
        lyrics = lyrics[0]
    beautyLyrics = ""
        #lyrics = re.sub("[\\[].*?[\\]]", "", lyrics)
    for line in lyrics.split("\n"):
        timestamp = line.replace("] ", "]").replace(']','[(]').split('[')[1::2]
        backupSing = line.replace(')','([)').split('(')[1::2]
        backupSing = ' '.join(backupSing)
        line = re.sub("[\(\[].*?[\)\]]", "", line)
        if len(line) > 1:
            line = "\n" + line
            if len(backupSing) > 1:
                line += "\n-# " + backupSing
        else:
            line = u"\n\u2669"
        beautyLyrics += line
    
    return beautyLyrics
      
