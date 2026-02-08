"""
Execution Plan Viewer Components

SQL Server execution plan görselleştirme widget'ları.
SSMS tarzı tree view ve operatör detay paneli.
Modern Light Theme uyumlu.
"""

from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTreeWidget, QTreeWidgetItem, QSplitter,
    QGroupBox, QScrollArea, QFrame, QTextEdit,
    QPushButton, QTabWidget, QProgressBar,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from app.core.logger import get_logger
from app.ui.theme import Colors
from app.analysis.plan_parser import ExecutionPlan, PlanOperator, MissingIndex, PlanWarning
from app.models.query_stats_models import PlanStability

logger = get_logger('ui.plan_viewer')


# Operator icon mapping
OPERATOR_ICONS = {
    'Clustered Index Scan': '🔍',
    'Clustered Index Seek': '🎯',
    'Nonclustered Index Scan': '🔎',
    'Nonclustered Index Seek': '🎯',
    'Table Scan': '📋',
    'Index Scan': '🔍',
    'Index Seek': '🎯',
    'Key Lookup': '🔑',
    'RID Lookup': '🔑',
    'Nested Loops': '🔄',
    'Hash Match': '#️⃣',
    'Merge Join': '🔀',
    'Sort': '📊',
    'Filter': '🔽',
    'Compute Scalar': '📐',
    'Stream Aggregate': '📈',
    'Hash Aggregate': '📊',
    'Parallelism': '⚡',
    'Select': '✅',
    'Insert': '➕',
    'Update': '✏️',
    'Delete': '❌',
}


class OperatorTreeItem(QTreeWidgetItem):
    """Plan operatörü için tree item"""
    
    def __init__(self, operator: PlanOperator, parent=None):
        super().__init__(parent)
        self.operator = operator
        self._setup_item()
    
    def _setup_item(self) -> None:
        op = self.operator
        
        # Get icon
        icon = OPERATOR_ICONS.get(op.physical_op, '⚙️')
        
        # Kolon 0: Operatör adı + ikon
        display = f"{icon} {op.short_name}"
        self.setText(0, display)
        
        # Kolon 1: Maliyet yüzdesi
        cost_text = f"{op.cost_percent:.1f}%"
        self.setText(1, cost_text)
        
        # Kolon 2: Tahmini satır sayısı
        rows_text = self._format_rows(op.estimated_rows)
        self.setText(2, rows_text)
        
        # Kolon 3: Nesne adı
        obj_text = op.object_name or ""
        if op.index_name and op.index_name != op.object_name:
            obj_text += f" ({op.index_name})"
        self.setText(3, obj_text)
        
        # Renk ve stil
        if op.has_warnings or op.spill_to_tempdb:
            self.setForeground(0, QColor(Colors.ERROR))
            self.setForeground(1, QColor(Colors.ERROR))
        elif op.is_scan or op.is_lookup:
            self.setForeground(0, QColor(Colors.WARNING))
            self.setForeground(1, QColor(Colors.WARNING))
        elif op.is_expensive:
            self.setForeground(0, QColor("#D97706"))
            self.setForeground(1, QColor("#D97706"))
        
        # Tooltip
        tooltip = self._build_tooltip()
        self.setToolTip(0, tooltip)
    
    def _format_rows(self, rows: float) -> str:
        """Satır sayısını formatla"""
        if rows >= 1_000_000:
            return f"{rows/1_000_000:.1f}M"
        elif rows >= 1_000:
            return f"{rows/1_000:.1f}K"
        return f"{rows:.0f}"
    
    def _build_tooltip(self) -> str:
        """Tooltip oluştur"""
        op = self.operator
        lines = [
            f"<b>{op.physical_op}</b>",
            f"Logical: {op.logical_op}",
            f"",
            f"Cost: {op.cost_percent:.2f}% (Subtree: {op.subtree_cost:.4f})",
            f"CPU: {op.estimated_cpu_cost:.4f}",
            f"I/O: {op.estimated_io_cost:.4f}",
            f"",
            f"Est. Rows: {op.estimated_rows:.0f}",
            f"Row Size: {op.estimated_row_size} bytes",
        ]
        
        if op.parallel:
            lines.append(f"Parallel: Yes (DOP: {op.estimated_degree})")
        
        if op.object_name:
            lines.append(f"")
            lines.append(f"Object: {op.database_name}.{op.schema_name}.{op.object_name}")
        
        if op.index_name:
            lines.append(f"Index: {op.index_name}")
        
        if op.seek_predicates:
            lines.append(f"")
            lines.append(f"Seek: {op.seek_predicates[:100]}")
        
        if op.predicates:
            lines.append(f"Predicate: {op.predicates[:100]}")
        
        if op.warnings:
            lines.append(f"")
            lines.append(f"<font color='red'>⚠️ Warnings:</font>")
            for w in op.warnings:
                lines.append(f"  • {w.message}")
        
        return "<br>".join(lines)


