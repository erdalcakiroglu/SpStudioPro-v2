"""
Security Audit View - Modern Enterprise Design
"""
import html
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QSplitter,
    QSizePolicy, QProgressBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors
from app.core.logger import get_logger
from app.core.config import get_settings
from app.database.connection import get_connection_manager
from app.services.security_service import (
    get_security_service,
    SecuritySummary,
    SecurityIssue,
    Login,
)
from app.database.queries.security_queries import SecurityRisk, get_risk_color

logger = get_logger('views.security')


class SummaryStatCard(QFrame):
    """Square stat card for footer summary (Blocking Analysis style)."""

    SCALE = 0.62
    BASE_TILE_SIZE = 98
    BASE_VALUE_FONT_SIZE = 18
    BASE_TITLE_FONT_SIZE = 10

    def __init__(self, title: str, value: str, accent: str, parent=None):
        super().__init__(parent)
        self._accent = str(accent or Colors.PRIMARY)
        self._setup_ui(title, value)

    def _setup_ui(self, title: str, value: str) -> None:
        self.setStyleSheet("background-color: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        tile_size = max(28, int(self.BASE_TILE_SIZE * self.SCALE))
        tile_radius = max(6, min(12, int(tile_size * 0.2)))
        tile = QFrame()
        tile.setFixedSize(tile_size, tile_size)
        tile.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {tile_radius}px;
            }}
        """)
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(0, 0, 0, 0)
        tile_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_font_size = max(11, int(self.BASE_VALUE_FONT_SIZE * self.SCALE))
        self._value_label = QLabel(str(value))
        self._value_label.setStyleSheet(
            f"color: {self._accent}; font-size: {value_font_size}px; font-weight: 700; background: transparent; border: none;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile_layout.addWidget(self._value_label)

        title_font_size = max(9, int(self.BASE_TITLE_FONT_SIZE * self.SCALE))
        self._title_label = QLabel(str(title))
        self._title_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {title_font_size}px; font-weight: 700; background: transparent;"
        )
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setWordWrap(True)

        layout.addWidget(tile)
        layout.addWidget(self._title_label)

    def update_value(self, value: str) -> None:
        self._value_label.setText(str(value))


class SecurityAuditWorker(QThread):
    """Run security audit without blocking UI."""

    completed = pyqtSignal(object)  # SecuritySummary
    failed = pyqtSignal(str)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service

    def run(self) -> None:
        try:
            summary = self._service.run_security_audit()
            self.completed.emit(summary)
        except Exception as e:
            self.failed.emit(str(e))


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
            
            details = QLabel(str(details_text))
            details.setStyleSheet(f"color: {self._issue.risk_color}; font-size: 11px; border: none;")
            details.setWordWrap(True)
            layout.addWidget(details)
        
        # Recommendation
        if self._issue.recommendation:
            rec = QLabel(str(self._issue.recommendation))
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
        elif self._login.is_locked:
            status_color = "#EF4444"
        elif self._login.is_expired:
            status_color = "#F59E0B"
        else:
            status_color = "#10B981"
        
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
        self._audit_worker: Optional[SecurityAuditWorker] = None
        self._audit_btn: Optional[QPushButton] = None
        self._audit_progress: Optional[QProgressBar] = None
        self._save_report_btn: Optional[QPushButton] = None
        self._last_summary: Optional[SecuritySummary] = None
        self._last_audit_context: Dict[str, object] = {}
    
    def _setup_ui(self):
        # Title section
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_layout.addStretch()
        
        # Run Audit button
        self._audit_progress = QProgressBar()
        self._audit_progress.setRange(0, 0)  # indeterminate
        self._audit_progress.setTextVisible(False)
        self._audit_progress.setFixedHeight(10)
        self._audit_progress.setFixedWidth(140)
        self._audit_progress.setVisible(False)
        self._audit_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Colors.BORDER};
                background: {Colors.SURFACE};
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background: {Colors.PRIMARY};
                border-radius: 5px;
            }}
        """)

        self._audit_btn = QPushButton("Run Audit")
        self._audit_btn.setStyleSheet(f"""
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
            QPushButton:disabled {{
                background: {Colors.BORDER};
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self._audit_btn.clicked.connect(self.refresh)

        right_controls = QWidget()
        right_controls.setStyleSheet("background: transparent;")
        right_controls_layout = QHBoxLayout(right_controls)
        right_controls_layout.setContentsMargins(0, 0, 0, 0)
        right_controls_layout.setSpacing(10)

        self._save_report_btn = QPushButton("Save HTML")
        self._save_report_btn.setEnabled(False)
        self._save_report_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_MUTED};
                border-color: {Colors.BORDER};
            }}
        """)
        self._save_report_btn.clicked.connect(self._on_save_html_clicked)

        right_controls_layout.addWidget(self._audit_progress)
        right_controls_layout.addWidget(self._save_report_btn)
        right_controls_layout.addWidget(self._audit_btn)
        title_layout.addWidget(right_controls)
        
        self._main_layout.addWidget(title_container)
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
        issues_header = QLabel("Security Issues")
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
        logins_header = QLabel("Server Logins")
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

        # ═══════════════════════════════════════════════════════════════════
        # FOOTER SUMMARY (bottom-right) - Blocking Analysis style
        # ═══════════════════════════════════════════════════════════════════
        summary_items = [
            ("critical", "Critical", "0", "", get_risk_color(SecurityRisk.CRITICAL)),
            ("high", "High", "0", "", get_risk_color(SecurityRisk.HIGH)),
            ("medium", "Medium", "0", "", get_risk_color(SecurityRisk.MEDIUM)),
            ("low", "Low", "0", "", get_risk_color(SecurityRisk.LOW)),
            ("logins", "Total Logins", "0", "", Colors.PRIMARY),
            ("sysadmins", "Sysadmins", "0", "", "#8B5CF6"),
        ]

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(12)
        footer_layout.addStretch(1)

        summary_container = QWidget()
        summary_layout = QHBoxLayout(summary_container)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(12)

        for card_id, label, value, icon, color in summary_items:
            card = self._create_summary_card(icon, label, value, color)
            self._summary_cards[card_id] = card
            summary_layout.addWidget(card)

        footer_layout.addWidget(
            summary_container,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self._main_layout.addLayout(footer_layout)

    def _create_summary_card(self, icon: str, label: str, value: str, color: str) -> SummaryStatCard:
        icon = str(icon or "").strip()
        title = f"{icon} {label}".strip() if icon else str(label)
        return SummaryStatCard(title, value, str(color))

    def _update_summary_card(self, card_id: str, value: str):
        """Update a summary card value"""
        if card_id in self._summary_cards:
            card = self._summary_cards[card_id]
            if hasattr(card, "update_value"):
                card.update_value(value)
    
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

        if self._audit_worker and self._audit_worker.isRunning():
            return

        logger.info("Running security audit...")
        self._set_audit_running(True)

        self._audit_worker = SecurityAuditWorker(self._service, parent=self)
        self._audit_worker.completed.connect(self._on_audit_completed)
        self._audit_worker.failed.connect(self._on_audit_failed)
        self._audit_worker.start()

    def _set_audit_running(self, running: bool) -> None:
        if self._audit_btn:
            self._audit_btn.setEnabled(not running)
            self._audit_btn.setText("Running..." if running else "Run Audit")
        if self._audit_progress:
            self._audit_progress.setVisible(running)
        if self._save_report_btn:
            self._save_report_btn.setEnabled((not running) and (self._last_summary is not None))

    def _on_audit_completed(self, summary: SecuritySummary) -> None:
        self._set_audit_running(False)
        self._last_summary = summary
        self._last_audit_context = self._collect_audit_context()
        self._update_ui(summary)

    def _on_audit_failed(self, message: str) -> None:
        self._set_audit_running(False)
        logger.error(f"Error running security audit: {message}")
        self._show_message_box(
            icon=QMessageBox.Icon.Critical,
            title="Security Audit Error",
            message=f"Security audit failed:\n\n{message}",
        )
    
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

        if self._save_report_btn:
            self._save_report_btn.setEnabled(self._last_summary is not None)

    def _on_save_html_clicked(self) -> None:
        if not self._last_summary:
            return

        settings = get_settings()
        reports_dir = Path(settings.app_dir) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M")
        default_name = str(reports_dir / f"security_audit_{ts}.html")

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Security Audit Report (HTML)",
            default_name,
            "HTML Files (*.html);;All Files (*)",
        )
        if not filename:
            return

        try:
            html_report = self._build_html_report(self._last_summary, self._last_audit_context)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_report)
            self._show_message_box(
                icon=QMessageBox.Icon.Information,
                title="Report Saved",
                message=f"Report saved:\n\n{filename}",
            )
        except Exception as e:
            self._show_message_box(
                icon=QMessageBox.Icon.Critical,
                title="Save Failed",
                message=f"Failed to save report:\n\n{e}",
            )

    def _collect_audit_context(self) -> Dict[str, object]:
        """Best-effort snapshot of connection context for the report."""
        ctx: Dict[str, object] = {"surface_area": []}
        try:
            conn = get_connection_manager().active_connection
            if conn:
                # Prefer live connection info (if available).
                info = getattr(conn, "info", None)
                if info:
                    ctx["server_name"] = getattr(info, "server_name", "") or ""
                    ctx["database_name"] = getattr(info, "database_name", "") or ""
                    ctx["edition"] = getattr(info, "edition", "") or ""
                    ctx["product_version"] = getattr(info, "product_version", "") or ""
                    ctx["server_version"] = getattr(info, "server_version", "") or ""

                # Fallbacks from profile
                profile = getattr(conn, "profile", None)
                if profile:
                    ctx["server_name"] = ctx.get("server_name") or getattr(profile, "server", "") or ""
                    ctx["database_name"] = ctx.get("database_name") or getattr(profile, "database", "") or ""
                    ctx["port"] = getattr(profile, "port", "") or ""
                    ctx["auth_method"] = getattr(getattr(profile, "auth_method", None), "value", "") or ""
                    ctx["encrypt"] = "yes" if getattr(profile, "encrypt", False) else "no"
                    ctx["trust_server_certificate"] = "yes" if getattr(profile, "trust_server_certificate", False) else "no"
                    ctx["driver"] = getattr(profile, "driver", "") or ""

                # Server properties (lightweight)
                try:
                    rows = conn.execute_query(
                        """
                        SELECT
                            CONVERT(nvarchar(128), SERVERPROPERTY('MachineName')) AS machine_name,
                            CONVERT(nvarchar(128), SERVERPROPERTY('ServerName')) AS server_name_prop,
                            CONVERT(nvarchar(128), SERVERPROPERTY('InstanceName')) AS instance_name,
                            CONVERT(nvarchar(128), SERVERPROPERTY('Edition')) AS edition,
                            CONVERT(nvarchar(128), SERVERPROPERTY('ProductVersion')) AS product_version,
                            CONVERT(nvarchar(128), SERVERPROPERTY('ProductLevel')) AS product_level,
                            CONVERT(nvarchar(128), SERVERPROPERTY('ProductUpdateLevel')) AS update_level,
                            CONVERT(nvarchar(128), SERVERPROPERTY('ProductUpdateReference')) AS update_reference,
                            CONVERT(nvarchar(128), SERVERPROPERTY('Collation')) AS collation,
                            CONVERT(int, SERVERPROPERTY('IsClustered')) AS is_clustered,
                            CONVERT(int, SERVERPROPERTY('IsHadrEnabled')) AS is_hadr_enabled,
                            CONVERT(int, SERVERPROPERTY('IsIntegratedSecurityOnly')) AS integrated_only,
                            CONVERT(int, SERVERPROPERTY('EngineEdition')) AS engine_edition
                        """
                    ) or []
                    if rows:
                        r = rows[0]
                        ctx["machine_name"] = r.get("machine_name") or ""
                        ctx["server_name_prop"] = r.get("server_name_prop") or ""
                        ctx["instance_name"] = r.get("instance_name") or ""
                        ctx["edition"] = ctx.get("edition") or r.get("edition") or ""
                        ctx["product_version"] = ctx.get("product_version") or r.get("product_version") or ""
                        ctx["product_level"] = r.get("product_level") or ""
                        ctx["update_level"] = r.get("update_level") or ""
                        ctx["update_reference"] = r.get("update_reference") or ""
                        ctx["collation"] = r.get("collation") or ""
                        ctx["is_clustered"] = r.get("is_clustered")
                        ctx["is_hadr_enabled"] = r.get("is_hadr_enabled")
                        ctx["integrated_only"] = r.get("integrated_only")
                        ctx["engine_edition"] = r.get("engine_edition")
                except Exception:
                    pass

                # Surface area config (best-effort)
                try:
                    rows = conn.execute_query(
                        """
                        SELECT
                            name AS config_name,
                            CAST(value_in_use AS int) AS value_in_use
                        FROM sys.configurations
                        WHERE name IN (
                            'xp_cmdshell',
                            'Ad Hoc Distributed Queries',
                            'Ole Automation Procedures',
                            'SQL Mail XPs',
                            'Database Mail XPs',
                            'clr enabled',
                            'clr strict security',
                            'external scripts enabled'
                        )
                        ORDER BY name
                        """
                    ) or []
                    ctx["surface_area"] = rows
                except Exception:
                    pass

                # Force Encryption (registry; often requires high permissions) - best effort
                try:
                    fe = conn.execute_query(
                        """
                        DECLARE @force_encryption INT;
                        EXEC master..xp_instance_regread
                            N'HKEY_LOCAL_MACHINE',
                            N'SOFTWARE\\Microsoft\\Microsoft SQL Server\\MSSQLServer\\SuperSocketNetLib',
                            N'ForceEncryption',
                            @force_encryption OUTPUT;
                        SELECT @force_encryption AS force_encryption;
                        """
                    ) or []
                    if fe:
                        ctx["force_encryption"] = fe[0].get("force_encryption")
                except Exception:
                    pass
        except Exception:
            pass
        return ctx

    def _show_message_box(self, icon: QMessageBox.Icon, title: str, message: str) -> None:
        # Static helpers (QMessageBox.information/critical) can end up with low-contrast text
        # depending on OS theme/QSS interaction, so we style it explicitly.
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(message)
        box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)

        box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {Colors.SURFACE};
            }}
            QMessageBox QLabel {{
                color: {Colors.TEXT_PRIMARY};
                background: transparent;
            }}
            QMessageBox QPushButton {{
                background: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 90px;
            }}
            QMessageBox QPushButton:hover {{
                border-color: {Colors.PRIMARY};
            }}
        """)

        box.exec()

    def _build_html_report(self, summary: SecuritySummary, context: Optional[Dict[str, object]] = None) -> str:
        def esc(s: object) -> str:
            return html.escape("" if s is None else str(s))

        def issue_row(issue: SecurityIssue) -> str:
            details = ""
            if issue.details:
                d = "<br/>".join(esc(x) for x in issue.details[:12])
                more = ""
                if len(issue.details) > 12:
                    more = f"<br/><em>... (+{len(issue.details) - 12} more)</em>"
                details = f"<div class='details'>{d}{more}</div>"
            rec = f"<div class='rec'>{esc(issue.recommendation)}</div>" if issue.recommendation else ""
            return (
                "<div class='issue'>"
                f"<div class='meta'><span class='risk' style='background:{esc(issue.risk_color)}'>{esc(issue.risk.value)}</span>"
                f"<span class='cat'>{esc(issue.category)}</span></div>"
                f"<div class='title'>{esc(issue.title)}</div>"
                f"<div class='desc'>{esc(issue.description)}</div>"
                f"{details}{rec}"
                "</div>"
            )

        ts = summary.collected_at.strftime("%Y-%m-%d %H:%M:%S") if summary.collected_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ctx = context or {}
        server_name = esc(ctx.get("server_name", ""))
        database_name = esc(ctx.get("database_name", ""))
        edition = esc(ctx.get("edition", ""))
        product_version = esc(ctx.get("product_version", "")) or esc(ctx.get("server_version", ""))
        product_level = esc(ctx.get("product_level", ""))
        update_level = esc(ctx.get("update_level", ""))
        update_reference = esc(ctx.get("update_reference", ""))
        machine_name = esc(ctx.get("machine_name", ""))
        instance_name = esc(ctx.get("instance_name", ""))
        collation = esc(ctx.get("collation", ""))
        engine_edition = esc(ctx.get("engine_edition", ""))
        is_clustered = ctx.get("is_clustered", None)
        is_hadr_enabled = ctx.get("is_hadr_enabled", None)
        integrated_only = ctx.get("integrated_only", None)
        force_encryption = ctx.get("force_encryption", None)
        port = esc(ctx.get("port", ""))
        auth_method = esc(ctx.get("auth_method", ""))
        encrypt = esc(ctx.get("encrypt", ""))
        trust_server_certificate = esc(ctx.get("trust_server_certificate", ""))
        driver = esc(ctx.get("driver", ""))

        def yn(val: object) -> str:
            if val is None or val == "":
                return "-"
            try:
                return "Yes" if int(val) == 1 else "No"
            except Exception:
                return esc(val)

        auth_mode = "-"
        try:
            auth_mode = "Windows only" if int(integrated_only) == 1 else "Mixed"
        except Exception:
            pass

        fe_text = "-"
        try:
            fe_text = "Enabled" if int(force_encryption) == 1 else "Disabled"
        except Exception:
            pass

        surface_area_rows = ctx.get("surface_area", []) or []
        surface_area_html = ""
        if isinstance(surface_area_rows, list) and surface_area_rows:
            rows_html = []
            for r in surface_area_rows:
                name = esc(getattr(r, "get", lambda _k, _d=None: None)("config_name", "") or "")
                v = getattr(r, "get", lambda _k, _d=None: None)("value_in_use", None)
                pill = "<span class='pill off'>OFF</span>"
                try:
                    pill = "<span class='pill on'>ON</span>" if int(v) == 1 else "<span class='pill off'>OFF</span>"
                except Exception:
                    pill = f"<span class='pill neutral'>{esc(v)}</span>"
                rows_html.append(f"<tr><td>{name}</td><td>{pill}</td></tr>")
            surface_area_html = (
                "<h3 class='sub'>Surface Area</h3>"
                "<table class='t'>"
                "<thead><tr><th>Setting</th><th>Status</th></tr></thead>"
                "<tbody>"
                + "\n".join(rows_html)
                + "</tbody></table>"
            )

        issues_html = "\n".join(issue_row(i) for i in (summary.issues or []))
        if not issues_html:
            issues_html = "<div class='ok'>No security issues found.</div>"

        total_logins = summary.sql_logins + summary.windows_logins

        # Logins table (top 30, consistent with UI)
        logins = summary.logins or []
        login_rows = []
        for l in logins[:30]:
            if l.is_disabled:
                status = "Disabled"
            elif l.is_locked:
                status = "Locked"
            elif l.is_expired:
                status = "Expired"
            else:
                status = "Active"

            password_last_set = getattr(l, "password_last_set", None)
            password_last_set_txt = password_last_set.strftime("%Y-%m-%d %H:%M:%S") if password_last_set else ""

            bad_pw_time = getattr(l, "bad_password_time", None)
            bad_pw_time_txt = bad_pw_time.strftime("%Y-%m-%d %H:%M:%S") if bad_pw_time else ""

            login_rows.append(
                "<tr>"
                f"<td>{esc(l.name)}</td>"
                f"<td>{esc(l.login_type)}</td>"
                f"<td>{esc(status)}</td>"
                f"<td>{esc(password_last_set_txt)}</td>"
                f"<td style='text-align:right'>{esc(l.bad_password_count)}</td>"
                f"<td>{esc(bad_pw_time_txt)}</td>"
                "</tr>"
            )

        logins_html = (
            "<div class='ok'>No logins found.</div>"
            if not login_rows
            else (
                "<table class='t'>"
                "<thead><tr>"
                "<th>Login</th><th>Type</th><th>Status</th><th>Password Last Set</th>"
                "<th>Bad PW</th><th>Bad PW Time</th>"
                "</tr></thead>"
                "<tbody>"
                + "\n".join(login_rows)
                + "</tbody></table>"
            )
        )
        logins_note = ""
        if len(logins) > 30:
            logins_note = f"<div class='note'>Showing first 30 of {len(logins)} logins.</div>"

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Security Audit Report</title>
  <style>
    :root {{
      --bg: {Colors.BACKGROUND};
      --surface: {Colors.SURFACE};
      --border: {Colors.BORDER};
      --text: {Colors.TEXT_PRIMARY};
      --muted: {Colors.TEXT_SECONDARY};
      --primary: {Colors.PRIMARY};
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
      margin-bottom: 16px;
    }}
    .header h1 {{
      margin: 0;
      font-size: 22px;
    }}
    .header .ts {{
      color: var(--muted);
      font-size: 12px;
    }}
    .tabs {{
      display: flex;
      gap: 8px;
      margin: 10px 0 0;
    }}
    .tab {{
      cursor: pointer;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 600;
    }}
    .tab.active {{
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.03);
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
      margin: 14px 0 18px;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
    }}
    .card .k {{
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }}
    .card .v {{
      font-size: 18px;
      font-weight: 700;
    }}
    .section {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 14px;
      margin-bottom: 14px;
    }}
    .section h2 {{
      margin: 0 0 10px;
      font-size: 14px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .issue {{
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 12px;
      margin: 10px 0;
      background: #ffffff;
    }}
    .meta {{
      display: flex;
      gap: 8px;
      align-items: center;
      margin-bottom: 6px;
    }}
    .risk {{
      color: #fff;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 999px;
    }}
    .cat {{
      color: var(--muted);
      font-size: 12px;
    }}
    .title {{
      font-weight: 700;
      margin: 2px 0 4px;
    }}
    .desc {{
      color: #334155;
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .details {{
      color: #475569;
      font-size: 12px;
      margin: 6px 0;
      padding-left: 8px;
      border-left: 3px solid var(--border);
    }}
    .rec {{
      margin-top: 6px;
      color: #065f46;
      font-size: 12px;
      font-weight: 600;
    }}
    .ok {{
      color: #065f46;
      font-weight: 700;
      padding: 10px 0;
    }}
    .note {{
      color: var(--muted);
      font-size: 12px;
      margin-top: 8px;
    }}
    .kv {{
      display: grid;
      grid-template-columns: 170px 1fr;
      gap: 6px 10px;
      font-size: 13px;
    }}
    .kv .k {{
      color: var(--muted);
    }}
    .t {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      font-size: 13px;
    }}
    .t th {{
      text-align: left;
      background: #f8fafc;
      color: #334155;
      font-size: 12px;
      padding: 10px 10px;
      border-bottom: 1px solid var(--border);
    }}
    .t td {{
      padding: 9px 10px;
      border-bottom: 1px solid #eef2f7;
      color: #0f172a;
      vertical-align: top;
    }}
    .t tr:last-child td {{
      border-bottom: none;
    }}
    .sub {{
      margin: 14px 0 10px;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .pill {{
      display: inline-block;
      padding: 2px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .02em;
    }}
    .pill.on {{
      background: #fee2e2;
      color: #991b1b;
      border: 1px solid #fecaca;
    }}
    .pill.off {{
      background: #dcfce7;
      color: #065f46;
      border: 1px solid #bbf7d0;
    }}
    .pill.neutral {{
      background: #e2e8f0;
      color: #0f172a;
      border: 1px solid #cbd5e1;
    }}
    @media (max-width: 900px) {{
      .cards {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
  </style>
  <script>
    function setTab(id) {{
      const tabs = document.querySelectorAll('.tab');
      const panels = document.querySelectorAll('[data-panel]');
      tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === id));
      panels.forEach(p => p.style.display = (p.dataset.panel === id ? 'block' : 'none'));
    }}
    window.addEventListener('DOMContentLoaded', () => setTab('summary'));
  </script>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <h1>Security Audit Report</h1>
      <div class="ts">Generated: {esc(ts)}</div>
    </div>

    <div class="tabs">
      <button class="tab" data-tab="summary" onclick="setTab('summary')">Summary</button>
      <button class="tab" data-tab="issues" onclick="setTab('issues')">Issues</button>
      <button class="tab" data-tab="logins" onclick="setTab('logins')">Logins</button>
    </div>

    <div class="cards">
      <div class="card"><div class="k">Critical</div><div class="v">{esc(summary.critical_count)}</div></div>
      <div class="card"><div class="k">High</div><div class="v">{esc(summary.high_count)}</div></div>
      <div class="card"><div class="k">Medium</div><div class="v">{esc(summary.medium_count)}</div></div>
      <div class="card"><div class="k">Low</div><div class="v">{esc(summary.low_count)}</div></div>
      <div class="card"><div class="k">Total Logins</div><div class="v">{esc(total_logins)}</div></div>
      <div class="card"><div class="k">Sysadmins</div><div class="v">{esc(summary.sysadmin_count)}</div></div>
    </div>

    <div class="section" data-panel="summary">
      <h2>Summary</h2>
      <div class="kv">
        <div class="k">Server</div><div>{server_name or '-'}</div>
        <div class="k">Server (SERVERPROPERTY)</div><div>{esc(ctx.get("server_name_prop", "")) or '-'}</div>
        <div class="k">Machine</div><div>{machine_name or '-'}</div>
        <div class="k">Instance</div><div>{instance_name or '-'}</div>
        <div class="k">Database</div><div>{database_name or '-'}</div>
        <div class="k">Edition</div><div>{edition or '-'}</div>
        <div class="k">Engine Edition</div><div>{engine_edition or '-'}</div>
        <div class="k">Version</div><div>{product_version or '-'}</div>
        <div class="k">Product Level</div><div>{product_level or '-'}</div>
        <div class="k">Update Level</div><div>{update_level or '-'}</div>
        <div class="k">Update Ref</div><div>{update_reference or '-'}</div>
        <div class="k">Collation</div><div>{collation or '-'}</div>
        <div class="k">Clustered</div><div>{yn(is_clustered)}</div>
        <div class="k">HADR Enabled</div><div>{yn(is_hadr_enabled)}</div>
        <div class="k">Auth Mode</div><div>{esc(auth_mode)}</div>
        <div class="k">Force Encryption</div><div>{esc(fe_text)}</div>
        <div class="k">Connection Auth</div><div>{auth_method or '-'}</div>
        <div class="k">Port</div><div>{port or '-'}</div>
        <div class="k">Driver</div><div>{driver or '-'}</div>
        <div class="k">Encrypt (client)</div><div>{encrypt or '-'}</div>
        <div class="k">Trust Server Cert</div><div>{trust_server_certificate or '-'}</div>
        <div class="k">Collected At</div><div>{esc(ts)}</div>
      </div>
      {surface_area_html}
    </div>

    <div class="section" data-panel="issues">
      <h2>Issues</h2>
      {issues_html}
    </div>

    <div class="section" data-panel="logins">
      <h2>Logins (Top 30)</h2>
      {logins_html}
      {logins_note}
    </div>
  </div>
</body>
</html>
"""
    
    def _update_issues_list(self, issues: List[SecurityIssue]):
        """Update the issues list"""
        # Clear existing
        while self._issues_layout.count() > 1:  # Keep stretch
            item = self._issues_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not issues:
            success = QLabel("No security issues found!")
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
