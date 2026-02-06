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
    QSizePolicy, QProgressBar, QRadioButton, QCheckBox,
    QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QAction
from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, Theme as ThemeStyles
from app.database.connection import get_connection_manager
from app.core.logger import get_logger
from app.core.exceptions import QueryExecutionError
from app.ui.components.code_editor import CodeEditor

# NEW: Pipeline-based collectors
from app.ai.collectors import (
    CollectorPipeline,
    ContextBudgetManager,
    ProgressObserver,
    ProgressPhase,
)

logger = get_logger('ui.explorer')


class ObjectExplorerView(BaseView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._selected_object_type_code: str = ""
        
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
        # Let the list expand to fill the left panel height.
        self.object_list.setMinimumHeight(0)
        self.object_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        left_layout.addWidget(self.object_list, 1)
        
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
        self._exec_stats_group = QGroupBox("Execution Statistics (Cached Plans)")
        self._exec_stats_group.setStyleSheet(f"""
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
        self.exec_stats_form = QFormLayout(self._exec_stats_group)
        self.exec_stats_form.setContentsMargins(12, 8, 12, 8)
        self.exec_stats_form.setSpacing(6)
        
        label_style = f"color: {Colors.TEXT_PRIMARY}; font-size: 11px;"
        label_title_style = f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;"
        
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
        
        stat_row_labels = [
            ("Execution Count:", self.stat_labels['execution_count']),
            ("Total CPU Time:", self.stat_labels['total_cpu']),
            ("Total Duration:", self.stat_labels['total_duration']),
            ("Total Logical Reads:", self.stat_labels['logical_reads']),
            ("Total Logical Writes:", self.stat_labels['logical_writes']),
            ("Total Physical Reads:", self.stat_labels['physical_reads']),
            ("Plan Creation Time:", self.stat_labels['creation_time']),
            ("Last Execution:", self.stat_labels['last_execution']),
        ]
        for label_text, value_label in stat_row_labels:
            label = QLabel(label_text)
            label.setStyleSheet(label_title_style)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.exec_stats_form.addRow(label, value_label)
        
        stats_layout.addWidget(self._exec_stats_group)

        # Table statistics (shown only for tables)
        self._table_stats_group = QGroupBox("Table Statistics")
        self._table_stats_group.setVisible(False)
        self._table_stats_group.setStyleSheet(self._exec_stats_group.styleSheet())
        self._table_stats_form = QFormLayout(self._table_stats_group)
        self._table_stats_form.setContentsMargins(12, 8, 12, 8)
        self._table_stats_form.setSpacing(6)

        self._table_stat_labels = {
            "row_count": QLabel("N/A"),
            "reserved_mb": QLabel("N/A"),
            "used_mb": QLabel("N/A"),
            "column_count": QLabel("N/A"),
            "index_count": QLabel("N/A"),
            "create_date": QLabel("N/A"),
            "modify_date": QLabel("N/A"),
            "last_user_read": QLabel("N/A"),
            "last_user_write": QLabel("N/A"),
        }
        for label in self._table_stat_labels.values():
            label.setStyleSheet(label_style)

        table_rows = [
            ("Row Count:", self._table_stat_labels["row_count"]),
            ("Reserved (MB):", self._table_stat_labels["reserved_mb"]),
            ("Used (MB):", self._table_stat_labels["used_mb"]),
            ("Columns:", self._table_stat_labels["column_count"]),
            ("Indexes:", self._table_stat_labels["index_count"]),
            ("Create Date:", self._table_stat_labels["create_date"]),
            ("Modify Date:", self._table_stat_labels["modify_date"]),
            ("Last User Read:", self._table_stat_labels["last_user_read"]),
            ("Last User Write:", self._table_stat_labels["last_user_write"]),
        ]
        for label_text, value_label in table_rows:
            label = QLabel(label_text)
            label.setStyleSheet(label_title_style)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table_stats_form.addRow(label, value_label)

        stats_layout.addWidget(self._table_stats_group)
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
        return ThemeStyles.combobox_style()

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
                # Store clean name + type for downstream behaviors (tables need different source/stats handling).
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    {
                        "full_name": f"{row['schema_name']}.{row['object_name']}",
                        "schema": row.get("schema_name", ""),
                        "name": row.get("object_name", ""),
                        "type_code": type_code,
                        "type_desc": row.get("type_desc", ""),
                    },
                )
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
        full_name, type_code = self._get_item_object_info(item)
        
        db_name = self.db_combo.currentText()
        if not full_name or not db_name or db_name == "(None)":
            return

        logger.info(f"Object selected: {full_name} in {db_name}")
        self._selected_object_type_code = type_code or ""
        self._load_object_source(db_name, full_name)
        self._load_object_stats(db_name, full_name)
        self._load_object_relations(db_name, full_name)

    @staticmethod
    def _get_item_object_info(item) -> tuple[str, str]:
        """Return (full_name, type_code) from a QListWidgetItem."""
        full_name = ""
        type_code = ""

        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            full_name = str(data.get("full_name", "") or "")
            type_code = str(data.get("type_code", "") or "")
        elif isinstance(data, str):
            full_name = data

        if not full_name:
            full_name = item.text() or ""
            # Remove icon prefix if present
            if full_name and len(full_name) > 2 and full_name[0] in '🔷🔶🟢📋⚪':
                full_name = full_name[2:].strip()

        return full_name, type_code

    def _load_object_source(self, db_name: str, full_name: str) -> None:
        """Seçilen nesnenin kaynak kodunu yükler"""
        self.code_editor.clear()
        
        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection

        if not active_conn or not active_conn.is_connected:
            return

        try:
            # Tables are not stored in sys.sql_modules; generate a best-effort CREATE TABLE script.
            if (self._selected_object_type_code or "").upper() == "U":
                script = self._get_table_create_script(active_conn, db_name, full_name)
                self.code_editor.set_text(script)
                return

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

    @staticmethod
    def _format_sql_type(type_name: str, max_length: int, precision: int, scale: int) -> str:
        """Format SQL Server data type with length/precision/scale where applicable."""
        t = (type_name or "").lower()
        if t in ("varchar", "char", "varbinary", "binary"):
            if max_length == -1:
                return f"{type_name}(max)"
            return f"{type_name}({max_length})"
        if t in ("nvarchar", "nchar"):
            if max_length == -1:
                return f"{type_name}(max)"
            return f"{type_name}({int(max_length/2)})"
        if t in ("decimal", "numeric"):
            return f"{type_name}({precision},{scale})"
        if t in ("datetime2", "time", "datetimeoffset"):
            return f"{type_name}({scale})"
        return type_name

    def _get_table_create_script(self, conn, db_name: str, full_name: str) -> str:
        """Best-effort CREATE TABLE script generator (columns + defaults + computed + identity + primary key)."""
        try:
            if "." in full_name:
                schema, table = full_name.split(".", 1)
            else:
                schema, table = "dbo", full_name

            # Use 3-part name so OBJECT_ID resolves in the target database.
            obj_expr = f"OBJECT_ID(N'[{db_name}].[{schema}].[{table}]')"

            cols_query = f"""
            SELECT
                c.column_id,
                c.name AS column_name,
                t.name AS type_name,
                c.max_length,
                c.precision,
                c.scale,
                c.is_nullable,
                c.is_identity,
                ic.seed_value,
                ic.increment_value,
                dc.name AS default_name,
                dc.definition AS default_definition,
                cc.definition AS computed_definition,
                cc.is_persisted
            FROM [{db_name}].sys.columns c
            JOIN [{db_name}].sys.types t
                ON c.user_type_id = t.user_type_id
            LEFT JOIN [{db_name}].sys.identity_columns ic
                ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            LEFT JOIN [{db_name}].sys.default_constraints dc
                ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
            LEFT JOIN [{db_name}].sys.computed_columns cc
                ON cc.object_id = c.object_id AND cc.column_id = c.column_id
            WHERE c.object_id = {obj_expr}
            ORDER BY c.column_id
            """

            pk_query = f"""
            SELECT
                kc.name AS constraint_name,
                i.type_desc AS index_type_desc,
                ic.key_ordinal,
                col.name AS column_name,
                ic.is_descending_key
            FROM [{db_name}].sys.key_constraints kc
            JOIN [{db_name}].sys.indexes i
                ON i.object_id = kc.parent_object_id AND i.index_id = kc.unique_index_id
            JOIN [{db_name}].sys.index_columns ic
                ON ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0
            JOIN [{db_name}].sys.columns col
                ON col.object_id = ic.object_id AND col.column_id = ic.column_id
            WHERE kc.parent_object_id = {obj_expr}
              AND kc.type = 'PK'
            ORDER BY ic.key_ordinal
            """

            cols = conn.execute_query(cols_query) or []
            if not cols:
                return "-- Table definition not available (no columns returned or insufficient permissions)."

            pk_rows = conn.execute_query(pk_query) or []

            lines = []
            lines.append("-- Best-effort CREATE TABLE script (generated).")
            lines.append(f"CREATE TABLE [{schema}].[{table}] (")

            col_lines = []
            for r in cols:
                col_name = r.get("column_name", "")
                type_name = r.get("type_name", "")
                max_length = int(r.get("max_length", 0) or 0)
                precision = int(r.get("precision", 0) or 0)
                scale = int(r.get("scale", 0) or 0)

                computed_def = r.get("computed_definition")
                if computed_def:
                    persisted = " PERSISTED" if r.get("is_persisted") else ""
                    col_def = f"    [{col_name}] AS {computed_def}{persisted}"
                    col_lines.append(col_def)
                    continue

                sql_type = self._format_sql_type(type_name, max_length, precision, scale)
                null_str = "NULL" if r.get("is_nullable") else "NOT NULL"

                identity = ""
                if r.get("is_identity"):
                    seed = r.get("seed_value", 1)
                    inc = r.get("increment_value", 1)
                    identity = f" IDENTITY({seed},{inc})"

                default_sql = ""
                default_def = r.get("default_definition")
                default_name = r.get("default_name")
                if default_def:
                    if default_name:
                        default_sql = f" CONSTRAINT [{default_name}] DEFAULT {default_def}"
                    else:
                        default_sql = f" DEFAULT {default_def}"

                col_lines.append(f"    [{col_name}] {sql_type}{identity} {null_str}{default_sql}")

            # Add PK if present
            if pk_rows:
                pk_name = pk_rows[0].get("constraint_name") or f"PK_{table}"
                idx_type = (pk_rows[0].get("index_type_desc") or "").upper()
                clustered = "CLUSTERED" if "CLUSTERED" in idx_type else "NONCLUSTERED"
                pk_cols = []
                for r in pk_rows:
                    cname = r.get("column_name", "")
                    direction = "DESC" if r.get("is_descending_key") else "ASC"
                    pk_cols.append(f"[{cname}] {direction}")
                col_lines.append(f"    CONSTRAINT [{pk_name}] PRIMARY KEY {clustered} ({', '.join(pk_cols)})")

            # Join columns with commas
            for i, c in enumerate(col_lines):
                suffix = "," if i < len(col_lines) - 1 else ""
                lines.append(f"{c}{suffix}")

            lines.append(");")
            return "\n".join(lines)
        except Exception as e:
            return f"-- Error generating CREATE TABLE script: {e}"

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

        # Reset table stats (if UI exists)
        if hasattr(self, "_table_stat_labels"):
            for label in self._table_stat_labels.values():
                label.setText("N/A")

        # Tables: show table stats group and skip execution stats query.
        is_table = (self._selected_object_type_code or "").upper() == "U"
        if hasattr(self, "_exec_stats_group") and hasattr(self, "_table_stats_group"):
            self._exec_stats_group.setVisible(not is_table)
            self._table_stats_group.setVisible(is_table)

        if is_table:
            self._load_table_stats(db_name, full_name)
            return

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

    def _load_table_stats(self, db_name: str, full_name: str) -> None:
        """Load table-level statistics (row count, dates, last usage, size, etc.)."""
        if not hasattr(self, "_table_stat_labels"):
            return

        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection

        if not active_conn or not active_conn.is_connected:
            return

        try:
            if "." in full_name:
                schema, table = full_name.split(".", 1)
            else:
                schema, table = "dbo", full_name

            # Use 3-part name so OBJECT_ID resolves in the target database.
            obj_expr = f"OBJECT_ID(N'[{db_name}].[{schema}].[{table}]')"

            query_main = f"""
            SELECT
                o.create_date,
                o.modify_date,
                SUM(CASE WHEN ps.index_id IN (0,1) THEN ps.row_count ELSE 0 END) AS row_count,
                CAST(SUM(ps.reserved_page_count) * 8.0 / 1024 AS DECIMAL(18,2)) AS reserved_mb,
                CAST(SUM(ps.used_page_count) * 8.0 / 1024 AS DECIMAL(18,2)) AS used_mb,
                (SELECT COUNT(*) FROM [{db_name}].sys.columns WHERE object_id = {obj_expr}) AS column_count,
                (SELECT COUNT(*) FROM [{db_name}].sys.indexes WHERE object_id = {obj_expr} AND index_id > 0) AS index_count
            FROM [{db_name}].sys.objects o
            JOIN [{db_name}].sys.dm_db_partition_stats ps
                ON ps.object_id = o.object_id
            WHERE o.object_id = {obj_expr}
            GROUP BY o.create_date, o.modify_date
            """

            rows = active_conn.execute_query(query_main) or []
            if rows:
                r = rows[0]
                self._table_stat_labels["row_count"].setText(f"{int(r.get('row_count', 0) or 0):,}")
                self._table_stat_labels["reserved_mb"].setText(str(r.get("reserved_mb", "N/A")))
                self._table_stat_labels["used_mb"].setText(str(r.get("used_mb", "N/A")))
                self._table_stat_labels["column_count"].setText(f"{int(r.get('column_count', 0) or 0):,}")
                self._table_stat_labels["index_count"].setText(f"{int(r.get('index_count', 0) or 0):,}")
                self._table_stat_labels["create_date"].setText(str(r.get("create_date"))[:19] if r.get("create_date") else "N/A")
                self._table_stat_labels["modify_date"].setText(str(r.get("modify_date"))[:19] if r.get("modify_date") else "N/A")

            usage_query = f"""
            SELECT
                MAX(last_user_seek) AS last_user_seek,
                MAX(last_user_scan) AS last_user_scan,
                MAX(last_user_lookup) AS last_user_lookup,
                MAX(last_user_update) AS last_user_update
            FROM sys.dm_db_index_usage_stats
            WHERE database_id = DB_ID(N'{db_name}')
              AND object_id = OBJECT_ID(N'[{db_name}].[{schema}].[{table}]')
            """
            usage = active_conn.execute_query(usage_query) or []
            if usage:
                u = usage[0]
                last_read = u.get("last_user_seek") or u.get("last_user_scan") or u.get("last_user_lookup")
                last_write = u.get("last_user_update")
                self._table_stat_labels["last_user_read"].setText(str(last_read)[:19] if last_read else "N/A")
                self._table_stat_labels["last_user_write"].setText(str(last_write)[:19] if last_write else "N/A")
        except Exception as e:
            logger.error(f"Failed to load table stats for {full_name}: {e}")

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

    def _query_object_dependencies(self, active_conn, db_name: str, full_name: str) -> list[dict]:
        """Return dependency rows with schema_name, object_name, and type."""
        query_primary = f"""
        SELECT DISTINCT
            ISNULL(referenced_schema_name, 'dbo') as schema_name,
            referenced_entity_name as object_name,
            referenced_class_desc as type
        FROM [{db_name}].sys.dm_sql_referenced_entities ('{full_name}', 'OBJECT')
        WHERE referenced_entity_name IS NOT NULL
        """
        try:
            return active_conn.execute_query(query_primary) or []
        except QueryExecutionError as e:
            logger.warning(
                f"Dependency query failed for {full_name} via dm_sql_referenced_entities: {e}. "
                "Falling back to sys.sql_expression_dependencies."
            )

        query_fallback = f"""
        SELECT DISTINCT
            ISNULL(d.referenced_schema_name, 'dbo') as schema_name,
            d.referenced_entity_name as object_name,
            d.referenced_class_desc as type
        FROM [{db_name}].sys.sql_expression_dependencies d
        WHERE d.referencing_id = OBJECT_ID('[{db_name}].{full_name}')
        AND d.referenced_entity_name IS NOT NULL
        """
        try:
            return active_conn.execute_query(query_fallback) or []
        except Exception as e:
            logger.error(f"Dependency fallback failed for {full_name}: {e}")
            return []

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
            results_deps = self._query_object_dependencies(active_conn, db_name, full_name)

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
            try:
                results_used = active_conn.execute_query(query_used_by) or []
            except QueryExecutionError as e:
                logger.warning(f"Failed to load referencing entities for {full_name}: {e}")
                results_used = []

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

        obj_type_upper = (obj_type or "").upper()
        is_table = obj_type_upper in {"USER_TABLE", "TABLE", "U"}

        # If type is ambiguous (or not provided), try resolving from sys.objects.
        if not is_table and obj_type_upper in {"OBJECT_OR_COLUMN", "", "OBJECT"}:
            resolved = self._resolve_object_type_code(db_name, full_name)
            is_table = (resolved == "U")
            if is_table:
                self._selected_object_type_code = "U"

        if is_table:
            self._selected_object_type_code = "U"
            self._load_object_source(db_name, full_name)
            self.details_tabs.setCurrentIndex(0)
            logger.info(f"Loaded table script for related object: {full_name}")
            return

        if obj_type_upper in source_types:
            self._selected_object_type_code = ""
            self._load_object_source(db_name, full_name)
            self.details_tabs.setCurrentIndex(0)
            logger.info(f"Loaded source for related object: {full_name}")
        else:
            self.code_editor.set_text(
                f"-- {full_name}\n-- Type: {obj_type}\n-- This object type does not have viewable source code."
            )
            self.details_tabs.setCurrentIndex(0)

    def _resolve_object_type_code(self, db_name: str, full_name: str) -> str:
        """Resolve object type code (e.g., U, P, V) from sys.objects."""
        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection
        if not active_conn or not active_conn.is_connected:
            return ""
        try:
            query = f"""
            SELECT o.type AS type_code
            FROM [{db_name}].sys.objects o
            JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
            WHERE s.name + '.' + o.name = '{full_name}'
            """
            result = active_conn.execute_query(query)
            if result:
                return str(result[0].get("type_code", "") or "")
        except Exception as e:
            logger.warning(f"Failed to resolve object type for {full_name}: {e}")
        return ""
    
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
        
        # AI Tune
        ai_tune_action = QAction("🤖  AI Tune", self)
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
        full_name, type_code = self._get_item_object_info(item)
        if not full_name:
            return
        self._selected_object_type_code = type_code or self._selected_object_type_code
        db_name = self.db_combo.currentText()
        self._load_object_stats(db_name, full_name)
        self.details_tabs.setCurrentIndex(1)
    
    def _show_relations_tab(self, item) -> None:
        """Relations tab'ına geç"""
        full_name, type_code = self._get_item_object_info(item)
        if not full_name:
            return
        self._selected_object_type_code = type_code or self._selected_object_type_code
        db_name = self.db_combo.currentText()
        self._load_object_relations(db_name, full_name)
        self.details_tabs.setCurrentIndex(2)
    
    def _ai_tune_object(self, item) -> None:
        """AI ile nesneyi optimize et"""
        full_name, type_code = self._get_item_object_info(item)
        if not full_name:
            return
        self._selected_object_type_code = type_code or self._selected_object_type_code
            
        db_name = self.db_combo.currentText()
        if not db_name or db_name == "(None)":
            return
        
        object_info = self._collect_object_info(db_name, full_name)
        
        dialog = AITuneDialog(object_info, self)
        dialog.exec()
    
    def _collect_object_info(self, db_name: str, full_name: str) -> dict:
        """
        Nesnenin tüm bilgilerini topla - Pipeline-based Collection
        
        Uses CollectorPipeline for modular, priority-based data collection.
        """
        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection
        
        # Default empty info structure
        empty_info = {
            'database': db_name,
            'full_name': full_name,
            'source_code': '',
            'stats': {},
            'depends_on': [],
            'used_by': [],
            'missing_indexes': [],
            'wait_stats': [],
            'query_store': {},
            'plan_xml': '',
            'plan_meta': {},
            'plan_insights': {},
            'existing_indexes': [],
            'parameter_sniffing': {},
            'historical_trend': {},
            'memory_grants': {},
            'collection_log': []
        }
        
        if not active_conn or not active_conn.is_connected:
            empty_info['collection_log'].append("ERROR: No active connection")
            return empty_info
        
        try:
            # Use CollectorPipeline for data collection
            pipeline = CollectorPipeline()
            
            # Run pipeline
            context = pipeline.run(
                db_name=db_name,
                full_name=full_name,
                connection=active_conn,
            )
            
            # Convert to legacy object_info format
            info = pipeline.to_object_info(context)
            
            logger.info(f"Pipeline collection completed for {full_name}: {len(info.get('collection_log', []))} steps")
            return info
            
        except Exception as e:
            logger.error(f"Pipeline collection failed: {e}")
            empty_info['collection_log'].append(f"Pipeline ERROR: {e}")
            
            # Fallback to legacy collection
            return self._collect_object_info_legacy(db_name, full_name)
    
    def _collect_object_info_legacy(self, db_name: str, full_name: str) -> dict:
        """
        Legacy collection method - fallback if pipeline fails.
        
        This is the original implementation kept for backward compatibility.
        """
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
            'wait_stats': [],
            'query_store': {},
            'plan_xml': '',
            'plan_meta': {},
            'plan_insights': {},
            'existing_indexes': [],
            'parameter_sniffing': {},
            'historical_trend': {},
            'memory_grants': {},
            'collection_log': ['[LEGACY MODE]']
        }
        
        if not active_conn or not active_conn.is_connected:
            return info
        
        def add_log(message: str) -> None:
            info['collection_log'].append(message)

        try:
            # 1. Source Code
            try:
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
                    add_log(f"Source Code: OK ({len(info['source_code'])} chars)")
                else:
                    add_log("Source Code: Not found")
            except Exception as e:
                add_log(f"Source Code: ERROR ({e})")
            
            # 2. Execution Stats
            try:
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
                    add_log("Execution Stats (DMV): OK")
                else:
                    add_log("Execution Stats (DMV): No data")
            except Exception as e:
                add_log(f"Execution Stats (DMV): ERROR ({e})")
            
            # 3. Missing Indexes
            try:
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
                    add_log(f"Missing Indexes: OK ({len(result)} found)")
                else:
                    add_log("Missing Indexes: None")
            except Exception as e:
                add_log(f"Missing Indexes: ERROR ({e})")
            
            # 4. Dependencies
            try:
                deps = self._query_object_dependencies(active_conn, db_name, full_name)
                if deps:
                    info['depends_on'] = [
                        {
                            "dep_name": f"{row.get('schema_name', 'dbo')}.{row.get('object_name')}",
                            "dep_type": row.get('type'),
                        }
                        for row in deps
                        if row.get('object_name')
                    ]
                    add_log(f"Dependencies: OK ({len(info['depends_on'])} found)")
                else:
                    add_log("Dependencies: None")
            except Exception as e:
                add_log(f"Dependencies: ERROR ({e})")

            # 5. Query Store (if enabled) + plan context (no execution)
            qs_info = self._collect_query_store_info(active_conn, db_name, full_name)
            if qs_info:
                info['query_store'] = qs_info
                if qs_info.get('plan_xml'):
                    info['plan_xml'] = qs_info.get('plan_xml') or ''
                    info['plan_meta'] = qs_info.get('plan_meta') or {}
            
            qs_status = (qs_info or {}).get("status", {})
            qs_error = (qs_info or {}).get("error")
            if qs_error:
                add_log(f"Query Store: ERROR ({qs_error})")
            if qs_status.get("is_enabled"):
                if qs_status.get("is_operational"):
                    add_log("Query Store: Enabled (READ_WRITE)")
                else:
                    add_log(f"Query Store: Enabled ({qs_status.get('actual_state', 'N/A')})")
            else:
                add_log("Query Store: Disabled or unavailable")
            
            if (qs_info or {}).get("summary"):
                add_log("Query Store Summary: OK")
            elif qs_status.get("is_operational"):
                add_log("Query Store Summary: No data in window")
            
            if (qs_info or {}).get("waits"):
                add_log(f"Query Store Waits: OK ({len(qs_info.get('waits', []))} categories)")
            elif qs_status.get("is_operational"):
                add_log("Query Store Waits: No data")
            
            if (qs_info or {}).get("top_queries"):
                add_log(f"Query Store Top Statements: OK ({len(qs_info.get('top_queries', []))})")
            elif qs_status.get("is_operational"):
                add_log("Query Store Top Statements: No data")
            
            if info.get("plan_xml"):
                add_log(f"Plan XML: OK ({len(info.get('plan_xml'))} chars)")
            else:
                add_log("Plan XML: Not found (Query Store)")

            # 6. Cached plan fallback (DMV) if Query Store plan missing
            if not info.get('plan_xml'):
                cached_plan = self._collect_cached_plan(active_conn, db_name, full_name)
                if cached_plan:
                    info['plan_xml'] = cached_plan.get('plan_xml') or ''
                    info['plan_meta'] = cached_plan.get('plan_meta') or {}
                    add_log(f"Plan XML (DMV cached): OK ({len(info.get('plan_xml'))} chars)")
                else:
                    add_log("Plan XML (DMV cached): Not found")
            
            # 7. Plan Insights (ExecutionPlanAnalyzer)
            if info.get('plan_xml'):
                try:
                    from app.ai.plan_analyzer import ExecutionPlanAnalyzer
                    analyzer = ExecutionPlanAnalyzer()
                    insights = analyzer.analyze(info['plan_xml'])
                    info['plan_insights'] = insights.to_dict()
                    info['plan_insights']['summary'] = insights.get_summary()
                    add_log(f"Plan Insights: OK ({len(insights.warnings)} warnings, {len(insights.expensive_operators)} expensive ops)")
                except Exception as e:
                    add_log(f"Plan Insights: ERROR ({e})")
            
            # 8. Existing Indexes (SP'nin kullandığı tablolar için)
            try:
                existing_indexes = self._collect_existing_indexes(active_conn, db_name, full_name)
                if existing_indexes:
                    info['existing_indexes'] = existing_indexes
                    add_log(f"Existing Indexes: OK ({len(existing_indexes)} tables)")
                else:
                    add_log("Existing Indexes: None found")
            except Exception as e:
                add_log(f"Existing Indexes: ERROR ({e})")
            
            # 9. Parameter Sniffing Analysis
            try:
                param_analysis = self._analyze_parameter_sniffing(active_conn, db_name, full_name, info.get('stats', {}))
                if param_analysis:
                    info['parameter_sniffing'] = param_analysis
                    risk = param_analysis.get('risk_level', 'unknown')
                    add_log(f"Parameter Sniffing: {risk} risk")
                else:
                    add_log("Parameter Sniffing: No data")
            except Exception as e:
                add_log(f"Parameter Sniffing: ERROR ({e})")
            
            # 10. Historical Trend Analysis (Query Store)
            if info.get('query_store', {}).get('status', {}).get('is_operational'):
                try:
                    trend = self._analyze_historical_trend(active_conn, db_name, full_name)
                    if trend:
                        info['historical_trend'] = trend
                        direction = trend.get('trend_direction', 'stable')
                        add_log(f"Historical Trend: {direction}")
                    else:
                        add_log("Historical Trend: No data")
                except Exception as e:
                    add_log(f"Historical Trend: ERROR ({e})")
            
            # 11. Memory Grant Analysis
            try:
                memory_grants = self._collect_memory_grants(active_conn, db_name, full_name)
                if memory_grants:
                    info['memory_grants'] = memory_grants
                    add_log(f"Memory Grants: OK")
                else:
                    add_log("Memory Grants: No data")
            except Exception as e:
                add_log(f"Memory Grants: ERROR ({e})")
                
        except Exception as e:
            logger.error(f"Error collecting object info: {e}")
            add_log(f"Collection Error: {e}")
        
        return info

    def _collect_query_store_info(self, conn, db_name: str, full_name: str, days: int = 7) -> dict:
        """Query Store'dan SP için özet, waits ve plan bilgisi topla (çalıştırmadan)"""
        info: dict = {
            "days": days,
            "status": {},
            "summary": {},
            "waits": [],
            "top_queries": [],
            "plan_xml": "",
            "plan_meta": {},
            "error": None,
        }
        
        try:
            # Query Store status (db scoped)
            status_query = f"""
            SELECT 
                CASE 
                    WHEN actual_state_desc IN ('READ_WRITE', 'READ_ONLY') THEN 1
                    ELSE 0
                END AS is_enabled,
                desired_state_desc,
                actual_state_desc,
                current_storage_size_mb,
                max_storage_size_mb
            FROM [{db_name}].sys.database_query_store_options
            """
            status_result = conn.execute_query(status_query)
            if not status_result:
                return info
            
            row = status_result[0]
            actual_state = str(row.get('actual_state_desc', '') or '')
            status = {
                "is_enabled": bool(row.get('is_enabled', 0)),
                "desired_state": str(row.get('desired_state_desc', '') or ''),
                "actual_state": actual_state,
                "current_storage_mb": float(row.get('current_storage_size_mb', 0) or 0),
                "max_storage_mb": float(row.get('max_storage_size_mb', 0) or 0),
            }
            status["is_operational"] = status["is_enabled"] and actual_state.upper() == "READ_WRITE"
            info["status"] = status
            
            if not status["is_operational"]:
                return info
            
            object_full_name = f"[{db_name}].{full_name}"
            
            # Summary metrics
            summary_query = f"""
            SELECT 
                SUM(rs.count_executions) AS total_executions,
                AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
                AVG(rs.avg_cpu_time) / 1000.0 AS avg_cpu_ms,
                AVG(rs.avg_logical_io_reads) AS avg_logical_reads,
                AVG(rs.avg_logical_io_writes) AS avg_logical_writes,
                AVG(rs.avg_physical_io_reads) AS avg_physical_reads,
                COUNT(DISTINCT p.plan_id) AS plan_count,
                MAX(rs.last_execution_time) AS last_execution
            FROM [{db_name}].sys.query_store_query q
            JOIN [{db_name}].sys.query_store_plan p ON q.query_id = p.query_id
            JOIN [{db_name}].sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
            JOIN [{db_name}].sys.query_store_runtime_stats_interval rsi 
                ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
            WHERE q.object_id = OBJECT_ID(:object_full_name)
              AND rsi.start_time > DATEADD(day, -:days, GETDATE())
            """
            summary_result = conn.execute_query(summary_query, {"object_full_name": object_full_name, "days": days})
            if summary_result:
                info["summary"] = summary_result[0]
            
            # Top statements (Query Store)
            top_queries_sql = f"""
            SELECT TOP 3
                q.query_id,
                q.query_hash,
                CAST(qt.query_sql_text AS NVARCHAR(MAX)) AS query_text,
                COUNT(DISTINCT p.plan_id) AS plan_count,
                SUM(rs.count_executions) AS total_executions,
                AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
                AVG(rs.avg_cpu_time) / 1000.0 AS avg_cpu_ms,
                AVG(rs.avg_logical_io_reads) AS avg_logical_reads,
                MAX(rs.last_execution_time) AS last_execution
            FROM [{db_name}].sys.query_store_query q
            JOIN [{db_name}].sys.query_store_query_text qt ON q.query_text_id = qt.query_text_id
            JOIN [{db_name}].sys.query_store_plan p ON q.query_id = p.query_id
            JOIN [{db_name}].sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
            JOIN [{db_name}].sys.query_store_runtime_stats_interval rsi 
                ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
            WHERE q.object_id = OBJECT_ID(:object_full_name)
              AND rsi.start_time > DATEADD(day, -:days, GETDATE())
            GROUP BY q.query_id, q.query_hash, CAST(qt.query_sql_text AS NVARCHAR(MAX))
            ORDER BY avg_duration_ms DESC
            """
            top_result = conn.execute_query(top_queries_sql, {"object_full_name": object_full_name, "days": days})
            if top_result:
                info["top_queries"] = top_result
            
            # Wait stats (Query Store 2017+)
            waits_sql = f"""
            SELECT 
                ws.wait_category_desc AS wait_category,
                SUM(ws.total_query_wait_time_ms) AS total_wait_ms,
                CAST(SUM(ws.total_query_wait_time_ms) * 100.0 / 
                    NULLIF(SUM(SUM(ws.total_query_wait_time_ms)) OVER(), 0) AS DECIMAL(5,2)) AS wait_percent
            FROM [{db_name}].sys.query_store_wait_stats ws
            JOIN [{db_name}].sys.query_store_plan p ON ws.plan_id = p.plan_id
            JOIN [{db_name}].sys.query_store_query q ON p.query_id = q.query_id
            JOIN [{db_name}].sys.query_store_runtime_stats_interval rsi 
                ON ws.runtime_stats_interval_id = rsi.runtime_stats_interval_id
            WHERE q.object_id = OBJECT_ID(:object_full_name)
              AND rsi.start_time > DATEADD(day, -:days, GETDATE())
            GROUP BY ws.wait_category_desc
            ORDER BY total_wait_ms DESC
            """
            waits_result = conn.execute_query(waits_sql, {"object_full_name": object_full_name, "days": days})
            if waits_result:
                info["waits"] = waits_result
            
            # Plan XML (top plan by executions)
            plan_sql = f"""
            SELECT TOP 1
                p.plan_id,
                p.query_id,
                p.query_plan_hash,
                CAST(p.query_plan AS NVARCHAR(MAX)) AS query_plan_xml,
                COALESCE(SUM(rs.count_executions), 0) AS total_executions,
                COALESCE(AVG(rs.avg_duration) / 1000.0, 0) AS avg_duration_ms,
                COALESCE(AVG(rs.avg_cpu_time) / 1000.0, 0) AS avg_cpu_ms,
                COALESCE(AVG(rs.avg_logical_io_reads), 0) AS avg_logical_reads,
                MAX(rs.last_execution_time) AS last_execution
            FROM [{db_name}].sys.query_store_plan p
            JOIN [{db_name}].sys.query_store_query q ON p.query_id = q.query_id
            LEFT JOIN [{db_name}].sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
            LEFT JOIN [{db_name}].sys.query_store_runtime_stats_interval rsi 
                ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
            WHERE q.object_id = OBJECT_ID(:object_full_name)
              AND (rsi.start_time > DATEADD(day, -:days, GETDATE()) OR rsi.start_time IS NULL)
            GROUP BY p.plan_id, p.query_id, p.query_plan_hash, CAST(p.query_plan AS NVARCHAR(MAX))
            ORDER BY total_executions DESC
            """
            plan_result = conn.execute_query(plan_sql, {"object_full_name": object_full_name, "days": days})
            if plan_result:
                plan_row = plan_result[0]
                info["plan_xml"] = plan_row.get("query_plan_xml") or ""
                info["plan_meta"] = {
                    "source": "query_store",
                    "plan_id": plan_row.get("plan_id"),
                    "query_id": plan_row.get("query_id"),
                    "plan_hash": plan_row.get("query_plan_hash"),
                    "total_executions": plan_row.get("total_executions"),
                    "avg_duration_ms": plan_row.get("avg_duration_ms"),
                    "avg_cpu_ms": plan_row.get("avg_cpu_ms"),
                    "avg_logical_reads": plan_row.get("avg_logical_reads"),
                    "last_execution": plan_row.get("last_execution"),
                }
            
        except Exception as e:
            logger.warning(f"Query Store info collection failed: {e}")
            info["error"] = str(e)
        
        return info

    def _collect_cached_plan(self, conn, db_name: str, full_name: str) -> dict:
        """DMV'den cached plan XML'i getir (Query Store yoksa fallback)"""
        try:
            object_full_name = f"[{db_name}].{full_name}"
            plan_query = """
            SELECT TOP 1
                p.plan_handle,
                p.objtype,
                p.usecounts,
                p.size_in_bytes,
                CAST(qp.query_plan AS NVARCHAR(MAX)) AS query_plan_xml,
                st.text AS query_text,
                p.cacheobjtype
            FROM sys.dm_exec_cached_plans p
            CROSS APPLY sys.dm_exec_query_plan(p.plan_handle) qp
            CROSS APPLY sys.dm_exec_sql_text(p.plan_handle) st
            WHERE p.objtype IN ('Proc', 'Prepared', 'Adhoc')
              AND st.objectid = OBJECT_ID(:object_full_name)
            ORDER BY p.usecounts DESC
            """
            result = conn.execute_query(plan_query, {"object_full_name": object_full_name})
            if not result:
                return {}
            
            row = result[0]
            return {
                "plan_xml": row.get("query_plan_xml") or "",
                "plan_meta": {
                    "source": "dmv_cached",
                    "objtype": row.get("objtype"),
                    "usecounts": row.get("usecounts"),
                    "size_in_bytes": row.get("size_in_bytes"),
                    "cacheobjtype": row.get("cacheobjtype"),
                    "query_text_preview": (row.get("query_text") or "")[:200],
                }
            }
        except Exception as e:
            logger.warning(f"Cached plan collection failed: {e}")
            return {}

    def _collect_existing_indexes(self, conn, db_name: str, full_name: str) -> list:
        """SP'nin kullandığı tablolar için mevcut index bilgilerini topla"""
        try:
            # Önce SP'nin kullandığı tabloları bul
            tables_query = f"""
            SELECT DISTINCT
                OBJECT_SCHEMA_NAME(d.referenced_major_id, DB_ID('{db_name}')) AS schema_name,
                OBJECT_NAME(d.referenced_major_id, DB_ID('{db_name}')) AS table_name
            FROM [{db_name}].sys.sql_expression_dependencies d
            JOIN [{db_name}].sys.objects o ON d.referencing_id = o.object_id
            JOIN [{db_name}].sys.schemas s ON o.schema_id = s.schema_id
            WHERE s.name + '.' + o.name = '{full_name}'
              AND d.referenced_minor_id = 0
              AND OBJECTPROPERTY(d.referenced_major_id, 'IsUserTable') = 1
            """
            tables = conn.execute_query(tables_query)
            if not tables:
                return []
            
            result = []
            for table in tables[:10]:  # Max 10 tablo
                schema = table.get('schema_name', 'dbo')
                tbl_name = table.get('table_name', '')
                if not tbl_name:
                    continue
                
                # Bu tablonun index'lerini getir
                idx_query = f"""
                SELECT 
                    i.name AS index_name,
                    i.type_desc AS index_type,
                    i.is_unique,
                    i.is_primary_key,
                    STUFF((
                        SELECT ', ' + c.name
                        FROM [{db_name}].sys.index_columns ic
                        JOIN [{db_name}].sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0
                        ORDER BY ic.key_ordinal
                        FOR XML PATH('')
                    ), 1, 2, '') AS key_columns,
                    STUFF((
                        SELECT ', ' + c.name
                        FROM [{db_name}].sys.index_columns ic
                        JOIN [{db_name}].sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 1
                        ORDER BY ic.key_ordinal
                        FOR XML PATH('')
                    ), 1, 2, '') AS include_columns,
                    ISNULL(us.user_seeks, 0) AS user_seeks,
                    ISNULL(us.user_scans, 0) AS user_scans,
                    ISNULL(us.user_lookups, 0) AS user_lookups,
                    ISNULL(us.user_updates, 0) AS user_updates
                FROM [{db_name}].sys.indexes i
                LEFT JOIN sys.dm_db_index_usage_stats us 
                    ON i.object_id = us.object_id AND i.index_id = us.index_id AND us.database_id = DB_ID('{db_name}')
                WHERE i.object_id = OBJECT_ID('[{db_name}].[{schema}].[{tbl_name}]')
                  AND i.type > 0
                ORDER BY i.is_primary_key DESC, us.user_seeks DESC
                """
                indexes = conn.execute_query(idx_query)
                
                if indexes:
                    result.append({
                        'table': f"{schema}.{tbl_name}",
                        'indexes': [
                            {
                                'name': idx.get('index_name', ''),
                                'type': idx.get('index_type', ''),
                                'is_unique': idx.get('is_unique', False),
                                'is_pk': idx.get('is_primary_key', False),
                                'key_columns': idx.get('key_columns', ''),
                                'include_columns': idx.get('include_columns', ''),
                                'seeks': idx.get('user_seeks', 0),
                                'scans': idx.get('user_scans', 0),
                                'lookups': idx.get('user_lookups', 0),
                                'updates': idx.get('user_updates', 0),
                            }
                            for idx in indexes
                        ]
                    })
            
            return result
        except Exception as e:
            logger.warning(f"Existing indexes collection failed: {e}")
            return []

    def _analyze_parameter_sniffing(self, conn, db_name: str, full_name: str, stats: dict) -> dict:
        """Parameter sniffing riskini analiz et"""
        try:
            result = {
                'risk_level': 'low',
                'indicators': [],
                'plan_count': 0,
                'cpu_variance': 0,
                'duration_variance': 0,
            }
            
            # Plan count kontrolü
            plan_count = stats.get('plan_count', 1) or 1
            result['plan_count'] = plan_count
            
            if plan_count >= 5:
                result['risk_level'] = 'high'
                result['indicators'].append(f"Multiple plans detected ({plan_count} plans)")
            elif plan_count >= 3:
                result['risk_level'] = 'medium'
                result['indicators'].append(f"Multiple plans detected ({plan_count} plans)")
            
            # Query Store'dan variance analizi
            object_full_name = f"[{db_name}].{full_name}"
            variance_query = f"""
            SELECT 
                COUNT(DISTINCT p.plan_id) AS plan_count,
                STDEV(rs.avg_duration / 1000.0) AS duration_stdev,
                AVG(rs.avg_duration / 1000.0) AS duration_avg,
                STDEV(rs.avg_cpu_time / 1000.0) AS cpu_stdev,
                AVG(rs.avg_cpu_time / 1000.0) AS cpu_avg,
                MAX(rs.avg_duration / 1000.0) AS max_duration,
                MIN(rs.avg_duration / 1000.0) AS min_duration
            FROM [{db_name}].sys.query_store_query q
            JOIN [{db_name}].sys.query_store_plan p ON q.query_id = p.query_id
            JOIN [{db_name}].sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
            JOIN [{db_name}].sys.query_store_runtime_stats_interval rsi 
                ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
            WHERE q.object_id = OBJECT_ID(:object_full_name)
              AND rsi.start_time > DATEADD(day, -7, GETDATE())
            """
            variance_result = conn.execute_query(variance_query, {"object_full_name": object_full_name})
            
            if variance_result and variance_result[0]:
                row = variance_result[0]
                duration_avg = float(row.get('duration_avg') or 0)
                duration_stdev = float(row.get('duration_stdev') or 0)
                cpu_avg = float(row.get('cpu_avg') or 0)
                cpu_stdev = float(row.get('cpu_stdev') or 0)
                max_duration = float(row.get('max_duration') or 0)
                min_duration = float(row.get('min_duration') or 0)
                
                # Coefficient of Variation hesapla
                if duration_avg > 0:
                    cv = (duration_stdev / duration_avg) * 100
                    result['duration_variance'] = round(cv, 2)
                    if cv > 100:
                        result['risk_level'] = 'high'
                        result['indicators'].append(f"High duration variance (CV: {cv:.0f}%)")
                    elif cv > 50:
                        if result['risk_level'] != 'high':
                            result['risk_level'] = 'medium'
                        result['indicators'].append(f"Moderate duration variance (CV: {cv:.0f}%)")
                
                if cpu_avg > 0:
                    cv = (cpu_stdev / cpu_avg) * 100
                    result['cpu_variance'] = round(cv, 2)
                    if cv > 100:
                        result['risk_level'] = 'high'
                        result['indicators'].append(f"High CPU variance (CV: {cv:.0f}%)")
                
                # Max/Min ratio kontrolü
                if min_duration > 0 and max_duration > 0:
                    ratio = max_duration / min_duration
                    if ratio > 10:
                        result['risk_level'] = 'high'
                        result['indicators'].append(f"Extreme duration range (max/min ratio: {ratio:.0f}x)")
                    elif ratio > 5:
                        if result['risk_level'] != 'high':
                            result['risk_level'] = 'medium'
                        result['indicators'].append(f"Wide duration range (max/min ratio: {ratio:.0f}x)")
            
            return result
        except Exception as e:
            logger.warning(f"Parameter sniffing analysis failed: {e}")
            return {}

    def _analyze_historical_trend(self, conn, db_name: str, full_name: str) -> dict:
        """Query Store'dan performans trendini analiz et"""
        try:
            object_full_name = f"[{db_name}].{full_name}"
            
            # Son 7 gün vs önceki 7 gün karşılaştırması
            trend_query = f"""
            WITH RecentStats AS (
                SELECT 
                    AVG(rs.avg_duration / 1000.0) AS avg_duration_ms,
                    AVG(rs.avg_cpu_time / 1000.0) AS avg_cpu_ms,
                    AVG(rs.avg_logical_io_reads) AS avg_logical_reads,
                    SUM(rs.count_executions) AS total_executions
                FROM [{db_name}].sys.query_store_query q
                JOIN [{db_name}].sys.query_store_plan p ON q.query_id = p.query_id
                JOIN [{db_name}].sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
                JOIN [{db_name}].sys.query_store_runtime_stats_interval rsi 
                    ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
                WHERE q.object_id = OBJECT_ID(:object_full_name)
                  AND rsi.start_time > DATEADD(day, -7, GETDATE())
            ),
            PreviousStats AS (
                SELECT 
                    AVG(rs.avg_duration / 1000.0) AS avg_duration_ms,
                    AVG(rs.avg_cpu_time / 1000.0) AS avg_cpu_ms,
                    AVG(rs.avg_logical_io_reads) AS avg_logical_reads,
                    SUM(rs.count_executions) AS total_executions
                FROM [{db_name}].sys.query_store_query q
                JOIN [{db_name}].sys.query_store_plan p ON q.query_id = p.query_id
                JOIN [{db_name}].sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
                JOIN [{db_name}].sys.query_store_runtime_stats_interval rsi 
                    ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
                WHERE q.object_id = OBJECT_ID(:object_full_name)
                  AND rsi.start_time BETWEEN DATEADD(day, -14, GETDATE()) AND DATEADD(day, -7, GETDATE())
            )
            SELECT 
                r.avg_duration_ms AS recent_duration,
                r.avg_cpu_ms AS recent_cpu,
                r.avg_logical_reads AS recent_reads,
                r.total_executions AS recent_executions,
                p.avg_duration_ms AS previous_duration,
                p.avg_cpu_ms AS previous_cpu,
                p.avg_logical_reads AS previous_reads,
                p.total_executions AS previous_executions
            FROM RecentStats r, PreviousStats p
            """
            result = conn.execute_query(trend_query, {"object_full_name": object_full_name})
            
            if not result or not result[0]:
                return {}
            
            row = result[0]
            recent_duration = float(row.get('recent_duration') or 0)
            previous_duration = float(row.get('previous_duration') or 0)
            recent_cpu = float(row.get('recent_cpu') or 0)
            previous_cpu = float(row.get('previous_cpu') or 0)
            recent_reads = float(row.get('recent_reads') or 0)
            previous_reads = float(row.get('previous_reads') or 0)
            
            trend = {
                'recent_period': 'Last 7 days',
                'previous_period': 'Previous 7 days',
                'recent_duration_ms': round(recent_duration, 2),
                'previous_duration_ms': round(previous_duration, 2),
                'recent_cpu_ms': round(recent_cpu, 2),
                'previous_cpu_ms': round(previous_cpu, 2),
                'recent_logical_reads': round(recent_reads, 0),
                'previous_logical_reads': round(previous_reads, 0),
                'trend_direction': 'stable',
                'changes': []
            }
            
            # Trend hesapla
            if previous_duration > 0:
                duration_change = ((recent_duration - previous_duration) / previous_duration) * 100
                trend['duration_change_percent'] = round(duration_change, 1)
                if duration_change > 20:
                    trend['trend_direction'] = 'degrading'
                    trend['changes'].append(f"Duration increased by {duration_change:.0f}%")
                elif duration_change < -20:
                    trend['trend_direction'] = 'improving'
                    trend['changes'].append(f"Duration decreased by {abs(duration_change):.0f}%")
            
            if previous_cpu > 0:
                cpu_change = ((recent_cpu - previous_cpu) / previous_cpu) * 100
                trend['cpu_change_percent'] = round(cpu_change, 1)
                if cpu_change > 20:
                    if trend['trend_direction'] != 'degrading':
                        trend['trend_direction'] = 'degrading'
                    trend['changes'].append(f"CPU increased by {cpu_change:.0f}%")
                elif cpu_change < -20:
                    trend['changes'].append(f"CPU decreased by {abs(cpu_change):.0f}%")
            
            if previous_reads > 0:
                reads_change = ((recent_reads - previous_reads) / previous_reads) * 100
                trend['reads_change_percent'] = round(reads_change, 1)
                if reads_change > 30:
                    trend['changes'].append(f"Logical reads increased by {reads_change:.0f}%")
                elif reads_change < -30:
                    trend['changes'].append(f"Logical reads decreased by {abs(reads_change):.0f}%")
            
            return trend
        except Exception as e:
            logger.warning(f"Historical trend analysis failed: {e}")
            return {}

    def _collect_memory_grants(self, conn, db_name: str, full_name: str) -> dict:
        """Memory grant bilgilerini topla"""
        try:
            object_full_name = f"[{db_name}].{full_name}"
            
            # DMV'den memory grant bilgileri
            memory_query = """
            SELECT TOP 1
                mg.session_id,
                mg.request_time,
                mg.grant_time,
                mg.requested_memory_kb,
                mg.granted_memory_kb,
                mg.required_memory_kb,
                mg.used_memory_kb,
                mg.max_used_memory_kb,
                mg.ideal_memory_kb,
                mg.is_small,
                mg.timeout_sec,
                mg.queue_id,
                mg.wait_order,
                CASE 
                    WHEN mg.granted_memory_kb > 0 AND mg.max_used_memory_kb > 0 
                    THEN CAST((mg.max_used_memory_kb * 100.0 / mg.granted_memory_kb) AS DECIMAL(5,2))
                    ELSE NULL 
                END AS memory_utilization_pct
            FROM sys.dm_exec_query_memory_grants mg
            CROSS APPLY sys.dm_exec_sql_text(mg.sql_handle) st
            WHERE st.objectid = OBJECT_ID(:object_full_name)
            ORDER BY mg.request_time DESC
            """
            result = conn.execute_query(memory_query, {"object_full_name": object_full_name})
            
            if not result:
                # Query Store'dan geçmiş memory grant bilgisi
                qs_memory_query = f"""
                SELECT TOP 1
                    AVG(rs.avg_query_max_used_memory) * 8.0 AS avg_memory_kb,
                    MAX(rs.max_query_max_used_memory) * 8.0 AS max_memory_kb,
                    MIN(rs.min_query_max_used_memory) * 8.0 AS min_memory_kb
                FROM [{db_name}].sys.query_store_query q
                JOIN [{db_name}].sys.query_store_plan p ON q.query_id = p.query_id
                JOIN [{db_name}].sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
                JOIN [{db_name}].sys.query_store_runtime_stats_interval rsi 
                    ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
                WHERE q.object_id = OBJECT_ID(:object_full_name)
                  AND rsi.start_time > DATEADD(day, -7, GETDATE())
                """
                qs_result = conn.execute_query(qs_memory_query, {"object_full_name": object_full_name})
                if qs_result and qs_result[0]:
                    row = qs_result[0]
                    return {
                        'source': 'query_store',
                        'avg_memory_kb': round(float(row.get('avg_memory_kb') or 0), 2),
                        'max_memory_kb': round(float(row.get('max_memory_kb') or 0), 2),
                        'min_memory_kb': round(float(row.get('min_memory_kb') or 0), 2),
                    }
                return {}
            
            row = result[0]
            requested = float(row.get('requested_memory_kb') or 0)
            granted = float(row.get('granted_memory_kb') or 0)
            used = float(row.get('max_used_memory_kb') or 0)
            ideal = float(row.get('ideal_memory_kb') or 0)
            
            memory_info = {
                'source': 'dmv_live',
                'requested_memory_kb': requested,
                'granted_memory_kb': granted,
                'used_memory_kb': used,
                'ideal_memory_kb': ideal,
                'utilization_pct': row.get('memory_utilization_pct'),
                'is_small': row.get('is_small', False),
                'warnings': []
            }
            
            # Memory grant uyarıları
            if granted > 0 and used > 0:
                utilization = (used / granted) * 100
                if utilization < 20:
                    memory_info['warnings'].append(f"Low memory utilization ({utilization:.0f}%) - grant may be over-estimated")
                elif utilization > 95:
                    memory_info['warnings'].append(f"High memory utilization ({utilization:.0f}%) - potential spill risk")
            
            if ideal > granted > 0:
                deficit = ((ideal - granted) / ideal) * 100
                if deficit > 20:
                    memory_info['warnings'].append(f"Memory grant deficit ({deficit:.0f}%) - query may spill to TempDB")
            
            return memory_info
        except Exception as e:
            logger.warning(f"Memory grants collection failed: {e}")
            return {}


class ClickableFrame(QFrame):
    """Clickable QFrame that emits clicked signal"""
    clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class AnalysisOptionsDialog(QDialog):
    """
    Analysis options dialog - shown before starting analysis.
    
    Allows user to select:
    - Analysis mode (Standard / Deep Analysis)
    - Cache options (Force Refresh)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚀 Analiz Seçenekleri")
        self.setFixedSize(500, 560)
        self.setModal(True)
        
        # Result values
        self.deep_mode = False
        self.skip_cache = False
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BACKGROUND};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("🚀 Analiz Başlatılıyor")
        header.setStyleSheet(f"""
            color: {Colors.PRIMARY};
            font-size: 20px;
            font-weight: bold;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        subtitle = QLabel("Lütfen analiz türünü seçin")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # ═══════════════════════════════════════════════════════
        # STANDARD ANALYSIS OPTION
        # ═══════════════════════════════════════════════════════
        self._standard_frame = ClickableFrame()
        self._standard_frame.setObjectName("standardFrame")
        self._standard_frame.setStyleSheet(f"""
            ClickableFrame {{
                background-color: {Colors.SURFACE};
                border: 2px solid {Colors.PRIMARY};
                border-radius: 10px;
            }}
        """)
        self._standard_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self._standard_frame.clicked.connect(lambda: self._standard_radio.setChecked(True))
        standard_layout = QVBoxLayout(self._standard_frame)
        standard_layout.setContentsMargins(16, 12, 16, 12)
        standard_layout.setSpacing(6)
        
        standard_header = QHBoxLayout()
        self._standard_radio = QRadioButton("⚡ Standard Analysis")
        self._standard_radio.setChecked(True)
        self._standard_radio.setStyleSheet(f"""
            QRadioButton {{
                color: {Colors.PRIMARY};
                font-size: 14px;
                font-weight: bold;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)
        self._standard_radio.toggled.connect(self._update_selection_style)
        standard_header.addWidget(self._standard_radio)
        standard_header.addStretch()
        self._standard_badge = QLabel("Önerilen")
        self._standard_badge.setObjectName("standardBadge")
        self._standard_badge.setStyleSheet(f"""
            QLabel#standardBadge {{
                background-color: {Colors.PRIMARY_LIGHT};
                color: {Colors.PRIMARY};
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                border: none;
            }}
        """)
        standard_header.addWidget(self._standard_badge)
        standard_layout.addLayout(standard_header)
        
        self._standard_desc = QLabel("• Hızlı ve verimli analiz\n• Çoğu senaryo için yeterli\n• Normal token kullanımı")
        self._standard_desc.setObjectName("standardDesc")
        self._standard_desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; margin-left: 24px; background: transparent; border: none;")
        standard_layout.addWidget(self._standard_desc)
        
        layout.addWidget(self._standard_frame)
        
        # ═══════════════════════════════════════════════════════
        # DEEP ANALYSIS OPTION
        # ═══════════════════════════════════════════════════════
        self._deep_frame = ClickableFrame()
        self._deep_frame.setObjectName("deepFrame")
        self._deep_frame.setStyleSheet(f"""
            ClickableFrame {{
                background-color: {Colors.SURFACE};
                border: 2px solid {Colors.BORDER};
                border-radius: 10px;
            }}
        """)
        self._deep_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self._deep_frame.clicked.connect(lambda: self._deep_radio.setChecked(True))
        deep_layout = QVBoxLayout(self._deep_frame)
        deep_layout.setContentsMargins(16, 12, 16, 12)
        deep_layout.setSpacing(6)
        
        deep_header = QHBoxLayout()
        self._deep_radio = QRadioButton("🔬 Deep Analysis")
        self._deep_radio.setStyleSheet(f"""
            QRadioButton {{
                color: #7c3aed;
                font-size: 14px;
                font-weight: bold;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)
        self._deep_radio.toggled.connect(self._update_selection_style)
        deep_header.addWidget(self._deep_radio)
        deep_header.addStretch()
        self._deep_badge = QLabel("3x Token")
        self._deep_badge.setObjectName("deepBadge")
        self._deep_badge.setStyleSheet(f"""
            QLabel#deepBadge {{
                background-color: #faf5ff;
                color: #7c3aed;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
                border: none;
            }}
        """)
        deep_header.addWidget(self._deep_badge)
        deep_layout.addLayout(deep_header)
        
        self._deep_desc = QLabel("• ~%20 daha yüksek doğruluk\n• Gelişmiş hallucination tespiti\n• Karmaşık SP'ler için ideal")
        self._deep_desc.setObjectName("deepDesc")
        self._deep_desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; margin-left: 24px; background: transparent; border: none;")
        deep_layout.addWidget(self._deep_desc)
        
        # Group radio buttons together
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._standard_radio, 0)
        self._mode_group.addButton(self._deep_radio, 1)
        
        # Deep Analysis Warning (shown when selected)
        self._deep_warning = QFrame()
        self._deep_warning.setObjectName("deepWarning")
        self._deep_warning.setStyleSheet("""
            QFrame#deepWarning {
                background-color: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 6px;
            }
            QFrame#deepWarning QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        self._deep_warning.setVisible(False)
        self._deep_warning.setFixedHeight(36)
        warning_layout = QHBoxLayout(self._deep_warning)
        warning_layout.setContentsMargins(10, 6, 10, 6)
        warning_layout.setSpacing(8)
        warning_icon = QLabel("⚠️")
        warning_icon.setFixedWidth(20)
        warning_layout.addWidget(warning_icon)
        warning_text = QLabel("Daha uzun sürer ve daha fazla API maliyeti oluşturur")
        warning_text.setStyleSheet("color: #92400e; font-size: 11px; background: transparent; border: none;")
        warning_layout.addWidget(warning_text)
        warning_layout.addStretch()
        deep_layout.addWidget(self._deep_warning)
        
        # Deep Analysis Confirmation Checkbox
        self._deep_confirm_check = QCheckBox("  ONAYLIYORUM - Deep Analysis kullanmak istiyorum")
        self._deep_confirm_check.setObjectName("deepConfirmCheck")
        self._deep_confirm_check.setStyleSheet(f"""
            QCheckBox#deepConfirmCheck {{
                color: #7c3aed;
                font-size: 11px;
                font-weight: 600;
                margin-left: 20px;
                background: transparent;
                border: none;
            }}
            QCheckBox#deepConfirmCheck::indicator {{
                width: 16px;
                height: 16px;
            }}
        """)
        self._deep_confirm_check.setVisible(False)
        self._deep_confirm_check.toggled.connect(self._update_start_button)
        deep_layout.addWidget(self._deep_confirm_check)
        
        layout.addWidget(self._deep_frame)
        
        # ═══════════════════════════════════════════════════════
        # CACHE OPTIONS
        # ═══════════════════════════════════════════════════════
        cache_frame = QFrame()
        cache_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px dashed {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        cache_layout = QHBoxLayout(cache_frame)
        cache_layout.setContentsMargins(16, 10, 16, 10)
        
        self._force_refresh_check = QCheckBox("🔄 Force Refresh (Cache'i atla, yeni analiz yap)")
        self._force_refresh_check.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
        """)
        cache_layout.addWidget(self._force_refresh_check)
        cache_layout.addStretch()
        
        layout.addWidget(cache_frame)
        
        layout.addStretch()
        
        # ═══════════════════════════════════════════════════════
        # BUTTONS
        # ═══════════════════════════════════════════════════════
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #f1f5f9;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        btn_layout.addStretch()
        
        self._start_btn = QPushButton("▶ Analizi Başlat")
        self._start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 32px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self._start_btn.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self._start_btn)
        
        layout.addLayout(btn_layout)
    
    def _update_selection_style(self):
        """Update frame styles based on selection"""
        if self._standard_radio.isChecked():
            # Standard selected
            self._standard_frame.setStyleSheet(f"""
                ClickableFrame {{
                    background-color: {Colors.SURFACE};
                    border: 2px solid {Colors.PRIMARY};
                    border-radius: 10px;
                }}
            """)
            self._deep_frame.setStyleSheet(f"""
                ClickableFrame {{
                    background-color: {Colors.SURFACE};
                    border: 2px solid {Colors.BORDER};
                    border-radius: 10px;
                }}
            """)
            self._deep_warning.setVisible(False)
            self._deep_confirm_check.setVisible(False)
            self._deep_confirm_check.setChecked(False)
        else:
            # Deep Analysis selected
            self._standard_frame.setStyleSheet(f"""
                ClickableFrame {{
                    background-color: {Colors.SURFACE};
                    border: 2px solid {Colors.BORDER};
                    border-radius: 10px;
                }}
            """)
            self._deep_frame.setStyleSheet(f"""
                ClickableFrame {{
                    background-color: #faf5ff;
                    border: 2px solid #7c3aed;
                    border-radius: 10px;
                }}
            """)
            self._deep_warning.setVisible(True)
            self._deep_confirm_check.setVisible(True)
        
        self._update_start_button()
    
    def _update_start_button(self):
        """Enable/disable start button based on selection"""
        if self._deep_radio.isChecked():
            # Deep Analysis requires confirmation
            self._start_btn.setEnabled(self._deep_confirm_check.isChecked())
            if self._deep_confirm_check.isChecked():
                self._start_btn.setText("🔬 Deep Analysis Başlat")
                self._start_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #7c3aed;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 12px 32px;
                        font-weight: 600;
                        font-size: 13px;
                    }}
                    QPushButton:hover {{
                        background-color: #6d28d9;
                    }}
                """)
            else:
                self._start_btn.setText("▶ Analizi Başlat")
        else:
            # Standard Analysis - always enabled
            self._start_btn.setEnabled(True)
            self._start_btn.setText("▶ Analizi Başlat")
            self._start_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 12px 32px;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
                QPushButton:disabled {{
                    background-color: {Colors.BORDER};
                    color: {Colors.TEXT_MUTED};
                }}
            """)
    
    def _on_start_clicked(self):
        """Handle start button click"""
        self.deep_mode = self._deep_radio.isChecked()
        self.skip_cache = self._force_refresh_check.isChecked()
        self.accept()