class PlanTreeWidget(QWidget):
    """
    Execution plan tree görünümü
    
    Operatör ağacını SSMS tarzı hiyerarşik olarak gösterir.
    """
    
    operator_selected = pyqtSignal(object)  # PlanOperator
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._plan: Optional[ExecutionPlan] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Plan özet satırı
        self._summary_label = QLabel("No plan loaded")
        self._summary_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY}; 
            font-size: 12px; 
            padding: 8px;
            background-color: {Colors.SURFACE};
            border-radius: 6px;
        """)
        layout.addWidget(self._summary_label)
        
        # Tree widget
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Operator", "Cost %", "Est. Rows", "Object"])
        self._tree.setColumnWidth(0, 320)
        self._tree.setColumnWidth(1, 80)
        self._tree.setColumnWidth(2, 100)
        self._tree.setColumnWidth(3, 200)
        self._tree.setAlternatingRowColors(True)
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {Colors.BORDER};
                background-color: {Colors.SURFACE};
                alternate-background-color: #F8FAFC;
                color: {Colors.TEXT_PRIMARY};
                border-radius: 8px;
            }}
            QTreeWidget::item {{
                padding: 6px 4px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QTreeWidget::item:selected {{
                background-color: rgba(79, 70, 229, 0.12);
                color: {Colors.PRIMARY};
            }}
            QTreeWidget::item:hover {{
                background-color: rgba(79, 70, 229, 0.06);
            }}
            QHeaderView::section {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid {Colors.BORDER};
                font-weight: 600;
                font-size: 12px;
            }}
            QTreeWidget::branch {{
                background: transparent;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url(none);
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                border-image: none;
                image: url(none);
            }}
        """)
        
        self._tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree)
    
    def set_plan(self, plan: Optional[ExecutionPlan]) -> None:
        """Planı ayarla ve görselleştir"""
        self._plan = plan
        self._tree.clear()
        
        if not plan:
            self._summary_label.setText(
                "📋 No plan available - Query Store has no plan, or the query may not have executed yet."
            )
            return
        
        # Özet
        parallel_text = "⚡ Parallel" if plan.degree_of_parallelism > 1 else "Single Thread"
        self._summary_label.setText(
            f"📊 Operators: {plan.operator_count} | "
            f"💰 Cost: {plan.total_cost:.4f} | "
            f"{parallel_text}"
        )
        
        # Tree'yi oluştur
        if plan.root_operator:
            self._add_operator_to_tree(plan.root_operator, None)
        
        # Tümünü genişlet
        self._tree.expandAll()
    
    def _add_operator_to_tree(
        self, 
        operator: PlanOperator, 
        parent_item: Optional[QTreeWidgetItem]
    ) -> None:
        """Operatörü tree'ye ekle"""
        if parent_item is None:
            item = OperatorTreeItem(operator)
            self._tree.addTopLevelItem(item)
        else:
            item = OperatorTreeItem(operator, parent_item)
        
        # Child operatörleri ekle
        for child in operator.children:
            self._add_operator_to_tree(child, item)
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Item tıklandığında"""
        if isinstance(item, OperatorTreeItem):
            self.operator_selected.emit(item.operator)


class OperatorDetailPanel(QWidget):
    """
    Seçilen operatörün detaylarını gösteren panel
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._operator: Optional[PlanOperator] = None
        self._plan_stability: Optional[PlanStability] = None
        self._plan_count: Optional[int] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Başlık
        self._title_label = QLabel("Select an operator")
        self._title_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 16px;
            font-weight: bold;
            padding: 8px;
            background-color: {Colors.SURFACE};
            border-radius: 8px;
        """)
        layout.addWidget(self._title_label)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")
        
        content = QWidget()
        content.setStyleSheet(f"background: transparent;")
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(12)
        
        # Metrikler grubu
        self._metrics_group = self._create_group("📊 Metrikler")
        self._metrics_layout = self._metrics_group.layout()
        self._content_layout.addWidget(self._metrics_group)

        # Plan stabilite grubu
        self._plan_stability_group = self._create_group("📋 Plan Stability")
        self._plan_stability_layout = self._plan_stability_group.layout()
        self._content_layout.addWidget(self._plan_stability_group)
        
        # Nesne bilgisi grubu
        self._object_group = self._create_group("📁 Object Info")
        self._object_layout = self._object_group.layout()
        self._content_layout.addWidget(self._object_group)
        
        # Predicates grubu
        self._predicate_group = self._create_group("🔍 Predicates")
        self._predicate_layout = self._predicate_group.layout()
        self._content_layout.addWidget(self._predicate_group)
        
        # Uyarılar grubu
        self._warnings_group = self._create_group("⚠️ Warnings")
        self._warnings_layout = self._warnings_group.layout()
        self._content_layout.addWidget(self._warnings_group)
        
        self._content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _create_group(self, title: str) -> QFrame:
        """Styled group box oluştur"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
        """)
        layout.addWidget(title_label)
        
        return frame
    
    def set_operator(self, operator: Optional[PlanOperator]) -> None:
        """Operatörü ayarla"""
        self._operator = operator
        self._update_view()

    def set_plan_stability(self, plan_stability: Optional[PlanStability], plan_count: Optional[int]) -> None:
        """Plan stabilite bilgisini ayarla"""
        self._plan_stability = plan_stability
        self._plan_count = plan_count
        self._update_plan_stability()
    
    def _update_view(self) -> None:
        """Görünümü güncelle"""
        # Layout'ları temizle (ilk title widget'ı hariç)
        self._clear_layout(self._metrics_layout, keep_first=True)
        self._clear_layout(self._plan_stability_layout, keep_first=True)
        self._clear_layout(self._object_layout, keep_first=True)
        self._clear_layout(self._predicate_layout, keep_first=True)
        self._clear_layout(self._warnings_layout, keep_first=True)

        self._update_plan_stability()
        
        op = self._operator
        if not op:
            self._title_label.setText("📋 Select an operator")
            return
        
        # Get icon
        icon = OPERATOR_ICONS.get(op.physical_op, '⚙️')
        
        # Başlık
        self._title_label.setText(f"{icon} {op.physical_op}")
        
        # Metrikler
        metrics = [
            ("Cost", f"{op.cost_percent:.2f}%", op.cost_percent > 20),
            ("Subtree", f"{op.subtree_cost:.6f}", False),
            ("CPU", f"{op.estimated_cpu_cost:.6f}", False),
            ("I/O", f"{op.estimated_io_cost:.6f}", op.estimated_io_cost > 0.1),
            ("Estimated Rows", f"{op.estimated_rows:,.0f}", op.estimated_rows > 100000),
            ("Row Size", f"{op.estimated_row_size} bytes", False),
        ]
        
        if op.parallel:
            metrics.append(("Parallel", f"Yes (DOP: {op.estimated_degree})", False))
        
        if op.memory_grant_kb:
            metrics.append(("Memory Grant", f"{op.memory_grant_kb:,} KB", op.memory_grant_kb > 10000))
        
        for name, value, is_warning in metrics:
            self._add_metric_row(self._metrics_layout, name, value, is_warning)
        
        # Nesne bilgisi
        if op.object_name:
            self._add_info_row(self._object_layout, "Database", op.database_name)
            self._add_info_row(self._object_layout, "Schema", op.schema_name)
            self._add_info_row(self._object_layout, "Table", op.object_name)
            if op.index_name:
                self._add_info_row(self._object_layout, "Index", op.index_name)
        else:
            na_label = QLabel("N/A")
            na_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; background: transparent;")
            self._object_layout.addWidget(na_label)
        
        # Predicates
        if op.seek_predicates:
            seek_label = QLabel(f"🎯 Seek: {op.seek_predicates}")
            seek_label.setWordWrap(True)
            seek_label.setStyleSheet(f"color: {Colors.SUCCESS}; background: transparent;")
            self._predicate_layout.addWidget(seek_label)
        
        if op.predicates:
            pred_label = QLabel(f"🔍 Where: {op.predicates}")
            pred_label.setWordWrap(True)
            pred_label.setStyleSheet(f"color: {Colors.WARNING}; background: transparent;")
            self._predicate_layout.addWidget(pred_label)
        
        if not op.seek_predicates and not op.predicates:
            na_label = QLabel("N/A")
            na_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; background: transparent;")
            self._predicate_layout.addWidget(na_label)
        
        # Uyarılar
        if op.warnings:
            for warning in op.warnings:
                w_label = QLabel(f"⚠️ {warning.message}")
                w_label.setWordWrap(True)
                w_label.setStyleSheet(f"color: {Colors.ERROR}; background: transparent;")
                self._warnings_layout.addWidget(w_label)
        else:
            ok_label = QLabel("✅ No warnings")
            ok_label.setStyleSheet(f"color: {Colors.SUCCESS}; background: transparent;")
            self._warnings_layout.addWidget(ok_label)

    def _update_plan_stability(self) -> None:
        """Plan stabilite görünümünü güncelle"""
        self._clear_layout(self._plan_stability_layout, keep_first=True)
        if not self._plan_stability:
            na_label = QLabel("N/A")
            na_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; background: transparent;")
            self._plan_stability_layout.addWidget(na_label)
            return

        plan_count = self._plan_count or 0
        if self._plan_stability == PlanStability.PROBLEM:
            text = f"🔴 Problem ({plan_count} plans) - Multiple plans detected - possible parameter sniffing"
            style = """
                color: #b91c1c;
                font-size: 11px;
                font-weight: 600;
                background-color: #fef2f2;
                border: 1px solid #fee2e2;
                border-radius: 6px;
                padding: 8px 10px;
            """
        elif self._plan_stability == PlanStability.ATTENTION:
            text = f"🟡 Attention ({plan_count} plans) - Plan changes detected"
            style = """
                color: #92400e;
                font-size: 11px;
                font-weight: 600;
                background-color: #fffbeb;
                border: 1px solid #fef3c7;
                border-radius: 6px;
                padding: 8px 10px;
            """
        else:
            text = "✅ Stable - single plan detected"
            style = """
                color: #047857;
                font-size: 11px;
                font-weight: 600;
                background-color: #ecfdf5;
                border: 1px solid #d1fae5;
                border-radius: 6px;
                padding: 8px 10px;
            """

        plan_label = QLabel(text)
        plan_label.setWordWrap(True)
        plan_label.setStyleSheet(style)
        self._plan_stability_layout.addWidget(plan_label)
    
    def _add_metric_row(self, layout: QVBoxLayout, name: str, value: str, is_warning: bool = False) -> None:
        """Metrik satırı ekle"""
        row = QHBoxLayout()
        row.setSpacing(8)
        
        name_label = QLabel(f"{name}:")
        name_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        name_label.setMinimumWidth(100)
        row.addWidget(name_label)
        
        value_label = QLabel(value)
        color = Colors.WARNING if is_warning else Colors.TEXT_PRIMARY
        value_label.setStyleSheet(f"font-weight: 600; color: {color}; background: transparent;")
        row.addWidget(value_label)
        row.addStretch()
        
        layout.addLayout(row)
    
    def _add_info_row(self, layout: QVBoxLayout, name: str, value: str) -> None:
        """Bilgi satırı ekle"""
        row = QHBoxLayout()
        row.setSpacing(8)
        
        name_label = QLabel(f"{name}:")
        name_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        name_label.setMinimumWidth(80)
        row.addWidget(name_label)
        
        value_label = QLabel(value or "N/A")
        value_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        row.addWidget(value_label)
        row.addStretch()
        
        layout.addLayout(row)
    
    def _clear_layout(self, layout: QVBoxLayout, keep_first: bool = False) -> None:
        """Layout'u temizle"""
        start = 1 if keep_first else 0
        while layout.count() > start:
            item = layout.takeAt(start)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())


