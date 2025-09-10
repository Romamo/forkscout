"""Simple ASCII table formatter for terminal compatibility."""



class SimpleTableFormatter:
    """Simple ASCII table formatter that works in all terminals."""

    def __init__(self):
        """Initialize the simple table formatter."""
        pass

    def format_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        title: str = None,
        column_widths: list[int] = None
    ) -> str:
        """
        Format data as a simple ASCII table.
        
        Args:
            headers: List of column headers
            rows: List of rows, each row is a list of cell values
            title: Optional table title
            column_widths: Optional list of column widths
            
        Returns:
            Formatted table as string
        """
        if not headers or not rows:
            return "No data to display"

        # Calculate column widths if not provided
        if column_widths is None:
            column_widths = []
            for i, header in enumerate(headers):
                max_width = len(header)
                for row in rows:
                    if i < len(row):
                        max_width = max(max_width, len(str(row[i])))
                column_widths.append(max_width)

        # Ensure column widths are at least as wide as headers
        for i, header in enumerate(headers):
            column_widths[i] = max(column_widths[i], len(header))

        # Build the table
        lines = []

        # Title
        if title:
            table_width = sum(column_widths) + len(headers) * 3 + 1
            title_line = f" {title} "
            padding = (table_width - len(title_line)) // 2
            lines.append("=" * table_width)
            lines.append("=" + " " * padding + title_line + " " * (table_width - len(title_line) - padding - 2) + "=")
            lines.append("=" * table_width)

        # Top border
        border_line = "+"
        for width in column_widths:
            border_line += "-" * (width + 2) + "+"
        lines.append(border_line)

        # Headers
        header_line = "|"
        for i, header in enumerate(headers):
            header_line += f" {header:<{column_widths[i]}} |"
        lines.append(header_line)

        # Header separator
        lines.append(border_line)

        # Data rows
        for row in rows:
            row_line = "|"
            for i, cell in enumerate(row):
                if i < len(column_widths):
                    cell_str = str(cell) if cell is not None else ""
                    # Truncate if too long
                    if len(cell_str) > column_widths[i]:
                        cell_str = cell_str[:column_widths[i] - 3] + "..."
                    row_line += f" {cell_str:<{column_widths[i]}} |"
            lines.append(row_line)

        # Bottom border
        lines.append(border_line)

        return "\n".join(lines)

    def format_commit_explanations_table(
        self,
        explanations_data: list[tuple[str, str, str, str, str, str]]
    ) -> str:
        """
        Format commit explanations as a simple ASCII table.
        
        Args:
            explanations_data: List of tuples (sha, category, impact, value, description, github_link)
            
        Returns:
            Formatted table as string
        """
        headers = ["SHA", "Category", "Impact", "Value", "Description", "GitHub"]
        column_widths = [8, 12, 8, 8, 50, 10]

        return self.format_table(
            headers=headers,
            rows=explanations_data,
            title="Commit Explanations",
            column_widths=column_widths
        )