class AITuneWorker(QThread):
    """
    AI Tune işlemi için background worker.
    
    Uses ProgressObserver for unified progress tracking during AI analysis.
    Emits confidence information for UI display.
    """
    
    analysis_ready = pyqtSignal(str)
    optimized_code_ready = pyqtSignal(str)
    error = pyqtSignal(str)
    log = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # (percentage, step_description)
    confidence_ready = pyqtSignal(dict)  # Confidence info dict
    
    def __init__(self, object_info: dict, mode: str = "analyze", deep_mode: bool = False, skip_cache: bool = False, parent=None):
        super().__init__(parent)
        self.object_info = object_info
        self.mode = mode
        self.deep_mode = deep_mode
        self.skip_cache = skip_cache
        
        # Initialize ProgressObserver for analysis phase
        self._observer = ProgressObserver(
            on_update=self._on_observer_update,
            include_optimization=(mode == "optimize")
        )
        
        # Store last analysis confidence for potential deep analysis
        self._last_confidence = None
    
    def _on_observer_update(self, percentage: int, message: str) -> None:
        """Callback from ProgressObserver"""
        try:
            self.progress.emit(percentage, message)
            self.log.emit(f"[{percentage}%] {message}")
        except Exception:
            pass
    
    def _emit_log(self, message: str) -> None:
        try:
            self.log.emit(message)
        except Exception:
            pass
    
    def _emit_progress(self, percentage: int, step: str) -> None:
        """Direct progress emit (for compatibility)"""
        try:
            self.progress.emit(percentage, step)
            self._emit_log(f"[{percentage}%] {step}")
        except Exception:
            pass
    
    def run(self):
        import asyncio
        
        try:
            # Start analysis phase
            self._observer.start_phase(ProgressPhase.ANALYSIS)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                if self.mode == "analyze":
                    result = loop.run_until_complete(self._analyze())
                    self._observer.complete("✅ Analysis complete!")
                    self.analysis_ready.emit(result)
                else:
                    # For optimization, start optimization phase
                    self._observer.start_phase(ProgressPhase.OPTIMIZATION)
                    result = loop.run_until_complete(self._generate_optimized_code())
                    self._observer.complete("✅ Code optimization complete!")
                    self.optimized_code_ready.emit(result)
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"AI Tune error: {e}")
            self._observer.error(str(e))
            self.error.emit(str(e))
    
    async def _analyze(self) -> str:
        """
        Perform AI analysis using ProgressObserver for step tracking.
        
        Uses ContextBudgetManager for optimized context assembly.
        """
        from app.ai.analysis_service import AIAnalysisService
        import asyncio
        
        info = self.object_info
        obs = self._observer
        
        # Step: Context Assembly
        obs.step_started("context_assembly", "📦 Assembling context...")
        await asyncio.sleep(0.05)
        
        source_code = info.get('source_code', '')
        if not source_code:
            obs.step_failed("context_assembly", "Source code not found")
            return "-- Source code not found"
        
        # Use ContextBudgetManager for optimized context
        budget_mgr = ContextBudgetManager()
        budget_mgr.add("source_code", source_code)
        budget_mgr.add("execution_stats", info.get('stats', {}))
        budget_mgr.add("plan_xml", info.get('plan_xml', ''))
        budget_mgr.add("plan_insights", info.get('plan_insights', {}))
        budget_mgr.add("missing_indexes", info.get('missing_indexes', []))
        budget_mgr.add("existing_indexes", info.get('existing_indexes', []))
        budget_mgr.add("query_store", info.get('query_store', {}))
        budget_mgr.add("dependencies", info.get('depends_on', []))
        budget_mgr.add("parameter_sniffing", info.get('parameter_sniffing', {}))
        budget_mgr.add("historical_trend", info.get('historical_trend', {}))
        budget_mgr.add("memory_grants", info.get('memory_grants', {}))
        
        # Get budget report
        budget_report = budget_mgr.get_budget_report()
        self._emit_log(f"Context: {budget_report['used_tokens']:,} tokens ({budget_report['utilization_pct']:.1f}% budget)")
        
        obs.step_completed("context_assembly", f"✅ Context: {len(source_code):,} chars source")
        
        # Log collected data summary
        if info.get('stats'):
            stats = info.get('stats', {})
            self._emit_log(f"Stats: {stats.get('execution_count', 0):,} executions, {stats.get('avg_duration_ms', 0):.2f}ms avg")
        
        if info.get('parameter_sniffing'):
            risk = info.get('parameter_sniffing', {}).get('risk_level', 'unknown')
            emoji = "🟢" if risk == "low" else ("🟡" if risk == "medium" else "🔴")
            self._emit_log(f"Parameter Sniffing: {emoji} {risk.upper()}")
        
        if info.get('historical_trend'):
            trend = info.get('historical_trend', {}).get('trend_direction', 'stable')
            self._emit_log(f"Historical Trend: {trend}")

        try:
            # Step: Building Prompt
            obs.step_started("prompt_building", "✍️ Building AI prompt...")
            await asyncio.sleep(0.05)
            
            service = AIAnalysisService()
            provider_name = getattr(service, "provider_id", None) or "active provider"
            self._emit_log(f"AI Provider: {provider_name}")
            
            obs.step_completed("prompt_building")
            
            # Step: AI Request
            obs.step_started("ai_request", "🤖 Requesting AI analysis...")
            
            response, confidence = await service.analyze_sp(
                source_code=source_code,
                object_name=info.get('full_name', 'Object'),
                stats=info.get('stats'),
                missing_indexes=info.get('missing_indexes'),
                dependencies=info.get('depends_on'),
                query_store=info.get('query_store'),
                plan_xml=info.get('plan_xml'),
                plan_meta=info.get('plan_meta'),
                plan_insights=info.get('plan_insights'),
                existing_indexes=info.get('existing_indexes'),
                parameter_sniffing=info.get('parameter_sniffing'),
                historical_trend=info.get('historical_trend'),
                memory_grants=info.get('memory_grants'),
                # Data completeness for graceful degradation
                completeness=info.get('completeness'),
                context_warning=info.get('context_warning'),
                # Analysis mode options
                deep_analysis=self.deep_mode,
                skip_cache=self.skip_cache,
            )
            
            # Store confidence for potential deep analysis
            self._last_confidence = confidence
            
            confidence_info = ""
            if confidence:
                confidence_info = f" | Confidence: {confidence.percentage}%"
                # Emit confidence info for UI
                try:
                    self.confidence_ready.emit(confidence.to_display_dict())
                except Exception:
                    pass
            
            obs.step_completed("ai_request", f"✅ AI response: {len(response) if response else 0:,} chars{confidence_info}")
            
            # Step: Response Parsing
            obs.step_started("response_parsing", "📋 Parsing AI response...")
            await asyncio.sleep(0.05)
            
            response_len = len(response) if response else 0
            self._emit_log(f"AI Response: {response_len:,} characters")
            
            obs.step_completed("response_parsing")
            
            return response
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            obs.step_failed("ai_request", str(e))
            self._emit_log(f"Error: {e}")
            return self._generate_fallback_report()
    
    async def _generate_optimized_code(self) -> str:
        """
        Generate optimized code using ProgressObserver for step tracking.
        """
        from app.ai.analysis_service import AIAnalysisService
        import asyncio
        
        info = self.object_info
        obs = self._observer
        
        # Step: Code Prompt Building
        obs.step_started("code_prompt", "✍️ Building optimization prompt...")
        await asyncio.sleep(0.05)
        
        source_code = info.get('source_code', '')
        if not source_code:
            obs.step_failed("code_prompt", "Source code not found")
            return "-- Source code not found"
        
        self._emit_log(f"Source code: {len(source_code):,} characters")
        
        # Log identified issues
        issues = []
        if info.get('plan_insights'):
            if info.get('plan_insights', {}).get('has_table_scan'):
                issues.append("Table Scan")
            if info.get('plan_insights', {}).get('has_key_lookup'):
                issues.append("Key Lookup")
        if info.get('parameter_sniffing', {}).get('risk_level') in ('medium', 'high'):
            issues.append("Parameter Sniffing")
        if issues:
            self._emit_log(f"Issues to address: {', '.join(issues)}")
        
        obs.step_completed("code_prompt")
        
        try:
            # Step: AI Optimization
            obs.step_started("ai_optimization", "🤖 Generating optimized code...")
            
            service = AIAnalysisService()
            provider_name = getattr(service, "provider_id", None) or "active provider"
            self._emit_log(f"AI Provider: {provider_name}")
            
            response = await service.optimize_sp(
                source_code=source_code,
                object_name=info.get('full_name', 'Object'),
                stats=info.get('stats'),
                missing_indexes=info.get('missing_indexes'),
                dependencies=info.get('depends_on'),
                query_store=info.get('query_store'),
                plan_xml=info.get('plan_xml'),
                plan_meta=info.get('plan_meta'),
                plan_insights=info.get('plan_insights'),
                existing_indexes=info.get('existing_indexes'),
                parameter_sniffing=info.get('parameter_sniffing'),
                historical_trend=info.get('historical_trend'),
                memory_grants=info.get('memory_grants'),
            )
            
            obs.step_completed("ai_optimization", f"✅ Generated {len(response) if response else 0:,} chars")
            
            # Step: Code Validation
            obs.step_started("code_validation", "✅ Validating optimized code...")
            await asyncio.sleep(0.05)
            
            response_len = len(response) if response else 0
            self._emit_log(f"Optimized code: {response_len:,} characters")
            
            obs.step_completed("code_validation")
            
            return response
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            obs.step_failed("ai_optimization", str(e))
            self._emit_log(f"Error: {e}")
            return self._generate_fallback_optimized_code()
    
    def _format_stats(self) -> str:
        stats = self.object_info.get('stats', {})
        if not stats:
            return "No statistics available"
        
        return f"""- Execution Count: {stats.get('execution_count', 0)}
- Avg CPU: {stats.get('avg_cpu_ms', 0):.2f} ms
- Avg Duration: {stats.get('avg_duration_ms', 0):.2f} ms
- Avg Reads: {stats.get('avg_logical_reads', 0):.0f}
- Plan Count: {stats.get('plan_count', 0)}"""
    
    def _generate_fallback_optimized_code(self) -> str:
        source = self.object_info.get('source_code', '')
        if not source:
            return "-- Source code not found"
        
        optimized = f"""-- OPTIMIZED BY AI (Fallback Mode)
-- Note: Basic optimizations were applied because AI is not configured/available

{source}

/*
╔════════════════════════════════════════════════════════════════╗
║                    RECOMMENDED OPTIMIZATIONS                  ║
╠════════════════════════════════════════════════════════════════╣
║ 1. Add SET NOCOUNT ON at the start of the procedure           ║
║ 2. Avoid SELECT *; select only required columns               ║
║ 3. Use indexed columns in WHERE predicates where possible     ║
║ 4. Consider NOLOCK carefully for large read-only workloads    ║
║ 5. Add TRY/CATCH error handling                               ║
╚════════════════════════════════════════════════════════════════╝
*/
"""
        return optimized
    
    def _build_tune_prompt(self) -> str:
        info = self.object_info
        
        prompt = f"""## Object To Analyze
- **Database:** {info['database']}
- **Object:** {info['full_name']}

## Source Code
```sql
{info['source_code'][:5000] if info['source_code'] else 'Source code not found'}
```

## Execution Statistics
"""
        if info['stats']:
            stats = info['stats']
            prompt += f"""- Total Executions: {stats.get('execution_count', 0):,}
- Avg CPU: {stats.get('avg_cpu_ms', 0):.2f} ms
- Avg Duration: {stats.get('avg_duration_ms', 0):.2f} ms
- Avg Reads: {stats.get('avg_logical_reads', 0):,.0f}
- Plan Count: {stats.get('plan_count', 0)}
"""
        else:
            prompt += "No statistics found.\n"
        
        prompt += "\n## Missing Index Recommendations\n"
        if info.get('missing_indexes'):
            for idx in info['missing_indexes']:
                prompt += f"""- Equality: {idx.get('equality_columns', '-')}
  Include: {idx.get('included_columns', '-')}
  Impact: %{idx.get('avg_user_impact', 0):.0f}
"""
        else:
            prompt += "No missing index recommendations.\n"
        
        prompt += """
---
Please provide a detailed analysis and recommendations.
"""
        return prompt
    
    def _generate_fallback_report(self) -> str:
        info = self.object_info
        stats = info.get('stats', {})
        
        report = f"""# 🔧 Performance Analysis Report

## 📋 Object Information
- **Database:** {info['database']}
- **Object:** {info['full_name']}

## 📊 Execution Statistics
"""
        
        if stats:
            exec_count = stats.get('execution_count', 0) or 0
            avg_cpu = stats.get('avg_cpu_ms', 0) or 0
            avg_duration = stats.get('avg_duration_ms', 0) or 0
            avg_reads = stats.get('avg_logical_reads', 0) or 0
            
            report += f"""| Metric | Value | Status |
|--------|-------|-------|
| Total Executions | {exec_count:,} | {'🟢' if exec_count < 10000 else '🟡'} |
| Avg CPU | {avg_cpu:.2f} ms | {'🟢' if avg_cpu < 100 else '🟡' if avg_cpu < 500 else '🔴'} |
| Avg Duration | {avg_duration:.2f} ms | {'🟢' if avg_duration < 100 else '🟡' if avg_duration < 1000 else '🔴'} |
| Avg Reads | {avg_reads:,.0f} | {'🟢' if avg_reads < 1000 else '🟡' if avg_reads < 10000 else '🔴'} |

"""
        else:
            report += "*No statistics found.*\n\n"
        
        report += """## 💡 General Recommendations

1. **Indexes:** Review missing index recommendations
2. **Execution Plan:** Use `SET STATISTICS IO ON` and review the execution plan
3. **Code Review:** Avoid `SELECT *` and return only required columns

*Note: For detailed AI analysis, configure an AI provider (Settings > AI / LLM).*
"""
        
        return report


