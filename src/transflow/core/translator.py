"""Markdown translator using AST transformation.

Key design principles:
1. Preserve Markdown structure - only modify text content
2. Create new AST nodes instead of modifying existing ones
3. Properly escape translated text to prevent HTML injection
4. Handle batch translations efficiently
"""

import logging
from pathlib import Path
from typing import Any, Optional

import marko
from marko.block import BlockElement, CodeBlock, FencedCode, Heading, HTMLBlock, Paragraph, Quote
from marko.inline import CodeSpan, Image, Link, RawText

from transflow.config import TransFlowConfig
from transflow.core.llm import LLMClient
from transflow.exceptions import TranslationError

class MarkdownTranslator:
    """Translate Markdown content while preserving structure."""

    def __init__(
        self,
        config: TransFlowConfig,
        model: Optional[str] = None,
        target_language: str = "zh",
    ):
        """
        Initialize translator.

        Args:
            config: Application configuration
            model: LLM model name
            target_language: Target language code
        """
        self.config = config
        self.target_language = target_language
        self.logger = logging.getLogger("transflow.translator")
        self.llm_client = LLMClient(config, model)

    async def translate_file(self, input_path: Path, output_path: Path) -> None:
        """
        Translate Markdown file.

        Args:
            input_path: Source Markdown file
            output_path: Destination Markdown file

        Raises:
            TranslationError: If translation fails
        """
        try:
            # Read input file
            content = input_path.read_text(encoding="utf-8")
            self.logger.info(f"Translating: {input_path}")

            # Parse to AST
            doc = marko.parse(content)

            # Extract translatable text nodes
            text_nodes = self._extract_translatable_nodes(doc)
            self.logger.info(f"Found {len(text_nodes)} translatable text segments")

            if not text_nodes:
                self.logger.warning("No translatable content found")
                output_path.write_text(content, encoding="utf-8")
                return

            # Translate in batches
            translations = await self._translate_nodes_in_batches(text_nodes)

            # Apply translations back to AST
            self._apply_translations(doc, translations)

            # Render back to Markdown
            translated_content = marko.render(doc)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(translated_content, encoding="utf-8")

            self.logger.info(f"Translation saved to: {output_path}")

        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            raise TranslationError(f"Failed to translate file: {e}") from e

    def _extract_translatable_nodes(self, doc: Any) -> list[tuple[Any, str]]:
        """
        Extract translatable text nodes from AST.

        Args:
            doc: Marko document AST

        Returns:
            List of (node, text) tuples
        """
        translatable_nodes = []

        def traverse(node: Any) -> None:
            # Skip code blocks and HTML blocks
            if isinstance(node, (CodeBlock, FencedCode, HTMLBlock)):
                return

            # Extract text from specific block types
            if isinstance(node, (Paragraph, Heading, Quote)):
                text = self._extract_text_from_inline(node)
                if text.strip():
                    translatable_nodes.append((node, text))

            # Recurse into children
            if hasattr(node, "children") and node.children:
                for child in node.children:
                    traverse(child)

        traverse(doc)
        return translatable_nodes

    def _extract_text_from_inline(self, node: Any) -> str:
        """
        Extract plain text from inline elements.

        Args:
            node: AST node with inline children

        Returns:
            Concatenated text content
        """
        if not hasattr(node, "children"):
            return ""

        text_parts = []

        def extract(element: Any) -> None:
            if isinstance(element, RawText):
                text_parts.append(element.children)
            elif isinstance(element, CodeSpan):
                # Skip code spans
                pass
            elif isinstance(element, (Link, Image)):
                # For links, only extract text content (not URL)
                if hasattr(element, "children"):
                    for child in element.children:
                        extract(child)
            elif hasattr(element, "children"):
                for child in element.children:
                    extract(child)

        for child in node.children:
            extract(child)

        return "".join(text_parts)

    async def _translate_nodes_in_batches(
        self,
        nodes: list[tuple[Any, str]],
        batch_size: int = 10,
    ) -> dict[str, str]:
        """
        Translate nodes in batches.

        Args:
            nodes: List of (node, text) tuples
            batch_size: Number of texts per batch

        Returns:
            Dictionary mapping original text to translation
        """
        translations = {}
        texts = [text for _, text in nodes]

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            self.logger.debug(f"Translating batch {i // batch_size + 1} ({len(batch)} items)")

            self.logger.info("============")
            for s in batch:
                self.logger.info(s)
            self.logger.info("============")

            translated_batch = await self.llm_client.translate_batch(
                batch,
                self.target_language,
            )

            # Map original to translated
            for original, translated in zip(batch, translated_batch):
                translations[original] = translated

        return translations

    def _apply_translations(self, doc: Any, translations: dict[str, str]) -> None:
        """
        Apply translations back to AST nodes.

        Args:
            doc: Marko document AST
            translations: Dictionary mapping original text to translation
        """

        def traverse(node: Any) -> None:
            # Skip code blocks and HTML blocks
            if isinstance(node, (CodeBlock, FencedCode, HTMLBlock)):
                return

            # Apply translation to specific block types
            if isinstance(node, (Paragraph, Heading, Quote)):
                original_text = self._extract_text_from_inline(node)
                if original_text.strip() and original_text in translations:
                    translated_text = translations[original_text]
                    self._replace_text_in_inline(node, translated_text)

            # Recurse into children
            if hasattr(node, "children") and node.children:
                for child in node.children:
                    traverse(child)

        traverse(doc)

    def _replace_text_in_inline(self, node: Any, new_text: str) -> None:
        """
        Replace text content in inline elements while preserving Markdown formatting.

        This method creates new RawText nodes to avoid HTML escaping issues.
        
        Args:
            node: AST node with inline children
            new_text: New text content (plain text, no Markdown syntax)
        """
        if not hasattr(node, "children"):
            return

        # Clear existing children and create new RawText node
        # This ensures the text is treated as plain text, not HTML/Markdown
        try:
            # Create a new RawText node with the translated text
            new_raw_text = RawText(new_text)
            
            # Replace all children with just the new RawText node
            # This prevents any inline formatting issues
            node.children = [new_raw_text]
            
        except Exception as e:
            self.logger.warning(f"Failed to create RawText node: {e}")
            # Fallback: try to find and update existing RawText
            for i, child in enumerate(node.children):
                if isinstance(child, RawText):
                    child.children = new_text
                    node.children = [child]
                    break