class MissingIndexPanel(QWidget):
    """Missing index önerilerini gösteren panel"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._indexes: List[MissingIndex] = []
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {Colors.BACKGROUND}; }}")
        
        self._content = QWidget()
        self._content.setStyleSheet(f"background: {Colors.BACKGROUND};")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(12)
        self._content_layout.addStretch()
        
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)
    
    def set_indexes(self, indexes: List[MissingIndex]) -> None:
        """Missing index'leri ayarla"""
        self._indexes = indexes
        self._update_view()
    
    def _update_view(self) -> None:
        """Görünümü güncelle"""
        # Temizle
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self._indexes:
            no_data = QLabel("✅ No missing index recommendations")
            no_data.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 14px; padding: 20px;")
            self._content_layout.insertWidget(0, no_data)
            return
        
        for idx, mi in enumerate(self._indexes):
            card = self._create_index_card(mi, idx + 1)
            self._content_layout.insertWidget(self._content_layout.count() - 1, card)
    
    def _create_index_card(self, mi: MissingIndex, number: int) -> QFrame:
        """Index öneri kartı oluştur"""
        card = QFrame()
        card.setObjectName("indexCard")
        card.setStyleSheet(f"""
            QFrame#indexCard {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-left: 4px solid {Colors.SUCCESS};
                border-radius: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        
        # Başlık
        title = QLabel(f"#{number} - {mi.schema_name}.{mi.table_name}")
        title.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Colors.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(title)
        
        # Impact
        impact_row = QHBoxLayout()
        impact_label = QLabel("Impact:")
        impact_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
        impact_row.addWidget(impact_label)
        
        impact_bar = QProgressBar()
        impact_bar.setMaximum(100)
        impact_bar.setValue(int(mi.impact))
        impact_bar.setTextVisible(True)
        impact_bar.setFormat(f"{mi.impact:.1f}%")
        impact_bar.setMaximumHeight(22)
        impact_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.BORDER};
                border: none;
                border-radius: 6px;
                text-align: center;
                color: white;
                font-weight: 600;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.SUCCESS};
                border-radius: 6px;
            }}
        """)
        impact_row.addWidget(impact_bar, 1)
        layout.addLayout(impact_row)
        
        # Kolonlar
        if mi.equality_columns:
            eq_label = QLabel(f"🎯 Equality: {', '.join(mi.equality_columns)}")
            eq_label.setStyleSheet(f"color: {Colors.PRIMARY}; background: transparent;")
            layout.addWidget(eq_label)
        
        if mi.inequality_columns:
            ineq_label = QLabel(f"📊 Inequality: {', '.join(mi.inequality_columns)}")
            ineq_label.setStyleSheet(f"color: {Colors.WARNING}; background: transparent;")
            layout.addWidget(ineq_label)
        
        if mi.include_columns:
            inc_label = QLabel(f"📎 Include: {', '.join(mi.include_columns)}")
            inc_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; background: transparent;")
            layout.addWidget(inc_label)
        
        # CREATE INDEX statement
        stmt_edit = QTextEdit()
        stmt_edit.setPlainText(mi.create_statement)
        stmt_edit.setReadOnly(True)
        stmt_edit.setMaximumHeight(80)
        stmt_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1E293B;
                color: #E2E8F0;
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }}
        """)
        layout.addWidget(stmt_edit)
        
        # Copy button
        copy_btn = QPushButton("📋 Kopyala")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setFixedWidth(100)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        copy_btn.clicked.connect(lambda: self._copy_statement(mi.create_statement))
        layout.addWidget(copy_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        return card
    
    def _copy_statement(self, text: str) -> None:
        """Metni panoya kopyala"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)


