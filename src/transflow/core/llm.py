"""LLM client for translation using OpenAI API."""

import logging
from typing import Any, Optional

from transflow.config import TransFlowConfig
from transflow.exceptions import APIError, TranslationError
from transflow.utils.http import HTTPClient


class LLMClient:
    """Client for interacting with Large Language Models."""

    def __init__(self, config: TransFlowConfig, model: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            config: Application configuration
            model: Model name (uses config default if not provided)

        Raises:
            ValidationError: If API key is missing
        """
        self.config = config
        self.model = model or config.default_model
        self.logger = logging.getLogger("transflow.llm")

        if not config.openai_api_key:
            raise APIError("OpenAI API key is required (TRANSFLOW_OPENAI_API_KEY)")

        self.http_client = HTTPClient(
            timeout=config.http_timeout,
            max_retries=config.http_max_retries,
            headers={
                "Authorization": f"Bearer {config.openai_api_key}",
                "Content-Type": "application/json",
            },
        )

    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> str:
        """
        Translate text to target language.

        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'zh', 'en')
            source_language: Source language (default: auto-detect)

        Returns:
            Translated text

        Raises:
            TranslationError: If translation fails
        """
        if not text.strip():
            return text

        prompt = self._build_translation_prompt(text, target_language, source_language)

        try:
            response = await self.http_client.post(
                f"{self.config.openai_base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional translator. Translate the given text accurately while preserving formatting and tone.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
            )

            data = response.json()
            translated = data["choices"][0]["message"]["content"].strip()

            self.logger.debug(f"Translated: {text[:50]}... -> {translated[:50]}...")

            return translated

        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            raise TranslationError(f"Failed to translate text: {e}") from e

    async def translate_batch(
        self,
        texts: list[str],
        target_language: str,
        source_language: str = "auto",
    ) -> list[str]:
        """
        Translate multiple texts in batch.

        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language

        Returns:
            List of translated texts (same order as input)

        Raises:
            TranslationError: If batch translation fails
        """
        if not texts:
            return []

        # Filter out empty texts but preserve indices
        non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
        non_empty_texts = [texts[i] for i in non_empty_indices]

        if not non_empty_texts:
            return texts

        # Combine texts with markers for splitting later
        combined_text = "\n\n---SPLIT---\n\n".join(non_empty_texts)
        prompt = self._build_translation_prompt(combined_text, target_language, source_language)

        try:
            response = await self.http_client.post(
                f"{self.config.openai_base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional translator. Translate the given text accurately while preserving the ---SPLIT--- markers exactly as they appear.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
            )

            data = response.json()
            translated_combined = data["choices"][0]["message"]["content"].strip()

            # Split back into individual translations
            translated_texts = translated_combined.split("\n\n---SPLIT---\n\n")

            # Handle case where split count doesn't match
            if len(translated_texts) != len(non_empty_texts):
                self.logger.warning(
                    f"Translation split mismatch: expected {len(non_empty_texts)}, got {len(translated_texts)}"
                )
                # Fall back to individual translation
                return await self._translate_individually(texts, target_language, source_language)

            # Reconstruct full list with empty texts preserved
            results = texts[:]
            for idx, translated in zip(non_empty_indices, translated_texts):
                results[idx] = translated.strip()

            self.logger.info(f"Batch translated {len(non_empty_texts)} texts")

            return results

        except Exception as e:
            self.logger.error(f"Batch translation failed: {e}")
            # Fall back to individual translation
            return await self._translate_individually(texts, target_language, source_language)

    async def _translate_individually(
        self,
        texts: list[str],
        target_language: str,
        source_language: str,
    ) -> list[str]:
        """
        Translate texts one by one (fallback method).

        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language

        Returns:
            List of translated texts
        """
        results = []
        for text in texts:
            if text.strip():
                translated = await self.translate_text(text, target_language, source_language)
                results.append(translated)
            else:
                results.append(text)
        return results

    def _build_translation_prompt(
        self,
        text: str,
        target_language: str,
        source_language: str,
    ) -> str:
        """
        Build translation prompt.

        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language

        Returns:
            Translation prompt
        """
        language_names = {
            "zh": "Chinese",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
        }

        target_lang_name = language_names.get(target_language, target_language)

        if source_language == "auto":
            return f"Translate the following text to {target_lang_name}:\n\n{text}"
        else:
            source_lang_name = language_names.get(source_language, source_language)
            return f"Translate the following text from {source_lang_name} to {target_lang_name}:\n\n{text}"

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters for English, ≈ 1.5 for Chinese
        # Use conservative estimate
        return len(text) // 3
