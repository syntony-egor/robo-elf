import discord
from discord.ext import commands
import asyncio
import logging
import traceback
import os
import tempfile
from datetime import datetime
from pathlib import Path
from config import DISCORD_TOKEN
from youtube_downloader import YouTubeDownloader
from gemini_processor import GeminiProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('robo-elf')

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.guilds = True

# Create bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize processors
youtube_downloader = YouTubeDownloader()
gemini_processor = GeminiProcessor()

# Track processed messages to avoid duplicates
processed_reactions = set()

@bot.event
async def on_ready():
    logger.info(f'Bot connected as {bot.user.name} ({bot.user.id})')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for 🪄 reactions on YouTube links"
        )
    )

@bot.event
async def on_raw_reaction_add(payload):
    """Handle reaction events"""
    # Skip if bot's own reaction
    if payload.user_id == bot.user.id:
        return

    emoji_str = str(payload.emoji)

    # Check if it's the magic wand emoji
    if emoji_str == '🪄':
        # Create unique key for this reaction
        reaction_key = f"{payload.message_id}_{payload.user_id}_{payload.emoji}"
        if reaction_key in processed_reactions:
            return
        processed_reactions.add(reaction_key)

        try:
            # Get the channel and message
            channel = bot.get_channel(payload.channel_id)
            if not channel:
                return

            message = await channel.fetch_message(payload.message_id)

            # Extract YouTube URLs from the message
            urls = youtube_downloader.extract_youtube_urls(message.content)

            if not urls:
                logger.info(f"No YouTube URLs found in message {message.id}")
                return

            logger.info(f"Processing {len(urls)} YouTube URL(s) from message {message.id}")

            # Process each URL
            for url in urls:
                asyncio.create_task(process_youtube_video(message, url))

        except Exception as e:
            logger.error(f"Error handling reaction: {e}")
            logger.error(traceback.format_exc())

    # Check if it's the Russian flag emoji for translation
    elif emoji_str == '🇷🇺':
        # Create unique key for this reaction
        reaction_key = f"{payload.message_id}_{payload.user_id}_{payload.emoji}"
        if reaction_key in processed_reactions:
            return
        processed_reactions.add(reaction_key)

        try:
            # Get the channel and message
            channel = bot.get_channel(payload.channel_id)
            if not channel:
                return

            message = await channel.fetch_message(payload.message_id)

            logger.info(f"Processing translation request for message {message.id}")

            # Process translation
            asyncio.create_task(process_translation(message, target_lang="ru"))

        except Exception as e:
            logger.error(f"Error handling translation reaction: {e}")
            logger.error(traceback.format_exc())

