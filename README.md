# Robo-Elf Discord Bot 🤖🧝

A helpful Discord bot that monitors for magic wand (🪄) reactions on messages containing YouTube links, then downloads the video, transcribes it using Google's Gemini AI, and posts a comprehensive analysis in a thread.

## Features

- **Automatic YouTube Detection**: Monitors messages for YouTube links
- **Magic Wand Activation**: React with 🪄 to trigger video processing
- **AI-Powered Analysis**: Uses Gemini 2.5 Pro for transcription and insights
- **Threaded Responses**: Creates organized threads with:
  - Video summary
  - Key insights and takeaways  
  - Full transcript with timestamps
  - Topic extraction

## Setup

### Prerequisites

- Python 3.8+
- Discord Bot Token
- Google Gemini API Key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd robo-elf
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
   - Copy `.env.example` to `.env` (or create `.env` directly)
   - Add your Discord bot token and Gemini API key

4. Run the bot:
```bash
python3 bot.py
```

## Usage

1. **Invite the bot** to your Discord server with necessary permissions:
   - Send Messages
   - Read Message History
   - Add Reactions
   - Create Public Threads
   - Send Messages in Threads

2. **Share a YouTube link** in any channel where the bot has access

3. **React with 🪄** (magic wand emoji) to the message

4. **Watch the magic happen** - the bot will:
   - Create a thread on your message
   - Download and process the video
   - Post the transcript and analysis

## Commands

- `!ping` - Check if the bot is responsive
- `!status` - Show bot status and instructions

## File Structure

```
robo-elf/
├── bot.py                 # Main Discord bot logic
├── youtube_downloader.py  # YouTube video downloader
├── gemini_processor.py    # Gemini AI integration
├── config.py             # Configuration loader
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── tmp/                  # Temporary video storage (auto-created)
└── README.md            # This file
```

## How It Works

1. **Reaction Detection**: The bot monitors for 🪄 reactions on messages
2. **URL Extraction**: Extracts YouTube URLs from the reacted message
3. **Video Download**: Downloads the video using yt-dlp to tmp/
4. **Gemini Processing**: 
   - Uploads video to Gemini Files API
   - Requests transcription and analysis
   - Extracts insights and key points
5. **Discord Response**: Creates a thread with formatted results
6. **Cleanup**: Automatically deletes temporary files

## Configuration

The bot uses environment variables for configuration:

- `DISCORD_TOKEN`: Your Discord bot token
- `GEMINI_API_KEY`: Your Google Gemini API key  
- `GEMINI_MODEL`: AI model to use (default: gemini-2.5-pro)

## Troubleshooting

- **Bot not responding**: Check bot token and permissions
- **Video download fails**: Ensure yt-dlp is up to date
- **Gemini errors**: Verify API key and quota limits
- **No thread created**: Check bot has thread creation permissions

## Security Notes

- Never commit `.env` file to version control
- Keep API keys secure and rotate them regularly
- The bot automatically cleans up downloaded videos after processing

## License

CC0 1.0 Universal - see LICENSE file for details