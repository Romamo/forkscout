"""Test that emoji and Unicode characters have been removed from output formatting."""


from forkscout.analysis.explanation_formatter import ExplanationFormatter
from forkscout.models.analysis import (
    CategoryType,
    ImpactLevel,
    MainRepoValue,
)


class TestEmojiRemoval:
    """Test that emoji and Unicode characters are not used in output formatting."""

    def test_explanation_formatter_category_icons_are_text(self):
        """Test that category icons are text labels, not emojis."""
        formatter = ExplanationFormatter(use_colors=False, use_icons=True)

        # Test all category types
        for category_type in CategoryType:
            icon = formatter.CATEGORY_ICONS.get(category_type, "[OTHER]")

            # Verify it's a text label in brackets
            assert icon.startswith("[") and icon.endswith("]"), f"Category icon for {category_type} is not a text label: {icon}"

            # Verify no emojis
            emoji_chars = ["📝", "❓", "🟢", "❔", "🚀", "🐛", "♻️", "🧪", "🔧", "⚡", "🔒"]
            for emoji in emoji_chars:
                assert emoji not in icon, f"Found emoji {emoji} in category icon {icon}"

    def test_explanation_formatter_impact_indicators_are_text(self):
        """Test that impact indicators are text labels, not emojis."""
        formatter = ExplanationFormatter(use_colors=False, use_icons=True)

        # Test all impact levels
        for impact_level in ImpactLevel:
            indicator = formatter.IMPACT_INDICATORS.get(impact_level, "[UNCLEAR]")

            # Verify it's a text label in brackets
            assert indicator.startswith("[") and indicator.endswith("]"), f"Impact indicator for {impact_level} is not a text label: {indicator}"

            # Verify no emojis
            emoji_chars = ["🟡", "🟠", "🔴", "✅", "❌", "⚠️"]
            for emoji in emoji_chars:
                assert emoji not in indicator, f"Found emoji {emoji} in impact indicator {indicator}"

    def test_explanation_formatter_value_indicators_are_text(self):
        """Test that value indicators are text labels, not emojis."""
        formatter = ExplanationFormatter(use_colors=False, use_icons=True)

        # Test all main repo values
        for value in MainRepoValue:
            indicator = formatter.VALUE_INDICATORS.get(value, "[UNCLEAR]")

            # Verify it's a text label in brackets
            assert indicator.startswith("[") and indicator.endswith("]"), f"Value indicator for {value} is not a text label: {indicator}"

            # Verify no emojis
            emoji_chars = ["✅", "❌", "❓"]
            for emoji in emoji_chars:
                assert emoji not in indicator, f"Found emoji {emoji} in value indicator {indicator}"

    def test_simple_table_formatter_uses_ascii_characters(self):
        """Test that SimpleTableFormatter uses ASCII characters for table borders."""
        from forkscout.analysis.simple_table_formatter import SimpleTableFormatter

        formatter = SimpleTableFormatter()

        # Create test data
        headers = ["SHA", "Category", "Impact", "Description"]
        rows = [
            ["abc1234", "[FEAT] Feature", "[HIGH] High", "Added new feature"],
            ["def5678", "[FIX] Bugfix", "[MED] Medium", "Fixed bug"]
        ]

        # Format as table
        table_output = formatter.format_table(headers, rows, title="Test Table")

        # Verify ASCII characters are used for borders
        assert "+" in table_output  # Corner characters
        assert "-" in table_output  # Horizontal lines
        assert "|" in table_output  # Vertical lines
        assert "=" in table_output  # Title separator

        # Verify no Unicode box drawing characters
        unicode_chars = ["┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼", "─", "│"]
        for char in unicode_chars:
            assert char not in table_output, f"Found Unicode box drawing character {char} in table output"

        # Verify no emojis in the output
        emoji_chars = ["📝", "❓", "🟢", "❔", "🚀", "🐛", "♻️", "🧪", "🔧", "⚡", "🔒",
                      "🟡", "🟠", "🔴", "✅", "❌", "⚠️", "🔗", "⚖️"]
        for emoji in emoji_chars:
            assert emoji not in table_output, f"Found emoji {emoji} in table output"

    def test_explanation_formatter_format_category_with_icon_no_emojis(self):
        """Test that format_category_with_icon produces text labels without emojis."""
        formatter = ExplanationFormatter(use_colors=False, use_icons=True)

        # Test each category type
        for category_type in CategoryType:
            formatted = formatter.format_category_with_icon(category_type)

            # Should contain text label
            assert "[" in formatted and "]" in formatted, f"Category formatting missing text label: {formatted}"

            # Should not contain emojis
            emoji_chars = ["📝", "❓", "🟢", "❔", "🚀", "🐛", "♻️", "🧪", "🔧", "⚡", "🔒"]
            for emoji in emoji_chars:
                assert emoji not in formatted, f"Found emoji {emoji} in category formatting: {formatted}"

    def test_explanation_formatter_format_impact_indicator_no_emojis(self):
        """Test that format_impact_indicator produces text labels without emojis."""
        formatter = ExplanationFormatter(use_colors=False, use_icons=True)

        # Test each impact level
        for impact_level in ImpactLevel:
            formatted = formatter.format_impact_indicator(impact_level)

            # Should contain text label
            assert "[" in formatted and "]" in formatted, f"Impact formatting missing text label: {formatted}"

            # Should not contain emojis
            emoji_chars = ["🟡", "🟠", "🔴", "✅", "❌", "⚠️"]
            for emoji in emoji_chars:
                assert emoji not in formatted, f"Found emoji {emoji} in impact formatting: {formatted}"

    def test_explanation_formatter_strip_rich_formatting(self):
        """Test that _strip_rich_formatting removes Rich codes but preserves ASCII labels."""
        formatter = ExplanationFormatter()

        # Test Rich formatting removal
        rich_text = "[bold red][FEAT] Feature[/bold red]"
        stripped = formatter._strip_rich_formatting(rich_text)

        # Should preserve ASCII label but remove Rich formatting
        assert "[FEAT]" in stripped
        assert "Feature" in stripped
        assert "[bold red]" not in stripped
        assert "[/bold red]" not in stripped

        # Test with multiple Rich codes
        complex_rich = "[bold yellow][HIGH] High[/bold yellow] [link=url]Link[/link]"
        stripped_complex = formatter._strip_rich_formatting(complex_rich)

        assert "[HIGH]" in stripped_complex
        assert "High" in stripped_complex
        assert "Link" in stripped_complex
        assert "[bold yellow]" not in stripped_complex
        assert "[link=url]" not in stripped_complex

    def test_no_problematic_emojis_in_constants(self):
        """Test that the specific problematic emojis mentioned in requirements are not used."""
        formatter = ExplanationFormatter()

        # Check all constant dictionaries for problematic emojis
        problematic_emojis = ["📝", "❓", "🟢", "❔"]

        # Check category icons
        for icon in formatter.CATEGORY_ICONS.values():
            for emoji in problematic_emojis:
                assert emoji not in icon, f"Found problematic emoji {emoji} in category icon {icon}"

        # Check impact indicators
        for indicator in formatter.IMPACT_INDICATORS.values():
            for emoji in problematic_emojis:
                assert emoji not in indicator, f"Found problematic emoji {emoji} in impact indicator {indicator}"

        # Check value indicators
        for indicator in formatter.VALUE_INDICATORS.values():
            for emoji in problematic_emojis:
                assert emoji not in indicator, f"Found problematic emoji {emoji} in value indicator {indicator}"