async def process_youtube_video(message: discord.Message, url: str):
    """Process a YouTube video: download, analyze, and respond"""
    thread = None
    status_message = None
    video_path = None
    
    try:
        # Get or create thread for the message
        thread = None
        
        # First check if the message already has a thread
        if hasattr(message, 'thread') and message.thread:
            thread = message.thread
            logger.info(f"Using existing thread for message {message.id}")
        else:
            # Try to create a thread
            try:
                thread_name = f"Video Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                thread = await message.create_thread(name=thread_name[:100])
                logger.info(f"Created new thread for message {message.id}")
            except discord.HTTPException as e:
                if e.code == 160004:  # Thread already exists
                    # The thread exists but we need to find it
                    # Check all active threads in the guild
                    for t in message.guild.threads:
                        # Check if this thread starts from our message
                        if t.parent_id == message.channel.id:
                            try:
                                starter_message = await t.parent.fetch_message(t.id)
                                if starter_message.id == message.id:
                                    thread = t
                                    logger.info(f"Found existing thread {t.id} for message {message.id}")
                                    break
                            except:
                                # Not the right thread, continue
                                pass
                    
                    # If we still can't find it, check archived threads
                    if not thread:
                        async for t in message.channel.archived_threads(limit=100):
                            if t.id == message.id:
                                thread = t
                                logger.info(f"Found archived thread {t.id} for message {message.id}")
                                break
                    
                    # Last resort - just use the channel
                    if not thread:
                        logger.warning(f"Could not find thread for message {message.id}, using channel")
                        thread = message.channel
                else:
                    raise
        
        # Send initial status
        embed = discord.Embed(
            title="🎬 Processing YouTube Video",
            description=f"Starting analysis of: {url}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Status", value="⏳ Downloading video...", inline=False)
        status_message = await thread.send(embed=embed)
        
        # Download video
        logger.info(f"Downloading video: {url}")
        video_path, metadata = await youtube_downloader.download_video(url)
        
        # Update status
        embed.set_field_at(
            0, 
            name="Status", 
            value=f"✅ Downloaded\n⏳ Analyzing with Gemini...\n📊 Duration: {metadata.get('duration', 0)}s",
            inline=False
        )
        embed.add_field(
            name="Video Info",
            value=f"**Title:** {metadata.get('title', 'Unknown')[:100]}\n"
                  f"**Channel:** {metadata.get('uploader', 'Unknown')}",
            inline=False
        )
        await status_message.edit(embed=embed)
        
        # Process with Gemini
        logger.info(f"Processing with Gemini: {video_path}")
        analysis = await gemini_processor.process_video(video_path, metadata)
        
        # Update status to completed
        embed.color = discord.Color.green()
        embed.set_field_at(
            0,
            name="Status",
            value="✅ Analysis Complete!",
            inline=False
        )
        await status_message.edit(embed=embed)
        
        # Send summary
        summary_embed = discord.Embed(
            title="📝 Video Summary",
            description=analysis.get('summary', 'No summary available'),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        # Add topics if available
        if analysis.get('topics'):
            topics_text = ", ".join(f"`{topic}`" for topic in analysis['topics'][:10])
            summary_embed.add_field(name="Topics", value=topics_text, inline=False)
        
        await thread.send(embed=summary_embed)
        
        # Send key insights
        if analysis.get('key_insights'):
            insights_text = "\n".join([
                f"{i+1}. {insight}" 
                for i, insight in enumerate(analysis['key_insights'][:10])
            ])
            
            # Split if too long
            if len(insights_text) > 1024:
                insights_chunks = split_text(insights_text, 1024)
                for i, chunk in enumerate(insights_chunks[:2]):  # Max 2 fields
                    insights_embed = discord.Embed(
                        title=f"💡 Key Insights" if i == 0 else "💡 Key Insights (continued)",
                        description=chunk,
                        color=discord.Color.blue()
                    )
                    await thread.send(embed=insights_embed)
            else:
                insights_embed = discord.Embed(
                    title="💡 Key Insights",
                    description=insights_text,
                    color=discord.Color.blue()
                )
                await thread.send(embed=insights_embed)
        
        # Send transcript
        if analysis.get('transcript'):
            await thread.send("## 📜 Full Transcript")
            
            # Format transcript
            transcript_text = ""
            for segment in analysis['transcript']:
                timestamp = segment.get('timestamp', '')
                text = segment.get('text', '')
                if timestamp:
                    transcript_text += f"**[{timestamp}]** {text}\n\n"
                else:
                    transcript_text += f"{text}\n\n"
            
            # Split transcript into Discord-sized chunks
            if transcript_text:
                chunks = split_text(transcript_text, 1900)
                for i, chunk in enumerate(chunks):
                    # Add page numbers if multiple chunks
                    if len(chunks) > 1:
                        chunk = f"**Part {i+1}/{len(chunks)}**\n\n{chunk}"
                    await thread.send(chunk)
        
        # Add completion reaction
        await message.add_reaction('✅')
        
        logger.info(f"Successfully processed video: {url}")
        
    except Exception as e:
        logger.error(f"Error processing video {url}: {e}")
        logger.error(traceback.format_exc())
        
        # Send error message
        error_embed = discord.Embed(
            title="❌ Processing Failed",
            description=f"Failed to process the video:\n```{str(e)[:500]}```",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        if thread:
            await thread.send(embed=error_embed)
        else:
            # If thread creation failed, try to react to original message
            try:
                await message.add_reaction('❌')
            except:
                pass
    
    finally:
        # Clean up downloaded file
        if video_path:
            youtube_downloader.cleanup_file(video_path)

async def process_translation(message: discord.Message, target_lang: str = "ru"):
    """Process translation request for text and/or images"""
    thread = None
    status_message = None
    temp_files = []

    try:
        # Get or create thread for the message
        if hasattr(message, 'thread') and message.thread:
            thread = message.thread
            logger.info(f"Using existing thread for message {message.id}")
        else:
            # Try to create a thread
            try:
                thread_name = f"Translation - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                thread = await message.create_thread(name=thread_name[:100])
                logger.info(f"Created new thread for message {message.id}")
            except discord.HTTPException as e:
                if e.code == 160004:  # Thread already exists
                    # Try to find existing thread
                    for t in message.guild.threads:
                        if t.parent_id == message.channel.id:
                            try:
                                starter_message = await t.parent.fetch_message(t.id)
                                if starter_message.id == message.id:
                                    thread = t
                                    logger.info(f"Found existing thread {t.id} for message {message.id}")
                                    break
                            except:
                                pass

                    if not thread:
                        async for t in message.channel.archived_threads(limit=100):
                            if t.id == message.id:
                                thread = t
                                logger.info(f"Found archived thread {t.id} for message {message.id}")
                                break

                    if not thread:
                        logger.warning(f"Could not find thread for message {message.id}, using channel")
                        thread = message.channel
                else:
                    raise

        # Send initial status
        embed = discord.Embed(
            title="🌐 Translation in Progress",
            description="Processing your translation request...",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        status_message = await thread.send(embed=embed)

        translations = []

        # Translate text content if present
        if message.content and message.content.strip():
            logger.info(f"Translating text content from message {message.id}")
            try:
                translated_text = await gemini_processor.translate_text(message.content, target_lang)
                translations.append({
                    "type": "text",
                    "content": translated_text
                })
            except Exception as e:
                logger.error(f"Text translation failed: {e}")
                translations.append({
                    "type": "text",
                    "error": str(e)
                })

        # Translate images if present
        if message.attachments:
            for attachment in message.attachments:
                # Check if it's an image
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    logger.info(f"Processing image attachment: {attachment.filename}")
                    try:
                        # Download image to temp file
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=Path(attachment.filename).suffix)
                        temp_files.append(temp_file.name)

                        await attachment.save(temp_file.name)
                        logger.info(f"Downloaded image to {temp_file.name}")

                        # Translate image
                        translated_text = await gemini_processor.translate_image(temp_file.name, target_lang)
                        translations.append({
                            "type": "image",
                            "filename": attachment.filename,
                            "content": translated_text
                        })
                    except Exception as e:
                        logger.error(f"Image translation failed for {attachment.filename}: {e}")
                        translations.append({
                            "type": "image",
                            "filename": attachment.filename,
                            "error": str(e)
                        })

        # Update status to completed
        if translations:
            embed.color = discord.Color.green()
            embed.title = "✅ Translation Complete"
            embed.description = "Translation has been completed successfully!"
            await status_message.edit(embed=embed)

            # Send translations
            for idx, trans in enumerate(translations):
                if "error" in trans:
                    error_msg = f"❌ **Translation Failed**\nType: {trans['type']}\nError: {trans['error']}"
                    if trans['type'] == 'image':
                        error_msg += f"\nFile: {trans.get('filename', 'Unknown')}"
                    await thread.send(error_msg)
                else:
                    if trans['type'] == 'text':
                        await thread.send(trans['content'][:2000])
                    elif trans['type'] == 'image':
                        header = f"🖼️ **{trans['filename']}**\n\n"
                        content = trans['content'][:2000 - len(header)]
                        await thread.send(header + content)

            # Add completion reaction
            await message.add_reaction('✅')
        else:
            embed.color = discord.Color.orange()
            embed.title = "⚠️ Nothing to Translate"
            embed.description = "No text or images found in the message."
            await status_message.edit(embed=embed)

        logger.info(f"Successfully processed translation for message {message.id}")

    except Exception as e:
        logger.error(f"Error processing translation: {e}")
        logger.error(traceback.format_exc())

        # Send error message
        error_embed = discord.Embed(
            title="❌ Translation Failed",
            description=f"An error occurred:\n```{str(e)[:500]}```",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )

        if thread:
            await thread.send(embed=error_embed)
        else:
            try:
                await message.add_reaction('❌')
            except:
                pass

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
                logger.info(f"Deleted temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_file}: {e}")

def split_text(text: str, max_length: int) -> list[str]:
    """Split text into chunks that fit Discord's message limits"""
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by paragraphs first
    paragraphs = text.split('\n\n')

    for para in paragraphs:
        # If single paragraph is too long, split by sentences
        if len(para) > max_length:
            sentences = para.split('. ')
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence + '. '
                else:
                    current_chunk += sentence + '. '
        else:
            # Check if adding paragraph exceeds limit
            if len(current_chunk) + len(para) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + '\n\n'
            else:
                current_chunk += para + '\n\n'

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

@bot.command(name='ping')
async def ping(ctx):
    """Simple ping command to check if bot is responsive"""
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Pong! Latency: {latency}ms')

@bot.command(name='status')
async def status(ctx):
    """Show bot status"""
    embed = discord.Embed(
        title="🤖 Robo-Elf Status",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(
        name="Instructions",
        value="React with 🪄 to any message containing a YouTube link to get a transcript and analysis!",
        inline=False
    )
    await ctx.send(embed=embed)

def main():
    """Run the bot"""
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()