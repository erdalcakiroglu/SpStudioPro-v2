"""
Security Audit View - Modern Enterprise Design
"""
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QSplitter,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, CircleStatCard
from app.core.logger import get_logger
from app.services.security_service import (
    get_security_service,
    SecuritySummary,
    SecurityIssue,
    Login,
)
from app.database.queries.security_queries import SecurityRisk

logger = get_logger('views.security')


class IssueCard(QFrame):
    """Card showing a security issue"""
    
    def __init__(self, issue: SecurityIssue, parent=None):
        super().__init__(parent)
        self._issue = issue
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                border-left: 4px solid {self._issue.risk_color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header row
        header = QHBoxLayout()
        
        # Risk badge
        risk_badge = QLabel(self._issue.risk.value)
        risk_badge.setStyleSheet(f"""
            background: {self._issue.risk_color}; 
            color: white; 
            padding: 2px 8px; 
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
        """)
        header.addWidget(risk_badge)
        
        # Category
        category_label = QLabel(self._issue.category)
        category_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; border: none;")
        header.addWidget(category_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Title
        title = QLabel(self._issue.title)
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; font-size: 14px; border: none;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel(self._issue.description)
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; border: none;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Details (if any)
        if self._issue.details:
            details_text = ", ".join(self._issue.details[:5])
            if len(self._issue.details) > 5:
                details_text += f" ... (+{len(self._issue.details) - 5} more)"
            
            details = QLabel(f"📋 {details_text}")
            details.setStyleSheet(f"color: {self._issue.risk_color}; font-size: 11px; border: none;")
            details.setWordWrap(True)
            layout.addWidget(details)
        
        # Recommendation
        if self._issue.recommendation:
            rec = QLabel(f"💡 {self._issue.recommendation}")
            rec.setStyleSheet(f"color: #059669; font-size: 11px; border: none;")
            rec.setWordWrap(True)
            layout.addWidget(rec)


class LoginRow(QFrame):
    """Row showing a login"""
    
    def __init__(self, login: Login, parent=None):
        super().__init__(parent)
        self._login = login
        self._setup_ui()
    
    def _setup_ui(self):
        # Determine status color
        if self._login.is_disabled:
            status_color = Colors.TEXT_SECONDARY
            status_icon = "⏸️"
        elif self._login.is_locked:
            status_color = "#EF4444"
            status_icon = "🔒"
        elif self._login.is_expired:
            status_color = "#F59E0B"
            status_icon = "⚠️"
        else:
            status_color = "#10B981"
            status_icon = "✅"
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.SURFACE};
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QFrame:hover {{
                background: {Colors.BACKGROUND};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Status icon
        icon = QLabel(status_icon)
        icon.setStyleSheet("font-size: 14px; border: none;")
        layout.addWidget(icon)
        
        # Login info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        
        name_label = QLabel(self._login.name)
        name_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 500; font-size: 12px; border: none;")
        info_layout.addWidget(name_label)
        
        type_label = QLabel(self._login.login_type)
        type_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; border: none;")
        info_layout.addWidget(type_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Status text
        if self._login.is_disabled:
            status_text = "Disabled"
        elif self._login.is_locked:
            status_text = "Locked"
        elif self._login.is_expired:
            status_text = "Expired"
        else:
            status_text = "Active"
        
        status = QLabel(status_text)
        status.setStyleSheet(f"color: {status_color}; font-size: 11px; font-weight: 500; border: none;")
        layout.addWidget(status)


class SecurityView(BaseView):
    """Security Audit view with modern enterprise design"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = get_security_service()
        self._summary_cards: Dict[str, QFrame] = {}
    
    def _setup_ui(self):
        # Title section
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side - title
        title_left = QVBoxLayout()
        title_left.setSpacing(8)
        
        title = QLabel("🛡️ Security Audit")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_left.addWidget(title)
        
        subtitle = QLabel("SQL Server security analysis and recommendations")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        title_left.addWidget(subtitle)
        
        title_layout.addLayout(title_left)
        title_layout.addStretch()
        
        # Run Audit button
        audit_btn = QPushButton("🔍 Run Audit")
        audit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {Colors.PRIMARY_HOVER};
            }}
        """)
        audit_btn.clicked.connect(self.refresh)
        title_layout.addWidget(audit_btn)
        
        self._main_layout.addWidget(title_container)
        self._main_layout.addSpacing(12)
        
        # ═══════════════════════════════════════════════════════════════════
        # SUMMARY CARDS
        # ═══════════════════════════════════════════════════════════════════
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        
        summary_items = [
            ("critical", "Critical", "0", "🔴", "#DC2626"),
            ("high", "High", "0", "🟠", "#EA580C"),
            ("medium", "Medium", "0", "🟡", "#D97706"),
            ("low", "Low", "0", "🔵", "#2563EB"),
            ("logins", "Total Logins", "0", "👤", Colors.PRIMARY),
            ("sysadmins", "Sysadmins", "0", "👑", "#8B5CF6"),
        ]
        
        for card_id, label, value, icon, color in summary_items:
            card = self._create_summary_card(icon, label, value, color)
            self._summary_cards[card_id] = card
            summary_layout.addWidget(card)
        
        summary_layout.addStretch()
        self._main_layout.addLayout(summary_layout)
        self._main_layout.addSpacing(12)
        
        # ═══════════════════════════════════════════════════════════════════
        # MAIN CONTENT
        # ═══════════════════════════════════════════════════════════════════
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Left panel - Security Issues
        left_panel = QFrame()
        left_panel.setStyleSheet(f"background: {Colors.SURFACE}; border: 1px solid {Colors.BORDER}; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Header
        issues_header = QLabel("⚠️ Security Issues")
        issues_header.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 14px; 
            font-weight: bold; 
            padding: 12px 16px;
            border-bottom: 1px solid {Colors.BORDER};
            background: transparent;
        """)
        left_layout.addWidget(issues_header)
        
        # Issues scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._issues_container = QWidget()
        self._issues_container.setStyleSheet("background: transparent;")
        self._issues_layout = QVBoxLayout(self._issues_container)
        self._issues_layout.setContentsMargins(8, 8, 8, 8)
        self._issues_layout.setSpacing(8)
        
        # Placeholder
        placeholder = QLabel("Click 'Run Audit' to analyze security")
        placeholder.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 32px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._issues_layout.addWidget(placeholder)
        self._issues_layout.addStretch()
        
        scroll.setWidget(self._issues_container)
        left_layout.addWidget(scroll)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Logins & Users
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background: {Colors.SURFACE}; border: 1px solid {Colors.BORDER}; border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Logins header
        logins_header = QLabel("👤 Server Logins")
        logins_header.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 14px; 
            font-weight: bold; 
            padding: 12px 16px;
            border-bottom: 1px solid {Colors.BORDER};
            background: transparent;
        """)
        right_layout.addWidget(logins_header)
        
        # Logins scroll
        logins_scroll = QScrollArea()
        logins_scroll.setWidgetResizable(True)
        logins_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._logins_container = QWidget()
        self._logins_container.setStyleSheet("background: transparent;")
        self._logins_layout = QVBoxLayout(self._logins_container)
        self._logins_layout.setContentsMargins(0, 0, 0, 0)
        self._logins_layout.setSpacing(0)
        
        logins_scroll.setWidget(self._logins_container)
        right_layout.addWidget(logins_scroll)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([550, 350])
        
        self._main_layout.addWidget(splitter, stretch=1)
    
    def _create_summary_card(self, icon: str, label: str, value: str, color: str) -> CircleStatCard:
        """Create a circle summary stat card - GUI-05 style"""
        title = f"{icon} {label}"
        return CircleStatCard(title, value, color)
    
    def _update_summary_card(self, card_id: str, value: str):
        """Update a summary card value"""
        if card_id in self._summary_cards:
            card = self._summary_cards[card_id]
            if isinstance(card, CircleStatCard):
                card.update_value(value)
            else:
                value_lbl = card.findChild(QLabel, "value")
                if value_lbl:
                    value_lbl.setText(value)
    
    def on_show(self) -> None:
        """Called when view becomes visible"""
        # Don't auto-refresh - let user trigger audit
        pass
    
    def refresh(self) -> None:
        """Run security audit"""
        if not self._is_initialized:
            return
            
        if not self._service.is_connected:
            logger.debug("Security audit skipped: No active connection")
            return
        
        logger.info("Running security audit...")
        
        try:
            summary = self._service.run_security_audit()
            self._update_ui(summary)
        except Exception as e:
            logger.error(f"Error running security audit: {e}")
    
    def _update_ui(self, summary: SecuritySummary):
        """Update UI with audit results"""
        # Update summary cards
        self._update_summary_card("critical", str(summary.critical_count))
        self._update_summary_card("high", str(summary.high_count))
        self._update_summary_card("medium", str(summary.medium_count))
        self._update_summary_card("low", str(summary.low_count))
        self._update_summary_card("logins", str(summary.sql_logins + summary.windows_logins))
        self._update_summary_card("sysadmins", str(summary.sysadmin_count))
        
        # Update issues list
        self._update_issues_list(summary.issues)
        
        # Update logins list
        self._update_logins_list(summary.logins)
    
    def _update_issues_list(self, issues: List[SecurityIssue]):
        """Update the issues list"""
        # Clear existing
        while self._issues_layout.count() > 1:  # Keep stretch
            item = self._issues_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not issues:
            success = QLabel("✅ No security issues found!")
            success.setStyleSheet(f"color: #10B981; font-size: 14px; padding: 32px; font-weight: bold;")
            success.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._issues_layout.insertWidget(0, success)
            return
        
        # Add issue cards
        for issue in issues:
            card = IssueCard(issue)
            self._issues_layout.insertWidget(self._issues_layout.count() - 1, card)
    
    def _update_logins_list(self, logins: List[Login]):
        """Update logins list"""
        # Clear existing
        while self._logins_layout.count():
            item = self._logins_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not logins:
            placeholder = QLabel("No logins found")
            placeholder.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 16px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._logins_layout.addWidget(placeholder)
            return
        
        for login in logins[:30]:  # Show max 30
            row = LoginRow(login)
            self._logins_layout.addWidget(row)
        
        if len(logins) > 30:
            more = QLabel(f"... and {len(logins) - 30} more")
            more.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 8px;")
            more.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._logins_layout.addWidget(more)
        
        self._logins_layout.addStretch()
