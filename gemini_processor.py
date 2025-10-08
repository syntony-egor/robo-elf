import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

class GeminiProcessor:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        logger.info(f"GeminiProcessor initialized with {GEMINI_MODEL}")
    
    async def process_video(self, video_path: str, video_metadata: dict = None, max_retries: int = 3) -> Dict[str, Any]:
        """Process video with Gemini and extract transcript and insights"""
        video_file = None
        start_time = time.time()
        last_error = None

        try:
            # Upload video to Gemini
            logger.info(f"Uploading video to Gemini: {Path(video_path).name}")
            video_file = await self._upload_to_gemini(video_path)

            # Analyze video with retry logic
            for attempt in range(max_retries):
                try:
                    logger.info(f"Analyzing video with Gemini (attempt {attempt + 1}/{max_retries})...")
                    analysis = await self._analyze_video(video_file, video_metadata)

                    # Parse result
                    result = self._parse_analysis(analysis, video_path, video_metadata)

                    processing_time = time.time() - start_time
                    logger.info(f"Processing completed in {processing_time:.1f} seconds")

                    return result

                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {error_str}")

                    # If it's a 500 error or rate limit, retry after delay
                    if "500" in error_str or "429" in error_str or "quota" in error_str.lower():
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                            logger.info(f"Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue
                    # Other errors - don't retry
                    raise

            # All retries exhausted
            raise last_error if last_error else Exception("All retries failed")

        finally:
            # Clean up Gemini file
            if video_file:
                await self._cleanup_gemini_file(video_file)
    
    async def _upload_to_gemini(self, video_path: str):
        """Upload video to Gemini Files API"""
        loop = asyncio.get_event_loop()
        
        # Upload file (synchronous operation in executor)
        video_file = await loop.run_in_executor(
            None,
            lambda: genai.upload_file(path=video_path, display_name=Path(video_path).name)
        )
        
        logger.info(f"File uploaded: {video_file.uri}")
        
        # Wait for processing
        while video_file.state.name == "PROCESSING":
            await asyncio.sleep(2)
            video_file = await loop.run_in_executor(
                None,
                lambda: genai.get_file(video_file.name)
            )
            logger.info(f"File state: {video_file.state.name}")
        
        if video_file.state.name != "ACTIVE":
            raise Exception(f"File processing failed: {video_file.state.name}")
        
        logger.info("File ready for analysis")
        return video_file
    
    async def _analyze_video(self, video_file, video_metadata: dict = None) -> str:
        """Analyze video with Gemini"""

        # Include metadata context if available
        context = ""
        if video_metadata:
            context = f"""
Метаданные видео:
- Название: {video_metadata.get('title', 'Неизвестно')}
- Длительность: {video_metadata.get('duration', 0)} секунд
- Автор: {video_metadata.get('uploader', 'Неизвестно')}
"""

        prompt = f"""{context}

Извлеки из этого Zoom-разговора все основные мысли и опиши их кратко, но полно.

КРИТИЧНО: Текст должен влезть в 2000 символов!

Формат (на русском):

📌 **[Тема 1]**
[2-3 предложения - суть обсуждения, ключевые выводы, важные детали]

📌 **[Тема 2]**
[2-3 предложения - суть обсуждения, ключевые выводы, важные детали]

📌 **[Тема 3]**
[2-3 предложения - суть обсуждения, ключевые выводы, важные детали]

...

Правила:
- Каждая тема описана ЦЕЛИКОМ - читатель должен понять её без видео
- Без воды, только факты и выводы
- Если была договорённость или решение - обязательно укажи
- Пиши простым языком
- СТРОГО не более 2000 символов в итоге"""

        loop = asyncio.get_event_loop()

        # Generate response (synchronous operation in executor)
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content([video_file, prompt])
        )

        return response.text
    
    def _parse_analysis(self, analysis: str, video_path: str, video_metadata: dict = None) -> Dict[str, Any]:
        """Parse Gemini analysis result"""
        # Clean potential markdown formatting
        cleaned = analysis.strip()
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])

        # Enforce 2000 character limit
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000].rsplit('\n', 1)[0] + "\n\n[обрезано до 2000 символов]"

        logger.info(f"Parsed analysis: {len(cleaned)} characters")

        # Return simple structure with text content
        return {
            "video_file": Path(video_path).name,
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "video_metadata": video_metadata,
            "summary": cleaned,
            "key_insights": [],
            "transcript": [],
            "topics": []
        }
    
    async def _cleanup_gemini_file(self, video_file):
        """Delete file from Gemini"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: genai.delete_file(video_file.name)
            )
            logger.info(f"Deleted file from Gemini: {video_file.name}")
        except Exception as e:
            logger.warning(f"Could not delete file from Gemini: {e}")

    async def translate_text(self, text: str, target_lang: str = "ru") -> str:
        """Translate text to target language using Gemini"""
        try:
            lang_names = {
                "ru": "Russian",
                "en": "English",
                "es": "Spanish",
                "fr": "French",
                "de": "German"
            }
            target_language = lang_names.get(target_lang, "Russian")

            prompt = f"""Translate the following text to {target_language}.
Preserve formatting, links, and structure. Return ONLY the translation without any additional commentary.

Text to translate:
{text}"""

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )

            translation = response.text.strip()
            logger.info(f"Translated text to {target_language}")
            return translation

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise

    async def translate_image(self, image_path: str, target_lang: str = "ru") -> str:
        """Extract text from image and translate to target language"""
        try:
            lang_names = {
                "ru": "Russian",
                "en": "English",
                "es": "Spanish",
                "fr": "French",
                "de": "German"
            }
            target_language = lang_names.get(target_lang, "Russian")

            # Upload image to Gemini
            loop = asyncio.get_event_loop()
            image_file = await loop.run_in_executor(
                None,
                lambda: genai.upload_file(path=image_path, display_name=Path(image_path).name)
            )

            try:
                # Wait for processing
                while image_file.state.name == "PROCESSING":
                    await asyncio.sleep(1)
                    image_file = await loop.run_in_executor(
                        None,
                        lambda: genai.get_file(image_file.name)
                    )

                if image_file.state.name != "ACTIVE":
                    raise Exception(f"Image processing failed: {image_file.state.name}")

                # Extract and translate text
                prompt = f"""Analyze this image and:
1. Extract all visible text from the image (OCR)
2. Translate the extracted text to {target_language}
3. Preserve the structure and formatting

Return ONLY the translated text without any additional commentary or explanations.
If there is no text in the image, respond with "[No text found in image]"."""

                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content([image_file, prompt])
                )

                translation = response.text.strip()
                logger.info(f"Extracted and translated text from image to {target_language}")

                return translation

            finally:
                # Clean up uploaded image
                await self._cleanup_gemini_file(image_file)

        except Exception as e:
            logger.error(f"Image translation failed: {e}")
            raise

# For testing
async def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python gemini_processor.py <video_file>")
        return
    
    processor = GeminiProcessor()
    result = await processor.process_video(sys.argv[1])
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())