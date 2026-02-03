"""
SQL Agent Jobs View - Modern Enterprise Design
"""
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QPushButton, QSplitter,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, CircleStatCard
from app.core.logger import get_logger
from app.services.jobs_service import (
    get_jobs_service,
    JobsSummary,
    Job,
    FailedJob,
    RunningJob,
)

logger = get_logger('views.jobs')


class JobCard(QFrame):
    """Card showing a single job"""
    
    def __init__(self, job: Job, parent=None):
        super().__init__(parent)
        self._job = job
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                border-left: 4px solid {self._job.status_color};
            }}
            QFrame:hover {{
                background: {Colors.BACKGROUND};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # Status indicator
        status_icon = "🔄" if self._job.is_running else (
            "✅" if self._job.last_run_status == 1 else (
            "❌" if self._job.last_run_status == 0 else "⏸️"))
        
        icon_label = QLabel(status_icon)
        icon_label.setStyleSheet("font-size: 20px; border: none;")
        layout.addWidget(icon_label)
        
        # Job info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(self._job.name)
        name_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; font-size: 13px; border: none;")
        info_layout.addWidget(name_label)
        
        # Category and status
        meta_text = f"{self._job.category}" if self._job.category else "Uncategorized"
        if not self._job.enabled:
            meta_text += " • Disabled"
        meta_label = QLabel(meta_text)
        meta_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; border: none;")
        info_layout.addWidget(meta_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Status and timing
        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        status_label = QLabel(self._job.status_text)
        status_label.setStyleSheet(f"color: {self._job.status_color}; font-weight: bold; font-size: 12px; border: none;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(status_label)
        
        # Last run or next run
        if self._job.last_run_date:
            time_text = self._format_datetime(self._job.last_run_date)
            time_label = QLabel(f"Last: {time_text}")
        elif self._job.next_run_date:
            time_text = self._format_datetime(self._job.next_run_date)
            time_label = QLabel(f"Next: {time_text}")
        else:
            time_label = QLabel("No schedule")
        
        time_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; border: none;")
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(time_label)
        
        layout.addLayout(right_layout)
    
    def _format_datetime(self, dt) -> str:
        if not dt:
            return "--"
        try:
            return dt.strftime("%m/%d %H:%M")
        except:
            return str(dt)[:16]


class FailedJobRow(QFrame):
    """Row showing a failed job"""
    
    def __init__(self, failed: FailedJob, parent=None):
        super().__init__(parent)
        self._failed = failed
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: #FEF2F2;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                border-left: 3px solid #EF4444;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Error icon
        icon = QLabel("❌")
        icon.setStyleSheet("font-size: 14px; border: none;")
        layout.addWidget(icon)
        
        # Job info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        
        name_label = QLabel(f"{self._failed.job_name} - Step {self._failed.step_id}: {self._failed.step_name}")
        name_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 500; font-size: 12px; border: none;")
        info_layout.addWidget(name_label)
        
        # Error message (truncated)
        msg = self._failed.message[:100] + "..." if len(self._failed.message) > 100 else self._failed.message
        msg_label = QLabel(msg)
        msg_label.setStyleSheet(f"color: #B91C1C; font-size: 11px; border: none;")
        msg_label.setWordWrap(True)
        info_layout.addWidget(msg_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Time
        if self._failed.run_datetime:
            try:
                time_text = self._failed.run_datetime.strftime("%H:%M")
            except:
                time_text = "--"
        else:
            time_text = "--"
        
        time_label = QLabel(time_text)
        time_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; border: none;")
        layout.addWidget(time_label)


class RunningJobRow(QFrame):
    """Row showing a running job"""
    
    def __init__(self, running: RunningJob, parent=None):
        super().__init__(parent)
        self._running = running
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: #EFF6FF;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                border-left: 3px solid #3B82F6;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Running icon
        icon = QLabel("🔄")
        icon.setStyleSheet("font-size: 14px; border: none;")
        layout.addWidget(icon)
        
        # Job info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        
        name_label = QLabel(self._running.job_name)
        name_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 500; font-size: 12px; border: none;")
        info_layout.addWidget(name_label)
        
        step_label = QLabel(f"Current: {self._running.current_step or 'Starting...'}")
        step_label.setStyleSheet(f"color: #1D4ED8; font-size: 11px; border: none;")
        info_layout.addWidget(step_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Running time
        time_label = QLabel(self._running.running_text)
        time_label.setStyleSheet(f"color: #3B82F6; font-weight: bold; font-size: 12px; border: none;")
        layout.addWidget(time_label)


class JobsView(BaseView):
    """SQL Agent Jobs view with modern enterprise design"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = get_jobs_service()
        self._summary_cards: Dict[str, QFrame] = {}
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
    
    def _setup_ui(self):
        # Title section
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side - title
        title_left = QVBoxLayout()
        title_left.setSpacing(8)
        
        title = QLabel("⚙️ SQL Agent Jobs")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_left.addWidget(title)
        
        subtitle = QLabel("Monitor and manage SQL Server Agent jobs")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        title_left.addWidget(subtitle)
        
        title_layout.addLayout(title_left)
        title_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(f"""
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
        refresh_btn.clicked.connect(self.refresh)
        title_layout.addWidget(refresh_btn)
        
        self._main_layout.addWidget(title_container)
        self._main_layout.addSpacing(12)
        
        # ═══════════════════════════════════════════════════════════════════
        # SUMMARY CARDS
        # ═══════════════════════════════════════════════════════════════════
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        
        summary_items = [
            ("total", "Total Jobs", "--", "📋", Colors.PRIMARY),
            ("enabled", "Enabled", "--", "✅", "#10B981"),
            ("running", "Running", "--", "🔄", "#3B82F6"),
            ("failed", "Failed (24h)", "--", "❌", "#EF4444"),
        ]
        
        for card_id, label, value, icon, color in summary_items:
            card = self._create_summary_card(icon, label, value, color)
            self._summary_cards[card_id] = card
            summary_layout.addWidget(card)
        
        summary_layout.addStretch()
        self._main_layout.addLayout(summary_layout)
        self._main_layout.addSpacing(12)
        
        # ═══════════════════════════════════════════════════════════════════
        # MAIN CONTENT (Split view)
        # ═══════════════════════════════════════════════════════════════════
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; }")
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Left panel - All Jobs
        left_panel = QFrame()
        left_panel.setStyleSheet(f"background: {Colors.SURFACE}; border: 1px solid {Colors.BORDER}; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Header
        jobs_header = QLabel("📋 All Jobs")
        jobs_header.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 14px; 
            font-weight: bold; 
            padding: 12px 16px;
            border-bottom: 1px solid {Colors.BORDER};
            background: transparent;
        """)
        left_layout.addWidget(jobs_header)
        
        # Jobs scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._jobs_container = QWidget()
        self._jobs_container.setStyleSheet("background: transparent;")
        self._jobs_layout = QVBoxLayout(self._jobs_container)
        self._jobs_layout.setContentsMargins(8, 8, 8, 8)
        self._jobs_layout.setSpacing(8)
        self._jobs_layout.addStretch()
        
        scroll.setWidget(self._jobs_container)
        left_layout.addWidget(scroll)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Alerts (Running + Failed)
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background: {Colors.SURFACE}; border: 1px solid {Colors.BORDER}; border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Running Jobs Section
        running_header = QLabel("🔄 Running Jobs")
        running_header.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 14px; 
            font-weight: bold; 
            padding: 12px 16px;
            border-bottom: 1px solid {Colors.BORDER};
            background: transparent;
        """)
        right_layout.addWidget(running_header)
        
        self._running_container = QWidget()
        self._running_container.setStyleSheet("background: transparent;")
        self._running_layout = QVBoxLayout(self._running_container)
        self._running_layout.setContentsMargins(0, 0, 0, 0)
        self._running_layout.setSpacing(0)
        
        right_layout.addWidget(self._running_container)
        
        # Failed Jobs Section
        failed_header = QLabel("❌ Failed Jobs (Last 24h)")
        failed_header.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 14px; 
            font-weight: bold; 
            padding: 12px 16px;
            border-bottom: 1px solid {Colors.BORDER};
            border-top: 1px solid {Colors.BORDER};
            background: transparent;
        """)
        right_layout.addWidget(failed_header)
        
        # Failed scroll
        failed_scroll = QScrollArea()
        failed_scroll.setWidgetResizable(True)
        failed_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._failed_container = QWidget()
        self._failed_container.setStyleSheet("background: transparent;")
        self._failed_layout = QVBoxLayout(self._failed_container)
        self._failed_layout.setContentsMargins(0, 0, 0, 0)
        self._failed_layout.setSpacing(0)
        
        failed_scroll.setWidget(self._failed_container)
        right_layout.addWidget(failed_scroll)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 400])
        
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
        self.refresh()
        self._refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def on_hide(self) -> None:
        """Called when view is hidden"""
        self._refresh_timer.stop()
    
    def refresh(self) -> None:
        """Refresh jobs data"""
        if not self._is_initialized:
            return
            
        if not self._service.is_connected:
            logger.debug("Jobs refresh skipped: No active connection")
            return
        
        logger.info("Refreshing jobs...")
        
        try:
            summary = self._service.get_jobs_summary()
            self._update_ui(summary)
        except Exception as e:
            logger.error(f"Error refreshing jobs: {e}")
    
    def _update_ui(self, summary: JobsSummary):
        """Update UI with new data"""
        # Update summary cards
        self._update_summary_card("total", str(summary.total_jobs))
        self._update_summary_card("enabled", str(summary.enabled_jobs))
        self._update_summary_card("running", str(summary.running_jobs))
        self._update_summary_card("failed", str(summary.failed_24h))
        
        # Update jobs list
        self._update_jobs_list(summary.jobs)
        
        # Update running jobs
        self._update_running_list(summary.running_jobs_list)
        
        # Update failed jobs
        self._update_failed_list(summary.failed_jobs)
    
    def _update_jobs_list(self, jobs: List[Job]):
        """Update the jobs list"""
        # Clear existing
        while self._jobs_layout.count() > 1:  # Keep stretch
            item = self._jobs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not jobs:
            placeholder = QLabel("No jobs found")
            placeholder.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 16px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._jobs_layout.insertWidget(0, placeholder)
            return
        
        # Add job cards
        for job in jobs:
            card = JobCard(job)
            self._jobs_layout.insertWidget(self._jobs_layout.count() - 1, card)
    
    def _update_running_list(self, running: List[RunningJob]):
        """Update running jobs list"""
        # Clear existing
        while self._running_layout.count():
            item = self._running_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not running:
            placeholder = QLabel("No jobs currently running")
            placeholder.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 16px; background: transparent;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._running_layout.addWidget(placeholder)
            return
        
        for job in running:
            row = RunningJobRow(job)
            self._running_layout.addWidget(row)
    
    def _update_failed_list(self, failed: List[FailedJob]):
        """Update failed jobs list"""
        # Clear existing
        while self._failed_layout.count():
            item = self._failed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not failed:
            placeholder = QLabel("No failed jobs in the last 24 hours")
            placeholder.setStyleSheet(f"color: #10B981; padding: 16px; background: transparent;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._failed_layout.addWidget(placeholder)
            return
        
        for job in failed[:10]:  # Show max 10
            row = FailedJobRow(job)
            self._failed_layout.addWidget(row)
        
        if len(failed) > 10:
            more = QLabel(f"... and {len(failed) - 10} more")
            more.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 8px; background: transparent;")
            more.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._failed_layout.addWidget(more)
