"""
Object Explorer View - Browse and analyze database objects (SP, View, Function, etc.)
GUI-05 Modern Design Style
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QLineEdit, QListWidget, QTabWidget, QSplitter,
    QLabel, QFrame, QGroupBox, QFormLayout,
    QMenu, QListWidgetItem,
    QDialog, QTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QAction
from app.ui.views.base_view import BaseView
from app.ui.theme import Colors
from app.database.connection import get_connection_manager
from app.core.logger import get_logger
from app.ui.components.code_editor import CodeEditor

logger = get_logger('ui.explorer')


class ObjectExplorerView(BaseView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
    @property
    def view_title(self) -> str:
        return "Object Explorer"
    
    def on_show(self) -> None:
        """View gösterildiğinde"""
        if not self._is_initialized:
            return
        self._load_databases()
    
    def refresh(self) -> None:
        """Dışarıdan çağrılabilir refresh metodu (database değiştiğinde)"""
        if not self._is_initialized:
            return
        self._load_databases()
        self._load_objects()

    def _setup_ui(self) -> None:
        """Sayfa düzenini oluşturur - GUI-05 Style"""
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        # Main container
        main_widget = QWidget()
        main_widget.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(12)
        
        # Title
        title = QLabel("Object Explorer")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 20px; 
            font-weight: 700;
            background: transparent;
        """)
        main_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Explore database objects and properties.")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; background: transparent;")
        main_layout.addWidget(subtitle)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{ 
                background-color: transparent;
                width: 4px;
            }}
        """)
        
        # ═══════════════════════════════════════════════════════════
        # LEFT PANEL - Filters and Objects
        # ═══════════════════════════════════════════════════════════
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_panel.setMinimumWidth(220)
        left_panel.setMaximumWidth(400)
        left_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        left_panel.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        
        # --- Filters Section ---
        filters_title = QLabel("Filters")
        filters_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
        left_layout.addWidget(filters_title)
        
        # Database filter
        db_label = QLabel("Database:")
        db_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        left_layout.addWidget(db_label)
        
        self.db_combo = QComboBox()
        self.db_combo.setMinimumWidth(150)
        self.db_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.db_combo.addItem("(None)")
        self.db_combo.setStyleSheet(self._get_combo_style())
        self.db_combo.currentIndexChanged.connect(self._on_db_changed)
        left_layout.addWidget(self.db_combo)
        
        # Object Type filter
        type_label = QLabel("Object Type:")
        type_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        left_layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(150)
        self.type_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.type_combo.addItems([
            "All Objects",
            "Stored Procedures",
            "Views",
            "Triggers",
            "Functions",
            "Tables"
        ])
        self.type_combo.setStyleSheet(self._get_combo_style())
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        left_layout.addWidget(self.type_combo)
        
        # Search filter
        search_label = QLabel("Search:")
        search_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        left_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 1px solid {Colors.PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self.search_input.textChanged.connect(self._filter_objects)
        left_layout.addWidget(self.search_input)
        
        left_layout.addSpacing(12)
        
        # --- Objects Section ---
        objects_title = QLabel("Objects")
        objects_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
        left_layout.addWidget(objects_title)
        
        # Objects list
        self.object_list = QListWidget()
        self.object_list.setMinimumHeight(300)
        self.object_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.SURFACE};
                border: none;
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {Colors.PRIMARY}10;
            }}
            QListWidget::item:selected {{
                background-color: {Colors.PRIMARY}20;
                color: {Colors.PRIMARY};
            }}
        """)
        self.object_list.itemClicked.connect(self._on_object_selected)
        self.object_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.object_list.customContextMenuRequested.connect(self._show_context_menu)
        left_layout.addWidget(self.object_list)
        
        left_layout.addStretch()
        
        # ═══════════════════════════════════════════════════════════
        # RIGHT PANEL - Tabs (Source Code, Statistics, Relations)
        # ═══════════════════════════════════════════════════════════
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_panel.setMinimumWidth(400)
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_panel.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Tab Widget - GUI-05 Style
        self.details_tabs = QTabWidget()
        self.details_tabs.setObjectName("ObjectExplorerTabs")
        self.details_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.details_tabs.setStyleSheet(f"""
            QTabWidget {{
                background-color: transparent;
                border: none;
            }}
            QTabBar::tab {{
                background-color: #f3f4f6;
                border: 1px solid {Colors.BORDER};
                border-bottom: 2px solid {Colors.BORDER};
                padding: 8px 16px;
                margin-right: 2px;
                font-size: 12px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.PRIMARY};
                color: #ffffff;
                border-bottom: 2px solid {Colors.PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Colors.BORDER};
            }}
            QTabWidget::pane {{
                border: 1px solid {Colors.BORDER};
                border-top: none;
                background-color: {Colors.SURFACE};
            }}
        """)
        
        # Tab 1: Source Code
        source_tab = QWidget()
        source_tab.setStyleSheet(f"background-color: {Colors.SURFACE};")
        source_layout = QVBoxLayout(source_tab)
        source_layout.setContentsMargins(12, 12, 12, 12)
        
        self.code_editor = CodeEditor()
        self.code_editor.setReadOnly(True)
        source_layout.addWidget(self.code_editor)
        self.details_tabs.addTab(source_tab, "Source Code")
        
        # Tab 2: Statistics
        stats_tab = QWidget()
        stats_tab.setStyleSheet(f"background-color: {Colors.SURFACE};")
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        
        # Stats label header
        stats_header = QLabel("Statistics")
        stats_header.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        stats_layout.addWidget(stats_header)
        
        # Statistics GroupBox
        exec_stats_group = QGroupBox("Execution Statistics (Cached Plans)")
        exec_stats_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: 600;
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {Colors.TEXT_SECONDARY};
            }}
        """)
        self.exec_stats_form = QFormLayout(exec_stats_group)
        self.exec_stats_form.setContentsMargins(12, 8, 12, 8)
        self.exec_stats_form.setSpacing(6)
        
        label_style = f"color: {Colors.TEXT_PRIMARY}; font-size: 11px;"
        
        self.stat_labels = {
            'execution_count': QLabel("0"),
            'total_cpu': QLabel("0 s"),
            'total_duration': QLabel("0 s"),
            'logical_reads': QLabel("0"),
            'logical_writes': QLabel("0"),
            'physical_reads': QLabel("0"),
            'creation_time': QLabel("N/A"),
            'last_execution': QLabel("N/A")
        }
        
        for label in self.stat_labels.values():
            label.setStyleSheet(label_style)
        
        self.exec_stats_form.addRow("Execution Count:", self.stat_labels['execution_count'])
        self.exec_stats_form.addRow("Total CPU Time:", self.stat_labels['total_cpu'])
        self.exec_stats_form.addRow("Total Duration:", self.stat_labels['total_duration'])
        self.exec_stats_form.addRow("Total Logical Reads:", self.stat_labels['logical_reads'])
        self.exec_stats_form.addRow("Total Logical Writes:", self.stat_labels['logical_writes'])
        self.exec_stats_form.addRow("Total Physical Reads:", self.stat_labels['physical_reads'])
        self.exec_stats_form.addRow("Plan Creation Time:", self.stat_labels['creation_time'])
        self.exec_stats_form.addRow("Last Execution:", self.stat_labels['last_execution'])
        
        stats_layout.addWidget(exec_stats_group)
        stats_layout.addStretch()
        
        self.details_tabs.addTab(stats_tab, "Statistics")
        
        # Tab 3: Relations
        relations_tab = QWidget()
        relations_tab.setStyleSheet(f"background-color: {Colors.SURFACE};")
        relations_layout = QVBoxLayout(relations_tab)
        relations_layout.setContentsMargins(12, 12, 12, 12)
        
        # Relations label header
        relations_header = QLabel("Relations")
        relations_header.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        relations_layout.addWidget(relations_header)
        
        # Placeholder text
        self._relations_placeholder = QLabel("Object relations will appear here...")
        self._relations_placeholder.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        relations_layout.addWidget(self._relations_placeholder)
        
        # Relations lists container
        self._relations_container = QWidget()
        self._relations_container.setVisible(False)
        relations_container_layout = QVBoxLayout(self._relations_container)
        relations_container_layout.setContentsMargins(0, 8, 0, 0)
        relations_container_layout.setSpacing(12)
        
        # ListWidget style for relations
        relations_list_style = f"""
            QListWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QListWidget::item {{
                padding: 6px 10px;
            }}
            QListWidget::item:hover {{
                background-color: {Colors.PRIMARY}15;
            }}
            QListWidget::item:selected {{
                background-color: {Colors.PRIMARY}25;
                color: {Colors.PRIMARY};
            }}
        """
        
        # Depends On GroupBox
        self.depends_on_group = QGroupBox("Depends On (Objects used by this object)")
        self.depends_on_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: 600;
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {Colors.TEXT_SECONDARY};
            }}
        """)
        depends_layout = QVBoxLayout(self.depends_on_group)
        depends_layout.setContentsMargins(8, 4, 8, 8)
        self.depends_on_list = QListWidget()
        self.depends_on_list.setStyleSheet(relations_list_style)
        self.depends_on_list.setMaximumHeight(150)
        self.depends_on_list.itemDoubleClicked.connect(self._on_relation_double_clicked)
        depends_layout.addWidget(self.depends_on_list)
        relations_container_layout.addWidget(self.depends_on_group)
        
        # Used By GroupBox
        self.used_by_group = QGroupBox("Used By (Objects using this object)")
        self.used_by_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: 600;
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {Colors.TEXT_SECONDARY};
            }}
        """)
        used_by_layout = QVBoxLayout(self.used_by_group)
        used_by_layout.setContentsMargins(8, 4, 8, 8)
        self.used_by_list = QListWidget()
        self.used_by_list.setStyleSheet(relations_list_style)
        self.used_by_list.setMaximumHeight(150)
        self.used_by_list.itemDoubleClicked.connect(self._on_relation_double_clicked)
        used_by_layout.addWidget(self.used_by_list)
        relations_container_layout.addWidget(self.used_by_group)
        
        relations_layout.addWidget(self._relations_container)
        relations_layout.addStretch()
        
        self.details_tabs.addTab(relations_tab, "Relations")
        
        right_layout.addWidget(self.details_tabs)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set stretch factors (25% left, 75% right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        main_layout.addWidget(splitter, stretch=1)
        self._main_layout.addWidget(main_widget)
    
    def _get_combo_style(self) -> str:
        """Get ComboBox style - GUI-05 style"""
        return f"""
            QComboBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
            QComboBox:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {Colors.TEXT_SECONDARY};
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                selection-background-color: {Colors.PRIMARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 8px;
                min-height: 20px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """

    def initialize(self) -> None:
        """View aktif olduğunda verileri yükle"""
        super().initialize()
        self._load_databases()
        self._load_objects()

    def _load_databases(self) -> None:
        """Bağlı olunan sunucudaki veritabanlarını listeler"""
        self.db_combo.blockSignals(True)
        self.db_combo.clear()
        self.db_combo.addItem("(None)")
        
        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection

        if not active_conn or not active_conn.is_connected:
            self.db_combo.blockSignals(False)
            return

        try:
            logger.info("Loading databases for explorer...")
            query = "SELECT name FROM sys.databases WHERE state = 0 AND name NOT IN ('model', 'tempdb') ORDER BY name"
            results = active_conn.execute_query(query)
            
            databases = [row['name'] for row in results]
            self.db_combo.addItems(databases)
            
            # Eğer aktif bir veritabanı varsa onu seç
            current_db = active_conn.profile.database
            index = self.db_combo.findText(current_db)
            if index >= 0:
                self.db_combo.setCurrentIndex(index)
            
            logger.info(f"Loaded {len(databases)} databases")
                
        except Exception as e:
            logger.error(f"Failed to load databases: {e}")
        finally:
            self.db_combo.blockSignals(False)

    def _on_db_changed(self, index: int) -> None:
        """Veritabanı değiştiğinde nesne listesini tazele"""
        self._load_objects()

    def _on_type_changed(self, index: int) -> None:
        """Nesne tipi değiştiğinde listeyi filtrele veya yeniden yükle"""
        self._load_objects()

    def _load_objects(self) -> None:
        """Seçilen veritabanındaki nesneleri yükler"""
        db_name = self.db_combo.currentText()
        if not db_name or db_name == "(None)":
            self.object_list.clear()
            return

        self.object_list.clear()
        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection

        if not active_conn or not active_conn.is_connected:
            logger.warning("No active connection, skipping object load")
            return

        try:
            # Nesne tipi filtresi
            type_filter = self.type_combo.currentText()
            type_condition = ""
            if type_filter == "Stored Procedures":
                type_condition = "AND o.type IN ('P', 'PC')"
            elif type_filter == "Views":
                type_condition = "AND o.type = 'V'"
            elif type_filter == "Functions":
                type_condition = "AND o.type IN ('FN', 'IF', 'TF', 'FS', 'FT')"
            elif type_filter == "Triggers":
                type_condition = "AND o.type = 'TR'"
            elif type_filter == "Tables":
                type_condition = "AND o.type = 'U'"
            else:  # All Objects
                type_condition = "AND o.type IN ('P', 'V', 'FN', 'IF', 'TF', 'TR', 'U')"

            query = f"""
            SELECT 
                CAST(s.name AS NVARCHAR(MAX)) as schema_name, 
                CAST(o.name AS NVARCHAR(MAX)) as object_name,
                CAST(o.type AS NVARCHAR(MAX)) as type_code,
                CAST(o.type_desc AS NVARCHAR(MAX)) as type_desc
            FROM [{db_name}].sys.objects o
            JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
            WHERE o.is_ms_shipped = 0 
            {type_condition}
            ORDER BY s.name, o.name
            """
            
            logger.info(f"Executing object load query for DB: {db_name} with filter: {type_filter}")
            results = active_conn.execute_query(query)
            
            if not results:
                logger.info(f"No objects found in {db_name} with the current filters")
                return

            # Object type icons
            type_icons = {
                'P': '🔷',   # Stored Procedure
                'PC': '🔷',  # CLR Stored Procedure
                'V': '🔶',   # View
                'FN': '🟢',  # Scalar Function
                'IF': '🟢',  # Inline Table Function
                'TF': '🟢',  # Table Function
                'TR': '🔷',  # Trigger
                'U': '📋',   # Table
            }

            for row in results:
                type_code = row.get('type_code', '').strip()
                icon = type_icons.get(type_code, '⚪')
                display_name = f"{icon} {row['schema_name']}.{row['object_name']}"
                
                item = QListWidgetItem(display_name)
                # Store clean name without icon for queries
                item.setData(Qt.ItemDataRole.UserRole, f"{row['schema_name']}.{row['object_name']}")
                self.object_list.addItem(item)
                
            logger.info(f"Successfully loaded {len(results)} objects for {db_name}")
            
        except Exception as e:
            logger.error(f"Failed to load objects from {db_name}: {e}")

    def _filter_objects(self, text: str) -> None:
        """Listedeki nesneleri arama metnine göre filtreler"""
        search_terms = text.lower().split()
        
        if not search_terms:
            for i in range(self.object_list.count()):
                self.object_list.item(i).setHidden(False)
            return

        for i in range(self.object_list.count()):
            item = self.object_list.item(i)
            item_text = item.text().lower()
            match = all(term in item_text for term in search_terms)
            item.setHidden(not match)

    def _on_object_selected(self, item) -> None:
        """Listeden bir nesne seçildiğinde detayları yükler"""
        full_name = item.data(Qt.ItemDataRole.UserRole)
        if not full_name:
            full_name = item.text()
            # Remove icon prefix if present
            if full_name and len(full_name) > 2 and full_name[0] in '🔷🔶🟢📋⚪':
                full_name = full_name[2:].strip()
        
        db_name = self.db_combo.currentText()
        if not full_name or not db_name or db_name == "(None)":
            return

        logger.info(f"Object selected: {full_name} in {db_name}")
        self._load_object_source(db_name, full_name)
        self._load_object_stats(db_name, full_name)
        self._load_object_relations(db_name, full_name)

    def _load_object_source(self, db_name: str, full_name: str) -> None:
        """Seçilen nesnenin kaynak kodunu yükler"""
        self.code_editor.clear()
        
        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection

        if not active_conn or not active_conn.is_connected:
            return

        try:
            query = f"""
            SELECT CAST(m.definition AS NVARCHAR(MAX)) as source_code
            FROM [{db_name}].sys.sql_modules m
            JOIN [{db_name}].sys.objects o ON m.object_id = o.object_id
            JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
            WHERE s.name + '.' + o.name = '{full_name}'
            """
            
            results = active_conn.execute_query(query)
            if results and results[0]['source_code']:
                self.code_editor.set_text(results[0]['source_code'])
            else:
                self.code_editor.set_text("-- Source code not available for this object type.")
                
        except Exception as e:
            logger.error(f"Failed to load source code for {full_name}: {e}")
            self.code_editor.set_text(f"-- Error loading source code: {e}")

    def _load_object_stats(self, db_name: str, full_name: str) -> None:
        """Seçilen nesnenin çalışma istatistiklerini yükler"""
        # Reset stats
        for key, label in self.stat_labels.items():
            if key in ['creation_time', 'last_execution']:
                label.setText("N/A")
            elif key in ['total_cpu', 'total_duration']:
                label.setText("0 s")
            else:
                label.setText("0")

        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection

        if not active_conn or not active_conn.is_connected:
            return

        try:
            query = f"""
            SELECT 
                SUM(qs.execution_count) as execution_count,
                SUM(qs.total_worker_time)/1000000.0 AS total_cpu_seconds,
                SUM(qs.total_elapsed_time)/1000000.0 AS total_duration_seconds,
                SUM(qs.total_logical_reads) as total_logical_reads,
                SUM(qs.total_logical_writes) as total_logical_writes,
                SUM(qs.total_physical_reads) as total_physical_reads,
                MIN(qs.creation_time) as creation_time,
                MAX(qs.last_execution_time) as last_execution_time
            FROM [{db_name}].sys.dm_exec_query_stats qs
            CROSS APPLY [{db_name}].sys.dm_exec_sql_text(qs.sql_handle) st
            WHERE st.objectid = OBJECT_ID('[{db_name}].{full_name}')
            AND st.dbid = DB_ID('{db_name}')
            """
            
            results = active_conn.execute_query(query)
            
            if results and results[0]['execution_count'] is not None:
                r = results[0]
                self.stat_labels['execution_count'].setText(f"{r['execution_count']:,}")
                self.stat_labels['total_cpu'].setText(f"{r['total_cpu_seconds']:.2f} s")
                self.stat_labels['total_duration'].setText(f"{r['total_duration_seconds']:.2f} s")
                self.stat_labels['logical_reads'].setText(f"{r['total_logical_reads']:,}")
                self.stat_labels['logical_writes'].setText(f"{r['total_logical_writes']:,}")
                self.stat_labels['physical_reads'].setText(f"{r['total_physical_reads']:,}")
                self.stat_labels['creation_time'].setText(str(r['creation_time'])[:19] if r['creation_time'] else "N/A")
                self.stat_labels['last_execution'].setText(str(r['last_execution_time'])[:19] if r['last_execution_time'] else "N/A")
            else:
                logger.info(f"No execution stats found in cache for {full_name}")
                
        except Exception as e:
            logger.error(f"Failed to load stats for {full_name}: {e}")

    def _get_object_type_short(self, type_desc: str) -> str:
        """Obje tipinin kısa açıklamasını döndürür"""
        type_mapping = {
            'SQL_STORED_PROCEDURE': 'SP',
            'CLR_STORED_PROCEDURE': 'CLR SP',
            'VIEW': 'View',
            'SQL_SCALAR_FUNCTION': 'Scalar Func',
            'SQL_TABLE_VALUED_FUNCTION': 'Table Func',
            'SQL_INLINE_TABLE_VALUED_FUNCTION': 'Inline Func',
            'USER_TABLE': 'Table',
            'SQL_TRIGGER': 'Trigger',
            'OBJECT_OR_COLUMN': 'Table/Column',
        }
        
        if type_desc and type_desc.upper() in type_mapping:
            return type_mapping[type_desc.upper()]
        return type_desc or 'Unknown'

    def _load_object_relations(self, db_name: str, full_name: str) -> None:
        """Seçilen nesnenin bağımlılıklarını yükler"""
        self.depends_on_list.clear()
        self.used_by_list.clear()

        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection

        if not active_conn or not active_conn.is_connected:
            self._relations_placeholder.setVisible(True)
            self._relations_container.setVisible(False)
            return

        try:
            # 1. Depends On
            query_depends = f"""
            SELECT DISTINCT
                ISNULL(referenced_schema_name, 'dbo') as schema_name,
                referenced_entity_name as object_name,
                referenced_class_desc as type
            FROM [{db_name}].sys.dm_sql_referenced_entities ('{full_name}', 'OBJECT')
            WHERE referenced_entity_name IS NOT NULL
            """
            
            # 2. Used By
            query_used_by = f"""
            SELECT DISTINCT
                OBJECT_SCHEMA_NAME(referencing_id, DB_ID('{db_name}')) as schema_name,
                OBJECT_NAME(referencing_id, DB_ID('{db_name}')) as object_name,
                o.type_desc as type
            FROM [{db_name}].sys.dm_sql_referencing_entities ('{full_name}', 'OBJECT') re
            JOIN [{db_name}].sys.objects o ON re.referencing_id = o.object_id
            WHERE OBJECT_NAME(referencing_id, DB_ID('{db_name}')) IS NOT NULL
            """
            
            results_deps = active_conn.execute_query(query_depends)
            
            for row in results_deps:
                type_short = self._get_object_type_short(row['type'])
                obj_name = f"{row['schema_name']}.{row['object_name']}"
                display = f"{obj_name}  ({type_short})"
                
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, {
                    'schema': row['schema_name'],
                    'name': row['object_name'],
                    'full_name': obj_name,
                    'type': row['type']
                })
                self.depends_on_list.addItem(item)

            results_used = active_conn.execute_query(query_used_by)
            for row in results_used:
                type_short = self._get_object_type_short(row['type'])
                obj_name = f"{row['schema_name']}.{row['object_name']}"
                display = f"{obj_name}  ({type_short})"
                
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, {
                    'schema': row['schema_name'],
                    'name': row['object_name'],
                    'full_name': obj_name,
                    'type': row['type']
                })
                self.used_by_list.addItem(item)
            
            # Show/hide placeholder
            has_relations = len(results_deps) > 0 or len(results_used) > 0
            self._relations_placeholder.setVisible(not has_relations)
            self._relations_container.setVisible(has_relations)
                
            logger.info(f"Loaded relations for {full_name}: {len(results_deps)} deps, {len(results_used)} used by")
            
        except Exception as e:
            logger.error(f"Failed to load relations for {full_name}: {e}")
            self._relations_placeholder.setVisible(True)
            self._relations_container.setVisible(False)

    def _on_relation_double_clicked(self, item) -> None:
        """Relations listesinde bir öğeye çift tıklandığında"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        db_name = self.db_combo.currentText()
        full_name = data.get('full_name', '')
        obj_type = data.get('type', '')
        
        if not db_name or not full_name or db_name == "(None)":
            return
        
        source_types = [
            'SQL_STORED_PROCEDURE', 'CLR_STORED_PROCEDURE',
            'VIEW',
            'SQL_SCALAR_FUNCTION', 'SQL_TABLE_VALUED_FUNCTION', 
            'SQL_INLINE_TABLE_VALUED_FUNCTION',
            'SQL_TRIGGER', 'CLR_TRIGGER'
        ]
        
        if obj_type and obj_type.upper() in source_types:
            self._load_object_source(db_name, full_name)
            self.details_tabs.setCurrentIndex(0)
            logger.info(f"Loaded source for related object: {full_name}")
        else:
            self.code_editor.set_text(f"-- {full_name}\n-- Type: {obj_type}\n-- This object type does not have viewable source code.")
            self.details_tabs.setCurrentIndex(0)
    
    def _show_context_menu(self, position) -> None:
        """Sağ tık context menüsünü göster"""
        item = self.object_list.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                color: {Colors.TEXT_PRIMARY};
                border-radius: 4px;
                font-size: 11px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {Colors.BORDER};
                margin: 4px 8px;
            }}
        """)
        
        # AI ile Tune Et
        ai_tune_action = QAction("🤖  AI ile Tune Et", self)
        ai_tune_action.triggered.connect(lambda: self._ai_tune_object(item))
        menu.addAction(ai_tune_action)
        
        menu.addSeparator()
        
        # Kaynak Kodu Göster
        view_source_action = QAction("📄  View Source Code", self)
        view_source_action.triggered.connect(lambda: self._on_object_selected(item))
        menu.addAction(view_source_action)
        
        # İstatistikleri Göster
        view_stats_action = QAction("📊  View Statistics", self)
        view_stats_action.triggered.connect(lambda: self._show_stats_tab(item))
        menu.addAction(view_stats_action)
        
        # İlişkileri Göster
        view_relations_action = QAction("🔗  View Relations", self)
        view_relations_action.triggered.connect(lambda: self._show_relations_tab(item))
        menu.addAction(view_relations_action)
        
        menu.exec(self.object_list.mapToGlobal(position))
    
    def _show_stats_tab(self, item) -> None:
        """Statistics tab'ına geç"""
        full_name = item.data(Qt.ItemDataRole.UserRole)
        if not full_name:
            return
        db_name = self.db_combo.currentText()
        self._load_object_stats(db_name, full_name)
        self.details_tabs.setCurrentIndex(1)
    
    def _show_relations_tab(self, item) -> None:
        """Relations tab'ına geç"""
        full_name = item.data(Qt.ItemDataRole.UserRole)
        if not full_name:
            return
        db_name = self.db_combo.currentText()
        self._load_object_relations(db_name, full_name)
        self.details_tabs.setCurrentIndex(2)
    
    def _ai_tune_object(self, item) -> None:
        """AI ile nesneyi optimize et"""
        full_name = item.data(Qt.ItemDataRole.UserRole)
        if not full_name:
            return
            
        db_name = self.db_combo.currentText()
        if not db_name or db_name == "(None)":
            return
        
        object_info = self._collect_object_info(db_name, full_name)
        
        dialog = AITuneDialog(object_info, self)
        dialog.exec()
    
    def _collect_object_info(self, db_name: str, full_name: str) -> dict:
        """Nesnenin tüm bilgilerini topla"""
        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection
        
        info = {
            'database': db_name,
            'full_name': full_name,
            'source_code': '',
            'stats': {},
            'depends_on': [],
            'used_by': [],
            'missing_indexes': [],
            'wait_stats': []
        }
        
        if not active_conn or not active_conn.is_connected:
            return info
        
        try:
            # 1. Source Code
            query_source = f"""
            SELECT CAST(m.definition AS NVARCHAR(MAX)) as source_code
            FROM [{db_name}].sys.sql_modules m
            JOIN [{db_name}].sys.objects o ON m.object_id = o.object_id
            JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
            WHERE s.name + '.' + o.name = '{full_name}'
            """
            result = active_conn.execute_query(query_source)
            if result and result[0].get('source_code'):
                info['source_code'] = result[0]['source_code']
            
            # 2. Execution Stats
            query_stats = f"""
            SELECT 
                SUM(qs.execution_count) as execution_count,
                AVG(qs.total_worker_time/NULLIF(qs.execution_count,0))/1000.0 AS avg_cpu_ms,
                AVG(qs.total_elapsed_time/NULLIF(qs.execution_count,0))/1000.0 AS avg_duration_ms,
                AVG(qs.total_logical_reads/NULLIF(qs.execution_count,0)) as avg_logical_reads,
                MAX(qs.total_worker_time/NULLIF(qs.execution_count,0))/1000.0 AS max_cpu_ms,
                MAX(qs.total_elapsed_time/NULLIF(qs.execution_count,0))/1000.0 AS max_duration_ms,
                COUNT(DISTINCT qs.plan_handle) as plan_count
            FROM [{db_name}].sys.dm_exec_query_stats qs
            CROSS APPLY [{db_name}].sys.dm_exec_sql_text(qs.sql_handle) st
            WHERE st.objectid = OBJECT_ID('[{db_name}].{full_name}')
            AND st.dbid = DB_ID('{db_name}')
            """
            result = active_conn.execute_query(query_stats)
            if result and result[0].get('execution_count'):
                info['stats'] = result[0]
            
            # 3. Missing Indexes
            query_missing = f"""
            SELECT TOP 5
                mid.equality_columns,
                mid.inequality_columns,
                mid.included_columns,
                migs.avg_user_impact,
                migs.user_seeks
            FROM sys.dm_db_missing_index_details mid
            JOIN sys.dm_db_missing_index_groups mig ON mid.index_handle = mig.index_handle
            JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
            WHERE mid.database_id = DB_ID('{db_name}')
            AND mid.statement LIKE '%' + '{full_name.split(".")[-1]}' + '%'
            ORDER BY migs.avg_user_impact * migs.user_seeks DESC
            """
            result = active_conn.execute_query(query_missing)
            if result:
                info['missing_indexes'] = result
            
            # 4. Dependencies
            query_deps = f"""
            SELECT DISTINCT
                ISNULL(referenced_schema_name, 'dbo') + '.' + referenced_entity_name as dep_name,
                referenced_class_desc as dep_type
            FROM [{db_name}].sys.dm_sql_referenced_entities ('{full_name}', 'OBJECT')
            WHERE referenced_entity_name IS NOT NULL
            """
            result = active_conn.execute_query(query_deps)
            if result:
                info['depends_on'] = result
                
        except Exception as e:
            logger.error(f"Error collecting object info: {e}")
        
        return info