class PlanViewerWidget(QWidget):
    """
    Tam execution plan görüntüleyici
    
    İçerir:
    - Plan tree view
    - Operatör detay paneli
    - Missing index önerileri
    - Plan uyarıları
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._plan: Optional[ExecutionPlan] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {Colors.BACKGROUND};
                border: none;
            }}
            QTabBar::tab {{
                background-color: transparent;
                border: none;
                border-bottom: 3px solid transparent;
                padding: 12px 20px;
                color: {Colors.TEXT_SECONDARY};
                font-weight: 500;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: {Colors.PRIMARY};
                border-bottom-color: {Colors.PRIMARY};
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                color: {Colors.TEXT_PRIMARY};
                background-color: rgba(79, 70, 229, 0.04);
            }}
        """)
        
        # Tab 1: Plan Tree + Detail
        plan_page = QWidget()
        plan_page.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        plan_layout = QHBoxLayout(plan_page)
        plan_layout.setContentsMargins(0, 8, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")
        
        # Sol: Tree
        self._tree_widget = PlanTreeWidget()
        self._tree_widget.operator_selected.connect(self._on_operator_selected)
        splitter.addWidget(self._tree_widget)
        
        # Sağ: Detail
        self._detail_panel = OperatorDetailPanel()
        splitter.addWidget(self._detail_panel)
        
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        plan_layout.addWidget(splitter)
        self._tabs.addTab(plan_page, "📊 Execution Plan")
        
        # Tab 2: Missing Indexes
        self._missing_panel = MissingIndexPanel()
        self._tabs.addTab(self._missing_panel, "📈 Missing Indexes")
        
        # Tab 3: Warnings
        warnings_page = QWidget()
        warnings_page.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        warnings_layout = QVBoxLayout(warnings_page)
        warnings_layout.setContentsMargins(16, 16, 16, 16)
        
        self._warnings_text = QTextEdit()
        self._warnings_text.setReadOnly(True)
        self._warnings_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                padding: 12px;
                font-size: 13px;
            }}
        """)
        self._warnings_text.setPlaceholderText("Plan warnings will appear here")
        warnings_layout.addWidget(self._warnings_text)
        
        self._tabs.addTab(warnings_page, "⚠️ Warnings")
        
        layout.addWidget(self._tabs)
    
    def set_plan(self, plan: Optional[ExecutionPlan]) -> None:
        """Planı ayarla"""
        self._plan = plan
        
        # Tree'yi güncelle
        self._tree_widget.set_plan(plan)
        
        # Detail'i temizle
        self._detail_panel.set_operator(None)
        
        # Missing indexes
        if plan:
            self._missing_panel.set_indexes(plan.missing_indexes)
            
            # Tab badge'lerini güncelle
            mi_count = len(plan.missing_indexes)
            if mi_count > 0:
                self._tabs.setTabText(1, f"📈 Missing Indexes ({mi_count})")
            else:
                self._tabs.setTabText(1, "📈 Missing Indexes")
            
            # Warnings
            warning_count = len(plan.warnings)
            if warning_count > 0:
                self._tabs.setTabText(2, f"⚠️ Warnings ({warning_count})")
                self._update_warnings_view(plan.warnings)
            else:
                self._tabs.setTabText(2, "⚠️ Warnings")
                self._warnings_text.setMarkdown(
                    "✅ **No plan warnings**\n\nNo warnings were detected in the execution plan."
                )
        else:
            self._missing_panel.set_indexes([])
            self._tabs.setTabText(1, "📈 Missing Indexes")
            self._tabs.setTabText(2, "⚠️ Warnings")
            self._warnings_text.clear()

    def set_plan_stability(self, plan_stability: Optional[PlanStability], plan_count: Optional[int]) -> None:
        """Plan stabilite bilgisini detay paneline ilet"""
        self._detail_panel.set_plan_stability(plan_stability, plan_count)
    
    def _on_operator_selected(self, operator: PlanOperator) -> None:
        """Operatör seçildiğinde"""
        self._detail_panel.set_operator(operator)
    
    def _update_warnings_view(self, warnings: List[PlanWarning]) -> None:
        """Uyarıları güncelle"""
        text = "## ⚠️ Plan Warnings\n\n"
        for i, w in enumerate(warnings, 1):
            icon = "🔴" if w.severity == "warning" else "🟡"
            text += f"### {icon} Warning {i}\n{w.message}\n\n"
        
        self._warnings_text.setMarkdown(text)
