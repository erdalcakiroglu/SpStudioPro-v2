"""
Chat View - AI-powered chat interface with Modern Enterprise Design
"""

from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QFrame,
    QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors
from app.core.logger import get_logger

logger = get_logger('ui.chat')


@dataclass
class ChatMessage:
    """Chat message data"""
    content: str
    is_user: bool
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MessageBubble(QFrame):
    """Chat message bubble widget"""
    
    def __init__(self, message: ChatMessage, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.message = message
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        if self.message.is_user:
            self.setObjectName("userMessage")
            self.setStyleSheet(f"""
                QFrame#userMessage {{
                    background-color: {Colors.PRIMARY};
                    border-radius: 18px 18px 4px 18px;
                    padding: 12px 16px;
                }}
            """)
        else:
            self.setObjectName("aiMessage")
            self.setStyleSheet(f"""
                QFrame#aiMessage {{
                    background-color: {Colors.SURFACE};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 18px 18px 18px 4px;
                    padding: 12px 16px;
                }}
            """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Message content
        content_label = QLabel(self.message.content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        if self.message.is_user:
            content_label.setStyleSheet("color: white; background: transparent;")
        else:
            content_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(content_label)
        
        # Timestamp (small, muted)
        time_label = QLabel(self.message.timestamp.strftime("%H:%M"))
        time_label.setObjectName("messageTime")
        if self.message.is_user:
            time_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px; background: transparent;")
        else:
            time_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px; background: transparent;")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(time_label)
        
        # Set max width
        self.setMaximumWidth(600)
        
        # Size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)


class QuickActionButton(QPushButton):
    """Quick action button with modern styling"""
    
    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 11))
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 20px;
                padding: 10px 20px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
                border-color: {Colors.PRIMARY};
                color: {Colors.PRIMARY};
            }}
        """)


class ChatView(BaseView):
    """
    AI Chat interface - main interaction point with modern design
    
    Signals:
        message_sent: Emitted when user sends a message
    """
    
    message_sent = pyqtSignal(str)
    
    # Quick action suggestions - grouped by category
    QUICK_ACTIONS = [
        "📊  Top Queries",
        "⏱️  Wait Stats",
        "🔒  Blocking",
        "📈  Index Recommendations",
        "💾  Memory Status",
    ]
    
    # Example queries for help
    EXAMPLE_QUERIES = [
        ("Performance", [
            "Show the 10 slowest queries",
            "Queries with high CPU usage",
            "Most frequently executed queries in the last hour",
        ]),
        ("Wait Stats", [
            "Show top wait statistics",
            "Analyze PAGEIOLATCH waits",
            "What is the signal wait ratio?",
        ]),
        ("Index", [
            "List missing index recommendations",
            "Find unused indexes",
            "Index fragmentation status",
        ]),
        ("General", [
            "Summarize server status",
            "Are there any blocking sessions?",
            "When was the last backup taken?",
        ]),
    ]
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._messages: List[ChatMessage] = []
    
    @property
    def view_title(self) -> str:
        return "Chat"
    
    def _setup_ui(self) -> None:
        """Setup chat interface with modern design"""
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        # Welcome/Home section
        self._create_home_section()
        
        # Chat messages area (scrollable, initially hidden)
        self._create_messages_area()
        
        # Input area is now part of the home section
    
    def _create_home_section(self) -> None:
        """Create modern home screen section"""
        self._home_widget = QWidget()
        self._home_widget.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        home_layout = QVBoxLayout(self._home_widget)
        home_layout.setContentsMargins(60, 50, 60, 40)
        home_layout.setSpacing(0)

        home_layout.addStretch(2)

        # ─── Title & Subtitle ───
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)

        title = QLabel("Chat with your Database")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 36px;
            font-weight: bold;
            background: transparent;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        title_layout.addWidget(title)

        subtitle = QLabel("Ask performance questions, inspect slow queries, and get AI-powered tuning suggestions.")
        subtitle.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 15px;
            background: transparent;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setWordWrap(True)
        title_layout.addWidget(subtitle)

        home_layout.addWidget(title_container)
        home_layout.addSpacing(50)

        # ─── Chat Card ───
        chat_card = QFrame()
        chat_card.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border-radius: 18px;
                border: 1px solid {Colors.BORDER};
            }}
        """)
        chat_card.setFixedHeight(190)
        chat_card.setMaximumWidth(850)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setXOffset(0)
        shadow.setYOffset(12)
        shadow.setColor(QColor(15, 23, 42, 30))
        chat_card.setGraphicsEffect(shadow)

        chat_card_layout = QVBoxLayout(chat_card)
        chat_card_layout.setContentsMargins(28, 28, 28, 28)
        chat_card_layout.setSpacing(20)

        # Input Container
        input_container = QFrame()
        input_container.setStyleSheet(f"""
            QFrame {{
                background-color: #F8FAFC;
                border-radius: 14px;
                border: 1px solid {Colors.BORDER};
            }}
        """)
        input_container.setFixedHeight(56)

        ic_layout = QHBoxLayout(input_container)
        ic_layout.setContentsMargins(16, 8, 8, 8)
        ic_layout.setSpacing(12)

        # Input field
        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Ask anything about your database performance...")
        self._input_field.setFont(QFont("Segoe UI", 13))
        self._input_field.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background-color: transparent;
                padding: 8px 4px;
                font-size: 14px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self._input_field.returnPressed.connect(self._send_message)
        ic_layout.addWidget(self._input_field, stretch=1)

        # Send button
        self._send_btn = QPushButton("Send  →")
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._send_btn.setFixedSize(110, 40)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        self._send_btn.clicked.connect(self._send_message)
        ic_layout.addWidget(self._send_btn)

        chat_card_layout.addWidget(input_container)

        # Quick Actions
        quick_container = QWidget()
        quick_container.setStyleSheet("background: transparent;")
        quick_layout = QHBoxLayout(quick_container)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(12)

        for text in self.QUICK_ACTIONS:
            qa = QuickActionButton(text)
            qa.clicked.connect(lambda checked, t=text: self._on_quick_action_clicked(t))
            quick_layout.addWidget(qa)

        quick_layout.addStretch()
        chat_card_layout.addWidget(quick_container)

        # Center card
        chat_wrapper = QHBoxLayout()
        chat_wrapper.addStretch()
        chat_wrapper.addWidget(chat_card)
        chat_wrapper.addStretch()
        home_layout.addLayout(chat_wrapper)
        
        home_layout.addSpacing(40)
        
        # Example queries section
        examples_container = QWidget()
        examples_container.setStyleSheet("background: transparent;")
        examples_container.setMaximumWidth(900)
        examples_layout = QVBoxLayout(examples_container)
        examples_layout.setContentsMargins(0, 0, 0, 0)
        examples_layout.setSpacing(16)
        
        examples_title = QLabel("💡 Example Queries")
        examples_title.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 14px;
            font-weight: 600;
            background: transparent;
        """)
        examples_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        examples_layout.addWidget(examples_title)
        
        # Create grid of example categories
        examples_grid = QHBoxLayout()
        examples_grid.setSpacing(16)
        
        for category, queries in self.EXAMPLE_QUERIES:
            cat_card = QFrame()
            cat_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {Colors.SURFACE};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 12px;
                }}
            """)
            cat_layout = QVBoxLayout(cat_card)
            cat_layout.setContentsMargins(16, 12, 16, 12)
            cat_layout.setSpacing(8)
            
            cat_label = QLabel(category)
            cat_label.setStyleSheet(f"""
                color: {Colors.PRIMARY};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            """)
            cat_layout.addWidget(cat_label)
            
            for query in queries:
                query_btn = QPushButton(query)
                query_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                query_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {Colors.TEXT_SECONDARY};
                        border: none;
                        text-align: left;
                        padding: 4px 0;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        color: {Colors.PRIMARY};
                    }}
                """)
                query_btn.clicked.connect(lambda checked, q=query: self._use_example_query(q))
                cat_layout.addWidget(query_btn)
            
            examples_grid.addWidget(cat_card)
        
        examples_layout.addLayout(examples_grid)
        
        examples_wrapper = QHBoxLayout()
        examples_wrapper.addStretch()
        examples_wrapper.addWidget(examples_container)
        examples_wrapper.addStretch()
        home_layout.addLayout(examples_wrapper)

        home_layout.addStretch(2)

        self._main_layout.addWidget(self._home_widget)
    
    def _create_messages_area(self) -> None:
        """Create scrollable messages area"""
        # Container for chat mode
        self._chat_widget = QWidget()
        self._chat_widget.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        chat_layout = QVBoxLayout(self._chat_widget)
        chat_layout.setContentsMargins(40, 20, 40, 20)
        chat_layout.setSpacing(0)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{ 
                border: none; 
                background: {Colors.BACKGROUND}; 
            }}
        """)
        
        # Messages container
        self._messages_container = QWidget()
        self._messages_container.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._messages_layout.setSpacing(16)
        self._messages_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add stretch at bottom to push messages up
        self._messages_layout.addStretch()
        
        scroll_area.setWidget(self._messages_container)
        self._scroll_area = scroll_area
        
        chat_layout.addWidget(scroll_area, 1)
        
        # Chat input area (for when in chat mode)
        self._create_chat_input_area(chat_layout)
        
        # Initially hidden (show when messages exist)
        self._chat_widget.setVisible(False)
        self._main_layout.addWidget(self._chat_widget)
    
    def _create_chat_input_area(self, parent_layout: QVBoxLayout) -> None:
        """Create chat input area for chat mode"""
        input_container = QWidget()
        input_container.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 16, 0, 0)
        input_layout.setSpacing(12)
        
        # Chat mode input field
        self._chat_input_field = QLineEdit()
        self._chat_input_field.setPlaceholderText("Ask about SQL performance...")
        self._chat_input_field.setFont(QFont("Segoe UI", 13))
        self._chat_input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 24px;
                padding: 14px 20px;
                font-size: 14px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self._chat_input_field.returnPressed.connect(self._send_chat_message)
        input_layout.addWidget(self._chat_input_field, 1)
        
        # Chat send button
        self._chat_send_btn = QPushButton("Send  →")
        self._chat_send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._chat_send_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self._chat_send_btn.setFixedSize(110, 48)
        self._chat_send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 24px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        self._chat_send_btn.clicked.connect(self._send_chat_message)
        input_layout.addWidget(self._chat_send_btn)
        
        parent_layout.addWidget(input_container)
    
    def _on_quick_action_clicked(self, text: str) -> None:
        """Handle quick action button click"""
        # Remove emoji prefix
        clean_text = text.split("  ", 1)[-1] if "  " in text else text
        self._input_field.setText(clean_text)
        self._send_message()
    
    def _use_example_query(self, query: str) -> None:
        """Use an example query"""
        self._input_field.setText(query)
        self._send_message()
    
    def _send_message(self) -> None:
        """Send user message from home screen"""
        text = self._input_field.text().strip()
        if not text:
            return
        
        # Clear input
        self._input_field.clear()
        
        # Switch to chat mode
        self._home_widget.setVisible(False)
        self._chat_widget.setVisible(True)
        
        # Add user message
        user_msg = ChatMessage(content=text, is_user=True)
        self._add_message(user_msg)
        
        # Emit signal for processing
        self.message_sent.emit(text)
        
        logger.info(f"User message sent: {text[:50]}...")
    
    def _send_chat_message(self) -> None:
        """Send user message from chat mode"""
        text = self._chat_input_field.text().strip()
        if not text:
            return
        
        # Clear input
        self._chat_input_field.clear()
        
        # Add user message
        user_msg = ChatMessage(content=text, is_user=True)
        self._add_message(user_msg)
        
        # Emit signal for processing
        self.message_sent.emit(text)
        
        logger.info(f"User message sent: {text[:50]}...")
    
    def _add_message(self, message: ChatMessage) -> None:
        """Add message to chat"""
        self._messages.append(message)
        
        # Create message bubble
        bubble = MessageBubble(message)
        
        # Create alignment wrapper
        wrapper = QWidget()
        wrapper.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        
        if message.is_user:
            wrapper_layout.addStretch()
            wrapper_layout.addWidget(bubble)
        else:
            wrapper_layout.addWidget(bubble)
            wrapper_layout.addStretch()
        
        # Insert before the stretch at the bottom
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, wrapper)
        
        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)
    
    def _scroll_to_bottom(self) -> None:
        """Scroll messages to bottom"""
        scrollbar = self._scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def add_ai_response(self, text: str) -> None:
        """Add AI response message"""
        ai_msg = ChatMessage(content=text, is_user=False)
        self._add_message(ai_msg)
    
    def add_loading_indicator(self) -> None:
        """Show typing/loading indicator"""
        if hasattr(self, '_loading_widget') and self._loading_widget:
            return  # Already showing
        
        # Create loading bubble
        self._loading_widget = QFrame()
        self._loading_widget.setObjectName("loadingMessage")
        self._loading_widget.setStyleSheet(f"""
            QFrame#loadingMessage {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 18px 18px 18px 4px;
                padding: 12px 16px;
            }}
        """)
        
        layout = QHBoxLayout(self._loading_widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Animated dots
        self._loading_label = QLabel("AI is thinking...")
        self._loading_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; border: none;")
        layout.addWidget(self._loading_label)
        
        dots_label = QLabel("...")
        dots_label.setStyleSheet(f"color: {Colors.PRIMARY}; font-size: 16px; font-weight: bold; border: none;")
        layout.addWidget(dots_label)
        
        self._loading_widget.setMaximumWidth(200)
        
        # Create wrapper
        wrapper = QWidget()
        wrapper.setObjectName("loadingWrapper")
        wrapper.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self._loading_widget)
        wrapper_layout.addStretch()
        
        # Insert before stretch
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, wrapper)
        
        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)
    
    def remove_loading_indicator(self) -> None:
        """Remove loading indicator"""
        if hasattr(self, '_loading_widget') and self._loading_widget:
            # Find and remove the wrapper
            for i in range(self._messages_layout.count()):
                item = self._messages_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if widget.objectName() == "loadingWrapper":
                        self._messages_layout.removeWidget(widget)
                        widget.deleteLater()
                        break
            self._loading_widget = None
    
    def clear_chat(self) -> None:
        """Clear all messages and return to home screen"""
        self._messages.clear()
        
        # Remove all message widgets
        while self._messages_layout.count() > 1:  # Keep the stretch
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Show home screen again
        self._home_widget.setVisible(True)
        self._chat_widget.setVisible(False)