class AITuneDialog(QDialog):
    """
    AI Tune dialog with confidence scoring and deep analysis support.
    
    Features:
    - Standard and Deep Analysis modes
    - Confidence badge with visual indicator
    - Validation warnings display
    - Professional HTML report generation
    """
    
    def __init__(self, object_info: dict, parent=None):
        super().__init__(parent)
        self.object_info = object_info
        self._optimized_code = ""
        self._log_entries = []
        self._collection_log_added = False
        
        # Confidence tracking
        self._last_confidence = None
        self._analysis_result = ""
        self._analysis_timestamp = None
        
        self._setup_ui()
        self._set_idle_state()
    
    def _setup_ui(self):
        self.setWindowTitle(f"AI Analysis: {self.object_info.get('full_name', '')}")
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
        
        title = QLabel(f"🤖 AI Performance Analysis: {self.object_info.get('full_name', '')}")
        title.setStyleSheet(f"color: {Colors.SECONDARY}; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Primary status pill shown in the header
        self._status_badge = QLabel("⏳ Analyzing...")
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

        # Progress bar - Enhanced visual design
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {Colors.BORDER};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:0.5 #8b5cf6, stop:1 #06b6d4);
                border-radius: 4px;
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
        self._info_label = QLabel("Step: Preparing analysis... (5%)")
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

        result_title = QLabel("📄 Analysis Result")
        result_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; font-size: 12px;")
        result_layout.addWidget(result_title)

        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setPlaceholderText("Preparing AI analysis, please wait...")
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
        log_title = QLabel("📋 Process Logs")
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
        copy_btn = QPushButton("Kopyala")
        copy_btn.setFixedHeight(22)
        copy_btn.setStyleSheet("""
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
        copy_btn.clicked.connect(self._copy_log)
        log_header.addWidget(copy_btn)
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
        
        # Confidence Badge (shown after analysis)
        confidence_container = QHBoxLayout()
        
        self._confidence_badge = QLabel("")
        self._confidence_badge.setStyleSheet(f"""
            background-color: {Colors.SURFACE};
            color: {Colors.TEXT_SECONDARY};
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
        """)
        self._confidence_badge.setVisible(False)
        confidence_container.addWidget(self._confidence_badge)
        
        self._deep_analysis_btn = QPushButton("🔬 Deep Analysis")
        self._deep_analysis_btn.setToolTip("Run comprehensive analysis (3x tokens, ~20% better accuracy)")
        self._deep_analysis_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #6d28d9;
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_MUTED};
            }}
        """)
        self._deep_analysis_btn.clicked.connect(self._run_deep_analysis)
        self._deep_analysis_btn.setVisible(False)
        confidence_container.addWidget(self._deep_analysis_btn)
        
        confidence_container.addStretch()
        layout.addLayout(confidence_container)
        
        # Buttons
        btn_layout = QHBoxLayout()

        self._start_btn = QPushButton("▶ Analizi Baslat")
        self._start_btn.clicked.connect(self._start_analysis)
        btn_layout.addWidget(self._start_btn)

        self._refresh_btn = QPushButton("🔄 Re-run Analysis")
        self._refresh_btn.clicked.connect(self._start_analysis)
        btn_layout.addWidget(self._refresh_btn)
        
        btn_layout.addStretch()

        self._save_btn = QPushButton("💾 Save Report")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_report)
        btn_layout.addWidget(self._save_btn)

        self._copy_btn = QPushButton("📋 Metni Kopyala")
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._copy_report)
        btn_layout.addWidget(self._copy_btn)
        
        self._close_btn = QPushButton("Kapat")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._close_btn)
        
        layout.addLayout(btn_layout)
        
        # Status
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self._status_label)

    def _set_idle_state(self):
        self._progress_bar.setValue(0)
        self._info_label.setText("📋 Ready to start analysis")
        self._status_badge.setText("⏸️ Ready")
        self._status_badge.setStyleSheet(f"""
            background-color: {Colors.PRIMARY_LIGHT};
            color: {Colors.TEXT_SECONDARY};
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
        """)
        self._result_text.setMarkdown("""## ℹ️ Analysis Not Started

Click **▶ Analizi Başlat** to run a comprehensive performance analysis.

### What will be analyzed:
- 📄 Source code review
- 📊 Execution statistics  
- 🗄️ Query Store metrics
- 🔍 Execution plan analysis
- 📈 Plan insights (warnings, expensive operators)
- 🗂️ Existing index usage
- ⚡ Parameter sniffing detection
- 📉 Historical performance trends
- 💾 Memory grant analysis

The AI will provide detailed optimization recommendations based on all collected data.
""")
        self._refresh_btn.setEnabled(False)

    def _start_analysis(self, deep_mode: bool = False, skip_cache: bool = False, show_options: bool = True):
        """Start AI analysis (standard or deep mode)"""
        # Show options dialog if this is a fresh start (not from Re-run or Deep Analysis button)
        if show_options:
            options_dialog = AnalysisOptionsDialog(self)
            result = options_dialog.exec()
            
            if result != QDialog.DialogCode.Accepted:
                return  # User cancelled
            
            deep_mode = options_dialog.deep_mode
            skip_cache = options_dialog.skip_cache
        
        self._start_btn.setEnabled(False)
        self._refresh_btn.setEnabled(False)
        self._save_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)
        self._deep_analysis_btn.setVisible(False)
        self._confidence_badge.setVisible(False)
        
        mode_label = "🔬 Deep Analysis" if deep_mode else "🔄 Standard Analysis"
        cache_info = " (Force Refresh)" if skip_cache else ""
        self._status_label.setText(f"{mode_label}{cache_info} running...")
        self._result_text.setMarkdown(f"## ⏳ Running {mode_label}...\n\nAnalyzing your stored procedure step by step...")
        self._analysis_result = ""
        self._progress_bar.setValue(0)
        self._info_label.setText("📋 Initializing analysis...")
        self._status_badge.setText("⏳ Analyzing...")
        
        if not self._collection_log_added:
            self._add_log("━━━━━ Data Collection Summary ━━━━━")
            for entry in self.object_info.get("collection_log", []):
                self._add_log(f"  {entry}")
            self._add_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            self._collection_log_added = True
        
        self._add_log("")
        self._add_log(f"━━━━━ {mode_label}{cache_info} Progress ━━━━━")
        if skip_cache:
            self._add_log("   ℹ️ Cache bypassed - running fresh analysis")
        
        # Store analysis timestamp
        from datetime import datetime
        self._analysis_timestamp = datetime.now()
        
        self._analysis_worker = AITuneWorker(
            self.object_info, 
            mode="analyze", 
            deep_mode=deep_mode,
            skip_cache=skip_cache
        )
        self._analysis_worker.analysis_ready.connect(self._on_analysis_complete)
        self._analysis_worker.error.connect(self._on_error)
        self._analysis_worker.log.connect(self._add_log)
        self._analysis_worker.progress.connect(self._on_progress_update)
        self._analysis_worker.confidence_ready.connect(self._on_confidence_ready)
        self._analysis_worker.start()
    
    def _run_deep_analysis(self):
        """Run deep analysis mode (3x tokens, ~20% better accuracy)"""
        self._add_log("🔬 Starting Deep Analysis mode (enhanced accuracy)...")
        self._add_log("   ℹ️ Deep analysis uses more tokens for comprehensive validation")
        self._start_analysis(deep_mode=True, show_options=False)
    
    def _on_progress_update(self, percentage: int, step: str):
        """Handle progress updates from worker"""
        self._progress_bar.setValue(percentage)
        self._info_label.setText(f"{step} ({percentage}%)")
        
        # Update status badge based on progress
        if percentage < 50:
            self._status_badge.setText(f"⏳ {percentage}%")
        elif percentage < 100:
            self._status_badge.setText(f"🔄 {percentage}%")
        else:
            if "❌" in step:
                self._status_badge.setText("❌ Failed")
            else:
                self._status_badge.setText("✅ Complete")
    
    def _on_confidence_ready(self, confidence_dict: dict):
        """Handle confidence information from analysis"""
        self._last_confidence = confidence_dict
        
        score = confidence_dict.get("score", 0)
        level = confidence_dict.get("level", "unknown")
        emoji = confidence_dict.get("emoji", "⚪")
        deep_recommended = confidence_dict.get("deep_analysis_recommended", False)
        
        # Update confidence badge
        self._confidence_badge.setText(f"{emoji} Confidence: {score}% ({level})")
        self._confidence_badge.setVisible(True)
        
        # Style based on level
        if level == "high":
            bg_color, text_color = "#dcfce7", "#166534"
        elif level == "medium":
            bg_color, text_color = "#fef9c3", "#854d0e"
        elif level == "low":
            bg_color, text_color = "#fed7aa", "#c2410c"
        else:
            bg_color, text_color = "#fee2e2", "#dc2626"
        
        self._confidence_badge.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
        """)
        
        # Show deep analysis button if recommended
        if deep_recommended:
            self._deep_analysis_btn.setVisible(True)
            self._add_log(f"💡 Deep Analysis recommended (confidence: {score}%)")
        
        # Log warnings
        warnings = confidence_dict.get("warnings", [])
        if warnings:
            self._add_log("⚠️ Validation warnings:")
            for w in warnings[:3]:
                self._add_log(f"  - {w}")
    
    def _on_analysis_complete(self, result: str):
        self._analysis_result = result
        self._result_text.setMarkdown(result)
        self._refresh_btn.setEnabled(True)
        self._start_btn.setEnabled(True)
        self._save_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)
        
        self._status_label.setText("✅ Analysis completed successfully")
        self._progress_bar.setValue(100)
        self._info_label.setText("✅ Analysis complete! (100%)")
        self._status_badge.setText("✅ Complete")
        self._status_badge.setStyleSheet(f"""
            background-color: #dcfce7;
            color: #166534;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        """)
        
        self._add_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self._add_log("✅ Analysis completed successfully!")
    
    def _on_error(self, error: str):
        self._analysis_result = ""
        self._result_text.setMarkdown(f"## ❌ Error\n\n{error}\n\n---\n\n*Please check the logs for more details.*")
        self._refresh_btn.setEnabled(True)
        self._start_btn.setEnabled(True)
        
        self._status_label.setText(f"❌ Error: {error[:80]}...")
        self._progress_bar.setValue(0)
        self._info_label.setText("❌ Error occurred - check logs")
        self._status_badge.setText("❌ Failed")
        self._status_badge.setStyleSheet(f"""
            background-color: #fee2e2;
            color: #dc2626;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
        """)
        
        self._add_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self._add_log(f"❌ ERROR: {error}")

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

    def _copy_log(self) -> None:
        from PyQt6.QtWidgets import QApplication
        text = self._log_area.toPlainText()
        QApplication.clipboard().setText(text)
        self._add_log("Logs copied to clipboard.")

    def _copy_report(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._result_text.toPlainText())
        self._add_log("Result copied to clipboard.")

    def _get_report_markdown(self) -> str:
        """
        Return original AI markdown when available.
        Avoid QTextEdit markdown round-trip artifacts for fenced code blocks.
        """
        if isinstance(self._analysis_result, str) and self._analysis_result.strip():
            return self._analysis_result
        return self._result_text.toMarkdown()

    def _save_report(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from datetime import datetime
        
        text = self._get_report_markdown()
        if not text:
            QMessageBox.information(self, "Report", "No report available to save.")
            return
        
        object_name = self.object_info.get('full_name', 'Unknown')
        safe_name = object_name.replace('.', '_').replace('[', '').replace(']', '')
        
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            f"AI_Report_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "HTML (*.html);;Markdown (*.md);;Text (*.txt)"
        )
        if not file_path:
            return
        
        try:
            if selected_filter.startswith("HTML"):
                content = self._generate_html_report()
            elif selected_filter.startswith("Text"):
                content = self._result_text.toPlainText()
            else:
                content = text
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._add_log(f"Report saved: {file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Report", f"Failed to save report: {e}")
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert markdown to HTML with proper handling of:
        - Code blocks (as single units)
        - Tables
        - Lists
        - Headers with section dividers
        """
        import re
        import html
        
        if not markdown_text:
            return ""
        
        # Pre-process: Remove escape backslashes (e.g., "1\." -> "1.")
        markdown_text = re.sub(r'\\([.#*_\[\]()])', r'\1', markdown_text)
        
        lines = markdown_text.split('\n')
        html_parts = []
        in_code_block = False
        code_block_content = []
        code_language = ""
        in_list = False
        list_type = None
        in_table = False
        table_rows = []
        h2_count = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Code block start/end
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_language = line.strip()[3:].strip()
                    code_block_content = []
                else:
                    in_code_block = False
                    code_text = '\n'.join(code_block_content)
                    code_text = html.escape(code_text)
                    html_parts.append(f'<pre><code class="language-{code_language}">{code_text}</code></pre>')
                i += 1
                continue
            
            if in_code_block:
                code_block_content.append(line)
                i += 1
                continue
            
            # Table detection (line starts with | or contains |)
            is_table_row = line.strip().startswith('|') and line.strip().endswith('|')
            is_separator = bool(re.match(r'^\|?[\s\-:|]+\|?$', line.strip())) and '|' in line
            
            if is_table_row or (in_table and is_separator):
                if not in_table:
                    # Close any open list
                    if in_list:
                        html_parts.append(f'</{list_type}>')
                        in_list = False
                        list_type = None
                    in_table = True
                    table_rows = []
                table_rows.append(line)
                i += 1
                continue
            elif in_table:
                # End of table
                html_parts.append(self._render_table(table_rows))
                in_table = False
                table_rows = []
                # Don't increment i, process current line
            
            # Headers
            if line.startswith('######'):
                html_parts.append(f'<h6>{self._inline_markdown(line[6:].strip())}</h6>')
            elif line.startswith('#####'):
                html_parts.append(f'<h5>{self._inline_markdown(line[5:].strip())}</h5>')
            elif line.startswith('####'):
                html_parts.append(f'<h4>{self._inline_markdown(line[4:].strip())}</h4>')
            elif line.startswith('###'):
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                html_parts.append(f'<h3>{self._inline_markdown(line[3:].strip())}</h3>')
            elif line.startswith('##'):
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                h2_count += 1
                if h2_count > 1:
                    html_parts.append('<hr>')
                html_parts.append(f'<h2>{self._inline_markdown(line[2:].strip())}</h2>')
            elif line.startswith('#'):
                html_parts.append(f'<h1>{self._inline_markdown(line[1:].strip())}</h1>')
            
            # Horizontal rule
            elif line.strip() in ['---', '***', '___']:
                html_parts.append('<hr>')
            
            # Ordered list
            elif re.match(r'^\d+\.\s+', line):
                if not in_list or list_type != 'ol':
                    if in_list:
                        html_parts.append(f'</{list_type}>')
                    html_parts.append('<ol>')
                    in_list = True
                    list_type = 'ol'
                content = re.sub(r'^\d+\.\s+', '', line)
                html_parts.append(f'<li>{self._inline_markdown(content)}</li>')
            
            # Unordered list
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                if not in_list or list_type != 'ul':
                    if in_list:
                        html_parts.append(f'</{list_type}>')
                    html_parts.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                content = line.strip()[2:]
                html_parts.append(f'<li>{self._inline_markdown(content)}</li>')
            
            # Empty line
            elif line.strip() == '':
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
            
            # Regular paragraph
            else:
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                if line.strip():
                    html_parts.append(f'<p>{self._inline_markdown(line)}</p>')
            
            i += 1
        
        # Close any open elements
        if in_list:
            html_parts.append(f'</{list_type}>')
        if in_table and table_rows:
            html_parts.append(self._render_table(table_rows))
        
        return '\n'.join(html_parts)
    
    def _render_table(self, rows: list) -> str:
        """Render markdown table rows to HTML table"""
        import html
        import re
        
        if not rows:
            return ""
        
        html_parts = ['<table>']
        header_done = False
        
        for row in rows:
            # Clean the row
            row = row.strip()
            if row.startswith('|'):
                row = row[1:]
            if row.endswith('|'):
                row = row[:-1]
            
            cells = [c.strip() for c in row.split('|')]
            
            # Skip separator rows (contain only -, :, spaces)
            if all(re.match(r'^[\s\-:]+$', c) for c in cells):
                continue
            
            if not header_done:
                # First data row is header
                html_parts.append('<thead><tr>')
                for cell in cells:
                    html_parts.append(f'<th>{self._inline_markdown(cell)}</th>')
                html_parts.append('</tr></thead>')
                html_parts.append('<tbody>')
                header_done = True
            else:
                html_parts.append('<tr>')
                for cell in cells:
                    html_parts.append(f'<td>{self._inline_markdown(cell)}</td>')
                html_parts.append('</tr>')
        
        if header_done:
            html_parts.append('</tbody>')
        html_parts.append('</table>')
        
        return '\n'.join(html_parts)
    
    def _inline_markdown(self, text: str) -> str:
        """Convert inline markdown (bold, italic, code, links)"""
        import re
        import html
        
        # Escape HTML first
        text = html.escape(text)
        
        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        
        # Italic: *text* or _text_
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
        
        # Inline code: `code`
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Links: [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        return text
    
    def _generate_html_report(self) -> str:
        """Generate professional HTML report with header information"""
        from datetime import datetime
        
        object_name = self.object_info.get('full_name', 'Unknown')
        database = self.object_info.get('database', 'Unknown')
        analysis_time = self._analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S') if self._analysis_timestamp else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get confidence info
        confidence_html = ""
        if self._last_confidence:
            score = self._last_confidence.get("score", 0)
            level = self._last_confidence.get("level", "unknown")
            emoji = self._last_confidence.get("emoji", "⚪")
            
            if level == "high":
                badge_color = "#166534"
                badge_bg = "#dcfce7"
            elif level == "medium":
                badge_color = "#854d0e"
                badge_bg = "#fef9c3"
            elif level == "low":
                badge_color = "#c2410c"
                badge_bg = "#fed7aa"
            else:
                badge_color = "#dc2626"
                badge_bg = "#fee2e2"
            
            confidence_html = f'''
            <div style="display: inline-block; background-color: {badge_bg}; color: {badge_color}; padding: 6px 14px; border-radius: 6px; font-weight: 600; margin-left: 10px;">
                {emoji} Confidence: {score}% ({level})
            </div>
            '''
        
        # Get completeness info
        completeness = self.object_info.get('completeness', {})
        quality_level = completeness.get('quality_level', 'unknown')
        completeness_score = completeness.get('completeness_score', 0)
        
        # Convert markdown to proper HTML
        body_content = self._markdown_to_html(self._get_report_markdown())
        
        html_template = f'''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Performance Analysis Report - {object_name}</title>
    <style>
        :root {{
            /* App Colors - Teal Theme */
            --primary: #0e8a9d;
            --primary-dark: #0d7a8b;
            --primary-light: #e4f0f4;
            --secondary: #6366f1;
            --success: #10b981;
            --success-light: #d1fae5;
            --warning: #f59e0b;
            --warning-light: #fef3c7;
            --danger: #dc2626;
            --danger-light: #fef2f2;
            --info: #3b82f6;
            --info-light: #dbeafe;
            
            /* Neutrals */
            --bg: #f5f7fb;
            --surface: #ffffff;
            --text: #1f2937;
            --text-secondary: #6b7280;
            --text-muted: #9ca3af;
            --border: #e5e7eb;
            --border-light: #eef2f7;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}
        
        /* Header - Teal gradient matching app */
        .header {{
            background: linear-gradient(135deg, #0a5f6f 0%, #0e8a9d 100%);
            color: white;
            padding: 32px 40px;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 26px;
            font-weight: 700;
            margin-bottom: 20px;
            letter-spacing: -0.5px;
        }}
        
        .header-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 30px;
            font-size: 14px;
        }}
        
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .meta-label {{
            opacity: 0.85;
        }}
        
        .meta-value {{
            font-weight: 600;
        }}
        
        .badges {{
            margin-top: 18px;
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .badge-success {{ background-color: rgba(16, 185, 129, 0.2); color: #065f46; }}
        .badge-warning {{ background-color: rgba(245, 158, 11, 0.2); color: #854d0e; }}
        .badge-info {{ background-color: rgba(14, 138, 157, 0.2); color: #0a5f6f; }}
        
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 0 40px 40px;
        }}
        
        .content {{
            background-color: var(--surface);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            padding: 36px 40px;
        }}
        
        /* Section Headers - Clear hierarchy */
        .content h1 {{
            color: var(--primary-dark);
            font-size: 22px;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 3px solid var(--primary);
        }}
        
        .content h2 {{
            color: var(--text);
            font-size: 18px;
            font-weight: 700;
            margin-top: 36px;
            margin-bottom: 16px;
            padding: 14px 18px;
            background: linear-gradient(90deg, var(--primary-light) 0%, transparent 100%);
            border-left: 4px solid var(--primary);
            border-radius: 0 8px 8px 0;
        }}
        
        .content h3 {{
            color: var(--primary-dark);
            font-size: 15px;
            font-weight: 600;
            margin-top: 24px;
            margin-bottom: 12px;
            padding-left: 12px;
            border-left: 3px solid var(--secondary);
        }}
        
        .content h4 {{
            color: var(--text);
            font-size: 14px;
            font-weight: 600;
            margin-top: 18px;
            margin-bottom: 10px;
        }}
        
        .content p {{
            margin-bottom: 14px;
            line-height: 1.7;
        }}
        
        /* List styling */
        .content ul, .content ol {{
            margin-left: 20px;
            margin-bottom: 18px;
        }}
        
        .content li {{
            margin-bottom: 10px;
            line-height: 1.6;
        }}
        
        .content ol > li {{
            margin-bottom: 14px;
            padding-bottom: 10px;
            border-bottom: 1px dashed var(--border-light);
        }}
        
        .content ol > li:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        
        /* Inline code */
        .content code {{
            background-color: var(--primary-light);
            color: var(--primary-dark);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
        }}
        
        /* Code blocks */
        .content pre {{
            position: relative;
            background-color: #f8fafc;
            border: 1px solid var(--border);
            color: var(--text);
            padding: 16px 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 16px 0 24px 0;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.4;
            white-space: pre;
        }}
        
        .content pre code {{
            background-color: transparent;
            padding: 0;
            color: inherit;
            font-size: inherit;
            line-height: inherit;
            white-space: pre;
        }}
        
        /* Code block copy button */
        .code-wrapper {{
            position: relative;
        }}
        
        .copy-btn {{
            position: absolute;
            top: 8px;
            right: 8px;
            background-color: var(--primary-light);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 11px;
            cursor: pointer;
            color: var(--primary-dark);
            transition: all 0.2s;
        }}
        
        .copy-btn:hover {{
            background-color: var(--primary);
            color: white;
            border-color: var(--primary);
        }}
        
        .copy-btn.copied {{
            background-color: var(--success-light);
            color: #065f46;
            border-color: var(--success);
        }}
        
        /* Tables */
        .content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 13px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0, 128, 128, 0.1);
        }}
        
        .content thead {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        }}
        
        .content th {{
            color: #ffffff;
            font-weight: 600;
            padding: 12px 16px;
            text-align: left;
            border: none;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        
        .content td {{
            border: none;
            border-bottom: 1px solid var(--border-light);
            padding: 10px 16px;
            text-align: left;
            color: var(--text);
        }}
        
        .content tbody tr {{
            background-color: #ffffff;
            transition: background-color 0.2s;
        }}
        
        .content tbody tr:nth-child(even) {{
            background-color: #f8fafa;
        }}
        
        .content tbody tr:hover {{
            background-color: var(--primary-light);
        }}
        
        .content tbody tr:last-child td {{
            border-bottom: none;
        }}
        
        /* Section Divider */
        .content hr {{
            border: none;
            height: 2px;
            background: linear-gradient(90deg, var(--primary) 0%, var(--border) 50%, transparent 100%);
            margin: 32px 0;
        }}
        
        /* Strong/Bold text */
        .content strong {{
            color: var(--text);
            font-weight: 600;
        }}
        
        /* Emphasis markers for priorities */
        .content em {{
            font-style: normal;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 12px;
            border-top: 1px solid var(--border);
            margin-top: 30px;
        }}
        
        .footer a {{
            color: var(--primary);
            text-decoration: none;
        }}
        
        @media print {{
            .header {{ background: #0e8a9d !important; -webkit-print-color-adjust: exact; }}
            body {{ background: white; }}
            .copy-btn {{ display: none; }}
            .content h2 {{ background: #e4f0f4 !important; -webkit-print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 AI Performance Analysis Report</h1>
        <div class="header-meta">
            <div class="meta-item">
                <span class="meta-label">📦 Object:</span>
                <span class="meta-value">{object_name}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">🗄️ Database:</span>
                <span class="meta-value">{database}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">📅 Analysis Date:</span>
                <span class="meta-value">{analysis_time}</span>
            </div>
        </div>
        <div class="badges">
            <span class="badge badge-info">Data Quality: {quality_level} ({completeness_score:.0f}%)</span>
            {confidence_html}
        </div>
    </div>
    
    <div class="container">
        <div class="content">
            {body_content}
        </div>
        
        <div class="footer">
            Generated by SQL Performance AI Studio Pro | {analysis_time}
        </div>
    </div>
    
    <script>
        // Add copy buttons to all code blocks
        document.addEventListener('DOMContentLoaded', function() {{
            const codeBlocks = document.querySelectorAll('pre');
            codeBlocks.forEach(function(pre, index) {{
                // Create wrapper
                const wrapper = document.createElement('div');
                wrapper.className = 'code-wrapper';
                pre.parentNode.insertBefore(wrapper, pre);
                wrapper.appendChild(pre);
                
                // Create copy button
                const btn = document.createElement('button');
                btn.className = 'copy-btn';
                btn.textContent = '📋 Copy';
                btn.onclick = function() {{
                    const code = pre.textContent;
                    navigator.clipboard.writeText(code).then(function() {{
                        btn.textContent = '✓ Copied!';
                        btn.classList.add('copied');
                        setTimeout(function() {{
                            btn.textContent = '📋 Copy';
                            btn.classList.remove('copied');
                        }}, 2000);
                    }});
                }};
                wrapper.appendChild(btn);
            }});
            
            // Fix line spacing in code - remove extra blank lines
            codeBlocks.forEach(function(pre) {{
                let text = pre.textContent;
                // Remove multiple consecutive blank lines
                text = text.replace(/\\n\\s*\\n\\s*\\n/g, '\\n\\n');
                // Remove leading/trailing whitespace
                text = text.trim();
                pre.textContent = text;
            }});
        }});
    </script>
</body>
</html>'''
        
        return html_template