class AITuneWorker(QThread):
    """AI Tune işlemi için background worker"""
    
    analysis_ready = pyqtSignal(str)
    optimized_code_ready = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, object_info: dict, mode: str = "analyze", parent=None):
        super().__init__(parent)
        self.object_info = object_info
        self.mode = mode
    
    def run(self):
        import asyncio
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                if self.mode == "analyze":
                    result = loop.run_until_complete(self._analyze())
                    self.analysis_ready.emit(result)
                else:
                    result = loop.run_until_complete(self._generate_optimized_code())
                    self.optimized_code_ready.emit(result)
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"AI Tune error: {e}")
            self.error.emit(str(e))
    
    async def _analyze(self) -> str:
        from app.ai.analysis_service import AIAnalysisService
        
        info = self.object_info
        source_code = info.get('source_code', '')
        if not source_code:
            return "-- Kaynak kod bulunamadı"

        try:
            service = AIAnalysisService()
            response = await service.analyze_sp(
                source_code=source_code,
                object_name=info.get('full_name', 'Object'),
                stats=info.get('stats'),
                missing_indexes=info.get('missing_indexes'),
                dependencies=info.get('depends_on'),
            )
            return response
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._generate_fallback_report()
    
    async def _generate_optimized_code(self) -> str:
        from app.ai.analysis_service import AIAnalysisService
        
        info = self.object_info
        source_code = info.get('source_code', '')
        
        if not source_code:
            return "-- Kaynak kod bulunamadı"
        
        try:
            service = AIAnalysisService()
            response = await service.optimize_sp(
                source_code=source_code,
                object_name=info.get('full_name', 'Object'),
                stats=info.get('stats'),
                missing_indexes=info.get('missing_indexes'),
                dependencies=info.get('depends_on'),
            )
            return response
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return self._generate_fallback_optimized_code()
    
    def _format_stats(self) -> str:
        stats = self.object_info.get('stats', {})
        if not stats:
            return "İstatistik bilgisi yok"
        
        return f"""- Execution Count: {stats.get('execution_count', 0)}
- Avg CPU: {stats.get('avg_cpu_ms', 0):.2f} ms
- Avg Duration: {stats.get('avg_duration_ms', 0):.2f} ms
- Avg Reads: {stats.get('avg_logical_reads', 0):.0f}
- Plan Count: {stats.get('plan_count', 0)}"""
    
    def _generate_fallback_optimized_code(self) -> str:
        source = self.object_info.get('source_code', '')
        if not source:
            return "-- Kaynak kod bulunamadı"
        
        optimized = f"""-- OPTIMIZED BY AI (Fallback Mode)
-- Not: AI bağlantısı olmadığı için temel optimizasyonlar uygulandı

{source}

/*
╔════════════════════════════════════════════════════════════════╗
║                    ÖNERİLEN OPTİMİZASYONLAR                    ║
╠════════════════════════════════════════════════════════════════╣
║ 1. Prosedürün başına SET NOCOUNT ON ekleyin                    ║
║ 2. SELECT * yerine sadece gerekli kolonları seçin             ║
║ 3. WHERE koşullarında index'li kolonları kullanın             ║
║ 4. Büyük tablolarda NOLOCK hint kullanmayı düşünün            ║
║ 5. TRY-CATCH ile hata yönetimi ekleyin                        ║
╚════════════════════════════════════════════════════════════════╝
*/
"""
        return optimized
    
    def _build_tune_prompt(self) -> str:
        info = self.object_info
        
        prompt = f"""## Analiz Edilecek Nesne
- **Veritabanı:** {info['database']}
- **Nesne:** {info['full_name']}

## Kaynak Kod
```sql
{info['source_code'][:5000] if info['source_code'] else 'Kaynak kod bulunamadı'}
```

## Çalışma İstatistikleri
"""
        if info['stats']:
            stats = info['stats']
            prompt += f"""- Toplam Çalışma: {stats.get('execution_count', 0):,}
- Ortalama CPU: {stats.get('avg_cpu_ms', 0):.2f} ms
- Ortalama Süre: {stats.get('avg_duration_ms', 0):.2f} ms
- Ortalama Okuma: {stats.get('avg_logical_reads', 0):,.0f}
- Plan Sayısı: {stats.get('plan_count', 0)}
"""
        else:
            prompt += "İstatistik verisi bulunamadı.\n"
        
        prompt += "\n## Eksik Index Önerileri\n"
        if info.get('missing_indexes'):
            for idx in info['missing_indexes']:
                prompt += f"""- Equality: {idx.get('equality_columns', '-')}
  Include: {idx.get('included_columns', '-')}
  Etki: %{idx.get('avg_user_impact', 0):.0f}
"""
        else:
            prompt += "Eksik index önerisi yok.\n"
        
        prompt += """
---
Lütfen detaylı analiz yap ve öneriler sun.
"""
        return prompt
    
    def _generate_fallback_report(self) -> str:
        info = self.object_info
        stats = info.get('stats', {})
        
        report = f"""# 🔧 Performans Analiz Raporu

## 📋 Nesne Bilgileri
- **Veritabanı:** {info['database']}
- **Nesne:** {info['full_name']}

## 📊 Çalışma İstatistikleri
"""
        
        if stats:
            exec_count = stats.get('execution_count', 0) or 0
            avg_cpu = stats.get('avg_cpu_ms', 0) or 0
            avg_duration = stats.get('avg_duration_ms', 0) or 0
            avg_reads = stats.get('avg_logical_reads', 0) or 0
            
            report += f"""| Metrik | Değer | Durum |
|--------|-------|-------|
| Toplam Çalışma | {exec_count:,} | {'🟢' if exec_count < 10000 else '🟡'} |
| Ortalama CPU | {avg_cpu:.2f} ms | {'🟢' if avg_cpu < 100 else '🟡' if avg_cpu < 500 else '🔴'} |
| Ortalama Süre | {avg_duration:.2f} ms | {'🟢' if avg_duration < 100 else '🟡' if avg_duration < 1000 else '🔴'} |
| Ortalama Okuma | {avg_reads:,.0f} | {'🟢' if avg_reads < 1000 else '🟡' if avg_reads < 10000 else '🔴'} |

"""
        else:
            report += "*İstatistik verisi bulunamadı.*\n\n"
        
        report += """## 💡 Genel Öneriler

1. **Index Kontrolü:** Eksik index önerilerini değerlendirin
2. **Execution Plan:** SET STATISTICS IO ON ile sorgu planını inceleyin
3. **Kod İncelemesi:** SELECT * yerine sadece gerekli kolonları seçin

*Not: Detaylı AI analizi için bir AI sağlayıcısı ayarlanmalıdır (Settings > AI / LLM).*
"""
        
        return report


