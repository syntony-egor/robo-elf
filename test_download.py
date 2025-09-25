#!/usr/bin/env python3
"""
Test script to verify YouTube downloading works
"""

import asyncio
import sys
from youtube_downloader import YouTubeDownloader

async def test_download(url=None):
    """Test downloading a YouTube video"""
    
    # Default test URL (short video)
    if not url:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
        print(f"No URL provided, using default test video: {url}")
    
    downloader = YouTubeDownloader()
    
    try:
        print(f"\n🎬 Starting download test...")
        print(f"URL: {url}")
        print("-" * 50)
        
        # Try to download
        file_path, metadata = await downloader.download_video(url)
        
        print("\n✅ Download successful!")
        print(f"File saved to: {file_path}")
        print(f"\nVideo metadata:")
        print(f"  Title: {metadata.get('title', 'Unknown')}")
        print(f"  Duration: {metadata.get('duration', 0)} seconds")
        print(f"  Uploader: {metadata.get('uploader', 'Unknown')}")
        print(f"  Views: {metadata.get('view_count', 0):,}")
        
        # Clean up
        print(f"\nCleaning up downloaded file...")
        downloader.cleanup_file(file_path)
        print("✅ Cleanup complete!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Download failed!")
        print(f"Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if the URL is valid and accessible")
        print("2. Try updating yt-dlp: python3 -m pip install --upgrade yt-dlp")
        print("3. Check your internet connection")
        print("4. The video might be age-restricted or private")
        return False

async def main():
    """Main test function"""
    # Get URL from command line or use default
    url = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = await test_download(url)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    print("YouTube Downloader Test Script")
    print("=" * 50)
    asyncio.run(main())