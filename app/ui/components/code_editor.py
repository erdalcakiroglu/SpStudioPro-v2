"""
Code Editor component based on QScintilla for syntax highlighting and line numbers.
Modern VS Code inspired dark theme with rich SQL syntax highlighting.
"""

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QColor, QFont
from PyQt6.Qsci import QsciScintilla, QsciLexerSQL
from typing import Optional


class SQLLexer(QsciLexerSQL):
    """Custom SQL Lexer with enhanced keyword highlighting"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def keywords(self, set_number: int) -> str:
        """Override keywords for better categorization"""
        if set_number == 1:
            # Primary DML keywords (SELECT/INSERT/UPDATE/DELETE) - Blue
            return (
                "select insert update delete merge"
            )
        elif set_number == 5:
            # Clauses / Joins - Purple
            return (
                "from where and or not in is null "
                "join left right inner outer full cross on as "
                "order by group having distinct top "
                "union all exists between like case when then else end "
                "with cte over partition row_number rank dense_rank "
                "asc desc nulls first last offset fetch next rows only"
            )
        elif set_number == 6:
            # Data types - Cyan
            return (
                "int integer bigint smallint tinyint "
                "varchar nvarchar char nchar text ntext "
                "decimal numeric float real money smallmoney "
                "date datetime datetime2 datetimeoffset time timestamp "
                "bit binary varbinary image "
                "uniqueidentifier xml sql_variant "
                "max"
            )
        elif set_number == 7:
            # Functions - Yellow
            return (
                "count sum avg min max "
                "isnull coalesce nullif iif choose "
                "cast convert try_cast try_convert "
                "len datalength substring left right ltrim rtrim trim "
                "upper lower replace stuff charindex patindex "
                "getdate getutcdate dateadd datediff datepart datename "
                "year month day hour minute second "
                "newid scope_identity @@identity @@rowcount @@error "
                "object_id object_name db_id db_name "
                "format string_agg concat concat_ws "
                "json_value json_query json_modify "
                "row_number rank dense_rank ntile lag lead "
                "first_value last_value"
            )
        elif set_number == 8:
            # DDL / Control flow - Amber
            return (
                "create alter drop table view procedure function trigger index "
                "begin end if else while return declare set exec execute "
                "into values primary key foreign references constraint default "
                "go use database schema grant revoke "
                "try catch throw transaction commit rollback"
            )
        return super().keywords(set_number)


class CodeEditor(QsciScintilla):
    """
    A professional code editor widget with SQL syntax highlighting,
    line numbers, and modern VS Code-inspired dark theme.
    """

    _PALETTE_DARK = {
        'bg': "#1E1E1E",           # Editor background
        'bg_line': "#2D2D30",      # Current line
        'margin_bg': "#1E1E1E",    # Line number margin
        'margin_fg': "#858585",    # Line numbers
        'selection': "#264F78",    # Selection
        'selection_fg': "#FFFFFF",
        'caret': "#AEAFAD",        # Cursor
        'brace_bg': "#3A3A3A",
        'brace_fg': "#FFFF00",
        'edge': "#3A3A3A",

        # Syntax
        'keyword': "#569CD6",      # SELECT, INSERT, FROM, WHERE (blue)
        'keyword_join': "#C586C0",  # JOIN/clauses (purple/pink)
        'keyword_ctrl': "#D7BA7D",  # DDL/control flow (amber)
        'datatype': "#4EC9B0",     # INT, VARCHAR, DATETIME (cyan/teal)
        'function': "#DCDCAA",     # COUNT, SUM, GETDATE (yellow)
        'string': "#CE9178",       # 'string values' (orange)
        'number': "#B5CEA8",       # 123, 45.67 (light green)
        'comment': "#6A9955",      # -- comments (green)
        'identifier': "#9CDCFE",   # Column/table names (light blue)
        'operator': "#D4D4D4",     # =, +, -, *, / (white/gray)
        'default': "#D4D4D4",      # Default text
    }

    _PALETTE_LIGHT = {
        'bg': "#f8fafc",           # Editor background (light gray)
        'bg_line': "#e5e7eb",      # Current line
        'margin_bg': "#eef2f7",    # Line number margin
        'margin_fg': "#9ca3af",    # Line numbers
        'selection': "#e4f0f4",    # Selection (teal tint)
        'selection_fg': "#1f2937",
        'caret': "#1f2937",        # Cursor
        'brace_bg': "#d1d5db",
        'brace_fg': "#111827",
        'edge': "#d1d5db",

        # Syntax (light theme)
        'keyword': "#2563eb",
        'keyword_join': "#7c3aed",
        'keyword_ctrl': "#b45309",
        'datatype': "#0f766e",
        'function': "#0ea5e9",
        'string': "#9a3412",
        'number': "#0f766e",
        'comment': "#64748b",
        'identifier': "#1f2937",
        'operator': "#1f2937",
        'default': "#1f2937",
    }
    
    def __init__(self, parent: Optional[object] = None, theme_override: Optional[str] = None):
        super().__init__(parent)
        self._theme_override = (theme_override or "").strip().lower()
        self._setup_editor()
        self._apply_theme()

        try:
            from app.ui.theme import get_theme_manager
            get_theme_manager().theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass

    def _setup_editor(self) -> None:
        """Configure basic editor settings"""
        # UTF-8 encoding
        self.setUtf8(True)
        
        # Line numbers (Margin 0)
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "00000")  # 5 digits
        self.setMarginLineNumbers(0, True)
        
        # Folding margin (Margin 1) - optional, can show +/- for blocks
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 1)
        
        # Current line highlighting
        self.setCaretLineVisible(True)
        self.setCaretWidth(2)
        
        # Indentation
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setAutoIndent(True)
        
        # Brace matching
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        
        # Edge column (120 chars)
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(120)
        
        # Scrolling
        self.setScrollWidth(1)
        self.setScrollWidthTracking(True)
        
        # No horizontal scrollbar initially
        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 1)
        
        # Word wrap off
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        
        # Read-only by default for explorer
        self.setReadOnly(False)

    def _resolve_palette(self) -> dict:
        if self._theme_override == "dark":
            return self._PALETTE_DARK
        if self._theme_override == "light":
            return self._PALETTE_LIGHT
        try:
            from app.ui.theme import get_theme_manager
            from app.core.constants import Theme as ThemeEnum

            manager = get_theme_manager()
            if manager.current_theme == ThemeEnum.DARK:
                return self._PALETTE_DARK
        except Exception:
            pass
        return self._PALETTE_LIGHT

    def _on_theme_changed(self, _theme_name: str) -> None:
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Apply SQL Lexer and VS Code Dark+ colors"""
        colors = self._resolve_palette()
        self.lexer = SQLLexer(self)
        
        # Font - Cascadia Code or Consolas
        font = QFont("Cascadia Code", 11)
        if not font.exactMatch():
            font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.lexer.setFont(font)
        self.setFont(font)
        
        # ═══════════════════════════════════════════════════════════
        # SQL Syntax Colors
        # ═══════════════════════════════════════════════════════════
        
        # Keywords (SELECT, FROM, WHERE, JOIN, etc.)
        self.lexer.setColor(QColor(colors['keyword']), QsciLexerSQL.Keyword)
        
        # Clause / join keywords - Purple
        self.lexer.setColor(QColor(colors['keyword_join']), QsciLexerSQL.KeywordSet5)
        
        # Data types (INT, VARCHAR) - Teal/Cyan
        self.lexer.setColor(QColor(colors['datatype']), QsciLexerSQL.KeywordSet6)
        
        # Functions (COUNT, SUM, GETDATE) - Yellow
        self.lexer.setColor(QColor(colors['function']), QsciLexerSQL.KeywordSet7)

        # DDL / control flow - Amber
        self.lexer.setColor(QColor(colors['keyword_ctrl']), QsciLexerSQL.KeywordSet8)
        
        # Strings - Orange
        self.lexer.setColor(QColor(colors['string']), QsciLexerSQL.SingleQuotedString)
        self.lexer.setColor(QColor(colors['string']), QsciLexerSQL.DoubleQuotedString)
        
        # Comments - Green
        self.lexer.setColor(QColor(colors['comment']), QsciLexerSQL.Comment)
        self.lexer.setColor(QColor(colors['comment']), QsciLexerSQL.CommentLine)
        self.lexer.setColor(QColor(colors['comment']), QsciLexerSQL.CommentDoc)
        self.lexer.setColor(QColor(colors['comment']), QsciLexerSQL.CommentLineHash)
        
        # Numbers - Light Green
        self.lexer.setColor(QColor(colors['number']), QsciLexerSQL.Number)
        
        # Identifiers (columns, tables) - Light Blue
        self.lexer.setColor(QColor(colors['identifier']), QsciLexerSQL.Identifier)
        self.lexer.setColor(QColor(colors['identifier']), QsciLexerSQL.QuotedIdentifier)
        
        # Operators - White/Gray
        self.lexer.setColor(QColor(colors['operator']), QsciLexerSQL.Operator)
        self.lexer.setColor(QColor(colors['operator']), QsciLexerSQL.PlusKeyword)
        
        # Default - Gray
        self.lexer.setColor(QColor(colors['default']), QsciLexerSQL.Default)
        
        # ═══════════════════════════════════════════════════════════
        # Background colors for all styles
        # ═══════════════════════════════════════════════════════════
        bg_color = QColor(colors['bg'])
        
        # Set paper (background) for all lexer styles
        for style in range(128):
            self.lexer.setPaper(bg_color, style)
        
        self.setPaper(bg_color)
        
        # Selection color
        self.setSelectionBackgroundColor(QColor(colors['selection']))
        self.setSelectionForegroundColor(QColor(colors['selection_fg']))
        
        # Margin colors
        self.setMarginsBackgroundColor(QColor(colors['margin_bg']))
        self.setMarginsForegroundColor(QColor(colors['margin_fg']))
        
        # Folding margin colors
        self.setFoldMarginColors(
            QColor(colors['bg']),
            QColor(colors['bg'])
        )

        # Caret + line, braces, edge
        self.setCaretLineBackgroundColor(QColor(colors['bg_line']))
        self.setCaretForegroundColor(QColor(colors['caret']))
        self.setMatchedBraceBackgroundColor(QColor(colors['brace_bg']))
        self.setMatchedBraceForegroundColor(QColor(colors['brace_fg']))
        self.setEdgeColor(QColor(colors['edge']))
        
        self.setLexer(self.lexer)

    def set_text(self, text: str) -> None:
        """Helper to set text and reset cursor"""
        self.setText(text)
        self.setCursorPosition(0, 0)
    
    def set_readonly(self, readonly: bool) -> None:
        """Set editor read-only state"""
        self.setReadOnly(readonly)