class AITuneDialog(QDialog):
    """AI Tune dialog"""
    
    def __init__(self, object_info: dict, parent=None):
        super().__init__(parent)
        self.object_info = object_info
        self._optimized_code = ""
        self._log_entries = []
        self._setup_ui()
        self._start_analysis()
    
    def _setup_ui(self):
        self.setWindowTitle(f"AI Analizi: {self.object_info.get('full_name', '')}")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BACKGROUND};
            }}
            QTextEdit {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_MUTED};
            }}
            QPushButton#closeBtn {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
            }}
            QPushButton#closeBtn:hover {{
                background-color: #F1F5F9;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel(f"🤖 AI Performans Analizi: {self.object_info.get('full_name', '')}")
        title.setStyleSheet(f"color: {Colors.SECONDARY}; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Primary status pill shown in the header
        self._status_badge = QLabel("⏳ Analiz ediliyor...")
        # Alias kept for backward compatibility with older code that referenced
        # `info_badge`; prevents NameError crashes while we refactor callers.
        info_badge = self._status_badge
        self._status_badge.setStyleSheet(f"""
            background-color: {Colors.PRIMARY_LIGHT};
            color: {Colors.TEXT_SECONDARY};
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
        """)
        header_layout.addWidget(self._status_badge)
        
        layout.addLayout(header_layout)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(5)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 2px;
                background-color: {Colors.BORDER};
            }}
            QProgressBar::chunk {{
                background-color: {Colors.SECONDARY};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self._progress_bar)

        # Info box
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px dashed {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(8)
        self._info_label = QLabel("İşlem adımı: Analiz hazırlanıyor... (5%)")
        self._info_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        info_layout.addWidget(self._info_label)
        info_layout.addStretch()
        layout.addWidget(info_frame)
        
        # Result text
        result_container = QFrame()
        result_container.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        result_layout = QVBoxLayout(result_container)
        result_layout.setContentsMargins(12, 8, 12, 12)
        result_layout.setSpacing(8)

        result_title = QLabel("📄 Analiz Sonucu")
        result_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; font-size: 12px;")
        result_layout.addWidget(result_title)

        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setPlaceholderText("AI analizi hazırlanıyor, lütfen bekleyin...")
        self._result_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                font-size: 13px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        result_layout.addWidget(self._result_text)
        layout.addWidget(result_container, 1)

        # Log panel
        log_container = QFrame()
        log_container.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(12, 8, 12, 12)
        log_layout.setSpacing(8)

        log_header = QHBoxLayout()
        log_title = QLabel("📋 İşlem Logları")
        log_title.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 11px;")
        log_header.addWidget(log_title)
        log_header.addStretch()
        clear_btn = QPushButton("Temizle")
        clear_btn.setFixedHeight(22)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #94a3b8;
            }
        """)
        clear_btn.clicked.connect(self._clear_log)
        log_header.addWidget(clear_btn)
        log_layout.addLayout(log_header)

        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setFixedHeight(120)
        self._log_area.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 11px;
                color: #e2e8f0;
            }
        """)
        log_layout.addWidget(self._log_area)
        layout.addWidget(log_container)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._refresh_btn = QPushButton("🔄 Yeniden Analiz Et")
        self._refresh_btn.clicked.connect(self._start_analysis)
        btn_layout.addWidget(self._refresh_btn)
        
        self._optimize_btn = QPushButton("✨ Kod Optimize Et")
        self._optimize_btn.clicked.connect(self._generate_optimized_code)
        btn_layout.addWidget(self._optimize_btn)
        
        btn_layout.addStretch()

        self._save_btn = QPushButton("💾 Raporu Kaydet")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_report)
        btn_layout.addWidget(self._save_btn)

        self._copy_btn = QPushButton("📋 Metni Kopyala")
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._copy_report)
        btn_layout.addWidget(self._copy_btn)

        self._view_btn = QPushButton("📄 Raporu Gör")
        self._view_btn.setEnabled(False)
        self._view_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._view_btn)
        
        self._close_btn = QPushButton("Kapat")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._close_btn)
        
        layout.addLayout(btn_layout)
        
        # Status
        self._status_label = QLabel("Hazır")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self._status_label)
    
    def _start_analysis(self):
        self._refresh_btn.setEnabled(False)
        self._status_label.setText("🔄 Analiz yapılıyor...")
        self._result_text.setMarkdown("## ⏳ Analiz Yapılıyor...\n\nBu işlem birkaç saniye sürebilir...")
        self._progress_bar.setValue(20)
        self._info_label.setText("İşlem adımı: Analiz hazırlanıyor... (20%)")
        self._status_badge.setText("⏳ Analiz ediliyor...")
        self._add_log("Sorgu bağlamı hazırlanıyor...")
        
        self._analysis_worker = AITuneWorker(self.object_info, mode="analyze")
        self._analysis_worker.analysis_ready.connect(self._on_analysis_complete)
        self._analysis_worker.error.connect(self._on_error)
        self._analysis_worker.start()
    
    def _generate_optimized_code(self):
        self._optimize_btn.setEnabled(False)
        self._status_label.setText("🔄 Kod optimize ediliyor...")
        self._progress_bar.setValue(35)
        self._info_label.setText("İşlem adımı: Kod optimizasyonu hazırlanıyor... (35%)")
        self._add_log("Kod optimizasyonu hazırlanıyor...")
        
        self._optimize_worker = AITuneWorker(self.object_info, mode="optimize")
        self._optimize_worker.optimized_code_ready.connect(self._on_optimized_code_ready)
        self._optimize_worker.error.connect(self._on_error)
        self._optimize_worker.start()
    
    def _on_analysis_complete(self, result: str):
        self._result_text.setMarkdown(result)
        self._refresh_btn.setEnabled(True)
        self._status_label.setText("✅ Analiz tamamlandı")
        self._progress_bar.setValue(100)
        self._info_label.setText("İşlem adımı: Analiz tamamlandı! (100%)")
        self._status_badge.setText("✅ Analiz tamamlandı!")
        self._save_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)
        self._view_btn.setEnabled(True)
        self._add_log("Analiz tamamlandı.")
    
    def _on_optimized_code_ready(self, code: str):
        self._optimized_code = code
        current_text = self._result_text.toMarkdown()
        self._result_text.setMarkdown(current_text + f"\n\n## ✨ Optimize Edilmiş Kod\n\n```sql\n{code}\n```")
        self._optimize_btn.setEnabled(True)
        self._status_label.setText("✅ Kod optimize edildi")
        self._progress_bar.setValue(100)
        self._info_label.setText("İşlem adımı: Kod optimize edildi! (100%)")
        self._status_badge.setText("✅ Analiz tamamlandı!")
        self._save_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)
        self._view_btn.setEnabled(True)
        self._add_log("Kod optimize edildi.")
    
    def _on_error(self, error: str):
        self._result_text.setMarkdown(f"## ⚠️ Hata\n\n{error}")
        self._refresh_btn.setEnabled(True)
        self._optimize_btn.setEnabled(True)
        self._status_label.setText(f"⚠️ Hata: {error}")
        self._progress_bar.setValue(0)
        self._info_label.setText(f"İşlem adımı: Hata oluştu")
        self._status_badge.setText("❌ Hata")
        self._add_log(f"Hata: {error}")

    def _add_log(self, message: str) -> None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: #94a3b8;">{message}</span>'
        self._log_entries.append(log_line)
        self._log_area.setHtml("<br>".join(self._log_entries))
        scrollbar = self._log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _clear_log(self) -> None:
        self._log_entries.clear()
        self._log_area.clear()

    def _copy_report(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._result_text.toPlainText())
        self._add_log("Sonuç panoya kopyalandı.")

    def _save_report(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from datetime import datetime
        text = self._result_text.toMarkdown()
        if not text:
            QMessageBox.information(self, "Rapor", "Kaydedilecek bir rapor bulunamadı.")
            return
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Raporu Kaydet",
            f"AI_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "HTML (*.html);;Markdown (*.md);;Text (*.txt)"
        )
        if not file_path:
            return
        try:
            if selected_filter.startswith("HTML"):
                content = self._result_text.toHtml()
            elif selected_filter.startswith("Text"):
                content = self._result_text.toPlainText()
            else:
                content = self._result_text.toMarkdown()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._add_log(f"Rapor kaydedildi: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Rapor", f"Rapor kaydedilemedi: {e}")
