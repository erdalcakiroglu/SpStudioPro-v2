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
            # Primary keywords (DML/DDL) - Blue
            return (
                "SELECT INSERT UPDATE DELETE FROM WHERE AND OR NOT IN IS NULL "
                "JOIN LEFT RIGHT INNER OUTER FULL CROSS ON AS "
                "CREATE ALTER DROP TABLE VIEW PROCEDURE FUNCTION TRIGGER INDEX "
                "BEGIN END IF ELSE WHILE RETURN DECLARE SET EXEC EXECUTE "
                "INTO VALUES ORDER BY GROUP HAVING DISTINCT TOP "
                "UNION ALL EXISTS BETWEEN LIKE CASE WHEN THEN "
                "PRIMARY KEY FOREIGN REFERENCES CONSTRAINT DEFAULT "
                "GO USE DATABASE SCHEMA GRANT REVOKE "
                "TRY CATCH THROW TRANSACTION COMMIT ROLLBACK "
                "WITH CTE OVER PARTITION ROW_NUMBER RANK DENSE_RANK "
                "ASC DESC NULLS FIRST LAST OFFSET FETCH NEXT ROWS ONLY"
            )
        elif set_number == 2:
            # Data types - Cyan
            return (
                "INT INTEGER BIGINT SMALLINT TINYINT "
                "VARCHAR NVARCHAR CHAR NCHAR TEXT NTEXT "
                "DECIMAL NUMERIC FLOAT REAL MONEY SMALLMONEY "
                "DATE DATETIME DATETIME2 DATETIMEOFFSET TIME TIMESTAMP "
                "BIT BINARY VARBINARY IMAGE "
                "UNIQUEIDENTIFIER XML SQL_VARIANT "
                "MAX"
            )
        elif set_number == 3:
            # Functions - Yellow
            return (
                "COUNT SUM AVG MIN MAX "
                "ISNULL COALESCE NULLIF IIF CHOOSE "
                "CAST CONVERT TRY_CAST TRY_CONVERT "
                "LEN DATALENGTH SUBSTRING LEFT RIGHT LTRIM RTRIM TRIM "
                "UPPER LOWER REPLACE STUFF CHARINDEX PATINDEX "
                "GETDATE GETUTCDATE DATEADD DATEDIFF DATEPART DATENAME "
                "YEAR MONTH DAY HOUR MINUTE SECOND "
                "NEWID SCOPE_IDENTITY @@IDENTITY @@ROWCOUNT @@ERROR "
                "OBJECT_ID OBJECT_NAME DB_ID DB_NAME "
                "FORMAT STRING_AGG CONCAT CONCAT_WS "
                "JSON_VALUE JSON_QUERY JSON_MODIFY "
                "ROW_NUMBER RANK DENSE_RANK NTILE LAG LEAD "
                "FIRST_VALUE LAST_VALUE"
            )
        return super().keywords(set_number)


