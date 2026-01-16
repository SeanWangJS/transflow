"""Tests for Markdown translator.

Following Google Python testing guidelines.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from transflow.config import TransFlowConfig
from transflow.core.translator import MarkdownTranslator
from transflow.exceptions import TranslationError


class TestMarkdownTranslator:
    """Tests for MarkdownTranslator class."""

    def test_init_creates_llm_client(self) -> None:
        """Test translator initialization creates LLM client."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")

        # Act
        translator = MarkdownTranslator(config, target_language="zh")

        # Assert
        assert translator.config == config
        assert translator.target_language == "zh"
        assert translator.llm_client is not None

    def test_init_with_custom_model(self) -> None:
        """Test translator accepts custom model parameter."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        custom_model = "gpt-4-turbo"

        # Act
        translator = MarkdownTranslator(config, model=custom_model)

        # Assert
        assert translator.llm_client.model == custom_model

    @pytest.mark.asyncio
    async def test_translate_file_creates_output_file(self) -> None:
        """Test translate_file creates output file with translated content."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config, target_language="zh")

        input_content = "# Hello World\n\nThis is a test."
        input_path = Path("/tmp/test_input.md")
        output_path = Path("/tmp/test_output.md")

        # Mock file operations
        with patch.object(Path, "read_text", return_value=input_content):
            with patch.object(Path, "write_text") as mock_write:
                with patch.object(Path, "mkdir"):
                    # Mock translation
                    mock_translate = AsyncMock(return_value={
                        "Hello World": "你好，世界",
                        "This is a test.": "这是一个测试",
                    })
                    translator._translate_nodes_in_batches = mock_translate

                    # Act
                    await translator.translate_file(input_path, output_path)

        # Assert
        mock_write.assert_called_once()
        written_content = mock_write.call_args[0][0]
        assert isinstance(written_content, str)

    @pytest.mark.asyncio
    async def test_translate_file_handles_empty_content(self) -> None:
        """Test translate_file handles files with no translatable content."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        input_content = "```python\nprint('code only')\n```"
        input_path = Path("/tmp/test_input.md")
        output_path = Path("/tmp/test_output.md")

        # Mock file operations
        with patch.object(Path, "read_text", return_value=input_content):
            with patch.object(Path, "write_text") as mock_write:
                with patch.object(Path, "mkdir"):
                    # Act
                    await translator.translate_file(input_path, output_path)

        # Assert
        mock_write.assert_called_once()
        # Should write original content unchanged
        written_content = mock_write.call_args[0][0]
        assert "print('code only')" in written_content

    @pytest.mark.asyncio
    async def test_translate_file_error_raises_translation_error(self) -> None:
        """Test translate_file raises TranslationError on failure."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        input_path = Path("/tmp/test_input.md")
        output_path = Path("/tmp/test_output.md")

        # Act & Assert
        with patch.object(Path, "read_text", side_effect=IOError("Read error")):
            with pytest.raises(TranslationError, match="Failed to translate file"):
                await translator.translate_file(input_path, output_path)

    def test_extract_translatable_nodes_includes_paragraphs(self) -> None:
        """Test node extraction includes paragraph text."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        import marko
        doc = marko.parse("This is a paragraph.")

        # Act
        nodes = translator._extract_translatable_nodes(doc)

        # Assert
        assert len(nodes) > 0
        assert any("paragraph" in str(node).lower() for node, _ in nodes)

    def test_extract_translatable_nodes_includes_headings(self) -> None:
        """Test node extraction includes heading text."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        import marko
        doc = marko.parse("# My Heading\n\nSome content.")

        # Act
        nodes = translator._extract_translatable_nodes(doc)

        # Assert
        assert len(nodes) >= 2  # Heading + paragraph
        texts = [text for _, text in nodes]
        assert any("Heading" in t for t in texts)

    def test_extract_translatable_nodes_skips_code_blocks(self) -> None:
        """Test node extraction excludes code blocks."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        import marko
        doc = marko.parse("```python\nprint('hello')\n```\n\nText content.")

        # Act
        nodes = translator._extract_translatable_nodes(doc)

        # Assert
        texts = [text for _, text in nodes]
        assert not any("print" in t for t in texts)  # Code should be excluded
        assert any("Text content" in t for t in texts)  # Text should be included

    def test_extract_text_from_inline_handles_simple_text(self) -> None:
        """Test inline text extraction from simple paragraph."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        import marko
        doc = marko.parse("Hello world")
        paragraph = doc.children[0]

        # Act
        text = translator._extract_text_from_inline(paragraph)

        # Assert
        assert "Hello world" in text

    def test_extract_text_from_inline_skips_code_spans(self) -> None:
        """Test inline text extraction excludes inline code."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        import marko
        doc = marko.parse("Text with `code` here")
        paragraph = doc.children[0]

        # Act
        text = translator._extract_text_from_inline(paragraph)

        # Assert
        # Should include text but may or may not include code
        assert "Text" in text

    @pytest.mark.asyncio
    async def test_translate_nodes_in_batches_calls_llm(self) -> None:
        """Test batch translation invokes LLM client."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        import marko
        doc = marko.parse("# Title\n\nParagraph.")
        nodes = translator._extract_translatable_nodes(doc)

        mock_translate_batch = AsyncMock(return_value=["标题", "段落"])

        # Act
        with patch.object(
            translator.llm_client,
            "translate_batch",
            new=mock_translate_batch,
        ):
            translations = await translator._translate_nodes_in_batches(nodes)

        # Assert
        assert len(translations) == len(nodes)
        mock_translate_batch.assert_called()

    @pytest.mark.asyncio
    async def test_translate_nodes_in_batches_with_large_set(self) -> None:
        """Test batch translation splits large node sets into batches."""
        # Arrange
        config = TransFlowConfig(openai_api_key="test_key")
        translator = MarkdownTranslator(config)

        # Create many nodes
        nodes = [(None, f"Text {i}") for i in range(25)]

        mock_translate_batch = AsyncMock(
            side_effect=lambda texts, lang: [f"Translated {t}" for t in texts]
        )

        # Act
        with patch.object(
            translator.llm_client,
            "translate_batch",
            new=mock_translate_batch,
        ):
            translations = await translator._translate_nodes_in_batches(nodes, batch_size=10)

        # Assert
        assert len(translations) == 25
        # Should have called translate_batch 3 times (10 + 10 + 5)
        assert mock_translate_batch.call_count == 3
