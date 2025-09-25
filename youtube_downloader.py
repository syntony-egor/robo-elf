import os
import re
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import yt_dlp

logger = logging.getLogger(__name__)

class YouTubeDownloader:
    def __init__(self):
        self.tmp_dir = Path("tmp")
        self.tmp_dir.mkdir(exist_ok=True)
        
    def extract_youtube_urls(self, text: str) -> list[str]:
        """Extract YouTube URLs from text"""
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&[\w=]+)*',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+(?:\?[\w=]+)?',
            r'(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+',
            r'(?:https?://)?(?:www\.)?m\.youtube\.com/watch\?v=[\w-]+(?:&[\w=]+)*'
        ]
        
        urls = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            urls.extend(matches)
        
        # Ensure URLs have protocol
        normalized_urls = []
        for url in urls:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            normalized_urls.append(url)
        
        return list(set(normalized_urls))  # Remove duplicates
    
    async def download_video(self, url: str) -> tuple[str, dict]:
        """Download YouTube video and return file path and metadata"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Configure yt-dlp options with better bot protection bypass
        ydl_opts = {
            'outtmpl': str(self.tmp_dir / f'{timestamp}_%(title)s.%(ext)s'),
            'format': 'best[ext=mp4]/best',  # Prefer mp4 format
            'quiet': True,  # Suppress output in production
            'no_warnings': True,  # Suppress warnings
            'extract_flat': False,
            # Use different extractors to bypass bot protection
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android', 'web'],  # Try iOS first, then Android, then web
                    'skip': ['hls', 'dash'],  # Skip problematic formats
                }
            },
            # Headers to appear more like a real browser
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            },
            # Additional options
            'age_limit': None,  # Don't filter by age
            'geo_bypass': True,  # Bypass geographic restrictions
            'nocheckcertificate': True,
            'prefer_free_formats': True,
            'no_check_formats': False,
        }
        
        loop = asyncio.get_event_loop()
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Extract info first
                    info = ydl.extract_info(url, download=False)
                    
                    # Log video details
                    logger.info(f"Downloading: {info.get('title', 'Unknown')}")
                    logger.info(f"Duration: {info.get('duration', 0)} seconds")
                    logger.info(f"Uploader: {info.get('uploader', 'Unknown')}")
                    
                    # Now download
                    ydl.download([url])
                    
                    # Get the actual filename
                    filename = ydl.prepare_filename(info)
                    # Handle different extensions
                    if not os.path.exists(filename):
                        # Try with mp4 extension
                        base = os.path.splitext(filename)[0]
                        for ext in ['.mp4', '.webm', '.mkv', '.mov']:
                            test_path = base + ext
                            if os.path.exists(test_path):
                                filename = test_path
                                break
                    
                    metadata = {
                        'title': info.get('title', 'Unknown'),
                        'duration': info.get('duration', 0),
                        'uploader': info.get('uploader', 'Unknown'),
                        'upload_date': info.get('upload_date', ''),
                        'description': info.get('description', ''),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'url': url
                    }
                    
                    return filename, metadata
                    
                except Exception as e:
                    logger.error(f"Download failed: {str(e)}")
                    raise
        
        # Run download in executor
        file_path, metadata = await loop.run_in_executor(None, download)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Downloaded file not found: {file_path}")
        
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        logger.info(f"Download complete: {file_path} ({file_size:.1f} MB)")
        
        return file_path, metadata
    
    def cleanup_file(self, file_path: str):
        """Delete a downloaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")

# For testing
async def main():
    downloader = YouTubeDownloader()
    
    # Test URL extraction
    test_text = "Check out this video: https://www.youtube.com/watch?v=dQw4w9WgXcQ and this one youtu.be/abc123"
    urls = downloader.extract_youtube_urls(test_text)
    print(f"Found URLs: {urls}")
    
    if urls:
        # Test download
        file_path, metadata = await downloader.download_video(urls[0])
        print(f"Downloaded to: {file_path}")
        print(f"Metadata: {metadata}")
        
        # Cleanup
        downloader.cleanup_file(file_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())