class CodeEditor(QsciScintilla):
    """
    A professional code editor widget with SQL syntax highlighting,
    line numbers, and modern VS Code-inspired dark theme.
    """
    
    # Color Palette (VS Code Dark+ inspired)
    COLORS = {
        'bg': "#1E1E1E",           # Editor background
        'bg_line': "#2D2D30",      # Current line
        'margin_bg': "#1E1E1E",    # Line number margin
        'margin_fg': "#858585",    # Line numbers
        'selection': "#264F78",    # Selection
        'caret': "#AEAFAD",        # Cursor
        
        # Syntax
        'keyword': "#569CD6",      # SELECT, INSERT, FROM, WHERE (blue)
        'keyword2': "#C586C0",     # BEGIN, END, IF, ELSE (purple/pink)
        'datatype': "#4EC9B0",     # INT, VARCHAR, DATETIME (cyan/teal)
        'function': "#DCDCAA",     # COUNT, SUM, GETDATE (yellow)
        'string': "#CE9178",       # 'string values' (orange)
        'number': "#B5CEA8",       # 123, 45.67 (light green)
        'comment': "#6A9955",      # -- comments (green)
        'identifier': "#9CDCFE",   # Column/table names (light blue)
        'operator': "#D4D4D4",     # =, +, -, *, / (white/gray)
        'default': "#D4D4D4",      # Default text
    }
    
    def __init__(self, parent: Optional[object] = None):
        super().__init__(parent)
        self._setup_editor()
        self._apply_theme()

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
        self.setCaretLineBackgroundColor(QColor(self.COLORS['bg_line']))
        self.setCaretForegroundColor(QColor(self.COLORS['caret']))
        self.setCaretWidth(2)
        
        # Indentation
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setAutoIndent(True)
        
        # Brace matching
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(QColor("#3A3A3A"))
        self.setMatchedBraceForegroundColor(QColor("#FFFF00"))
        
        # Edge column (80 chars)
        self.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
        self.setEdgeColumn(120)
        self.setEdgeColor(QColor("#3A3A3A"))
        
        # Scrolling
        self.setScrollWidth(1)
        self.setScrollWidthTracking(True)
        
        # No horizontal scrollbar initially
        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 1)
        
        # Word wrap off
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        
        # Read-only by default for explorer
        self.setReadOnly(False)

    def _apply_theme(self) -> None:
        """Apply SQL Lexer and VS Code Dark+ colors"""
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
        
        # Keywords (SELECT, FROM, WHERE, JOIN, etc.) - Blue
        self.lexer.setColor(QColor(self.COLORS['keyword']), QsciLexerSQL.Keyword)
        
        # Secondary keywords (BEGIN, END, IF) - Purple  
        self.lexer.setColor(QColor(self.COLORS['keyword2']), QsciLexerSQL.KeywordSet5)
        
        # Data types (INT, VARCHAR) - Teal/Cyan
        self.lexer.setColor(QColor(self.COLORS['datatype']), QsciLexerSQL.KeywordSet6)
        
        # Functions (COUNT, SUM, GETDATE) - Yellow
        self.lexer.setColor(QColor(self.COLORS['function']), QsciLexerSQL.KeywordSet7)
        
        # Strings - Orange
        self.lexer.setColor(QColor(self.COLORS['string']), QsciLexerSQL.SingleQuotedString)
        self.lexer.setColor(QColor(self.COLORS['string']), QsciLexerSQL.DoubleQuotedString)
        
        # Comments - Green
        self.lexer.setColor(QColor(self.COLORS['comment']), QsciLexerSQL.Comment)
        self.lexer.setColor(QColor(self.COLORS['comment']), QsciLexerSQL.CommentLine)
        self.lexer.setColor(QColor(self.COLORS['comment']), QsciLexerSQL.CommentDoc)
        self.lexer.setColor(QColor(self.COLORS['comment']), QsciLexerSQL.CommentLineHash)
        
        # Numbers - Light Green
        self.lexer.setColor(QColor(self.COLORS['number']), QsciLexerSQL.Number)
        
        # Identifiers (columns, tables) - Light Blue
        self.lexer.setColor(QColor(self.COLORS['identifier']), QsciLexerSQL.Identifier)
        self.lexer.setColor(QColor(self.COLORS['identifier']), QsciLexerSQL.QuotedIdentifier)
        
        # Operators - White/Gray
        self.lexer.setColor(QColor(self.COLORS['operator']), QsciLexerSQL.Operator)
        self.lexer.setColor(QColor(self.COLORS['operator']), QsciLexerSQL.PlusKeyword)
        
        # Default - Gray
        self.lexer.setColor(QColor(self.COLORS['default']), QsciLexerSQL.Default)
        
        # ═══════════════════════════════════════════════════════════
        # Background colors for all styles
        # ═══════════════════════════════════════════════════════════
        bg_color = QColor(self.COLORS['bg'])
        
        # Set paper (background) for all lexer styles
        for style in range(128):
            self.lexer.setPaper(bg_color, style)
        
        self.setPaper(bg_color)
        
        # Selection color
        self.setSelectionBackgroundColor(QColor(self.COLORS['selection']))
        self.setSelectionForegroundColor(QColor("#FFFFFF"))
        
        # Margin colors
        self.setMarginsBackgroundColor(QColor(self.COLORS['margin_bg']))
        self.setMarginsForegroundColor(QColor(self.COLORS['margin_fg']))
        
        # Folding margin colors
        self.setFoldMarginColors(
            QColor(self.COLORS['bg']), 
            QColor(self.COLORS['bg'])
        )
        
        self.setLexer(self.lexer)

    def set_text(self, text: str) -> None:
        """Helper to set text and reset cursor"""
        self.setText(text)
        self.setCursorPosition(0, 0)
    
    def set_readonly(self, readonly: bool) -> None:
        """Set editor read-only state"""
        self.setReadOnly(readonly)
