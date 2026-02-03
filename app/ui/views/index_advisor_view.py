"""
Index Advisor View - Modern Enterprise Design with AI Analysis
"""
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QFrame, QGraphicsDropShadowEffect,
    QPushButton, QSplitter, QTextEdit, QDialog, QScrollArea,
    QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QAction

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, CircleStatCard
from app.database.connection import get_connection_manager
from app.core.logger import get_logger

logger = get_logger("ui.index_advisor")


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that sorts using a numeric value when provided."""

    def __init__(self, text: str, numeric_value: Optional[float] = None):
        super().__init__(text)
        self._numeric_value = numeric_value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            if self._numeric_value is not None and other._numeric_value is not None:
                return self._numeric_value < other._numeric_value
        return super().__lt__(other)


class IndexAnalysisWorker(QThread):
    """Background worker for AI index analysis"""
    
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, index_data: Dict, parent=None):
        super().__init__(parent)
        self.index_data = index_data
    
    def run(self):
        import asyncio
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._analyze())
                self.finished.emit(result)
            finally:
                loop.close()
        except Exception as e:
            self.error.emit(str(e))
    
    async def _analyze(self) -> str:
        """Analyze index with AI"""
        from app.ai.analysis_service import AIAnalysisService
        
        try:
            d = self.index_data
            table_info = {
                "table_name": d.get("table", "N/A"),
                "row_count": "N/A",
                "size_mb": "N/A",
            }
            missing_index_dmv = {
                "equality_columns": d.get("equality", "N/A"),
                "inequality_columns": d.get("inequality", "N/A"),
                "included_columns": d.get("include", "N/A"),
                "user_seeks": d.get("seeks", 0),
                "avg_user_impact": d.get("impact", 0),
            }
            query_text = d.get("statement", "") or d.get("table", "")
            
            service = AIAnalysisService()
            response = await service.get_index_recommendations(
                query_text=query_text,
                table_info=table_info,
                missing_index_dmv=missing_index_dmv,
                existing_indexes=None
            )
            return response
        except Exception:
            return self._generate_fallback()
    
    def _build_prompt(self) -> str:
        d = self.index_data
        return f"""Index Analizi:
- Tablo: {d.get('table', 'N/A')}
- Equality Columns: {d.get('equality', 'N/A')}
- Inequality Columns: {d.get('inequality', 'N/A')}
- Include Columns: {d.get('include', 'N/A')}
- Tahmini Etki: %{d.get('impact', 0):.0f}
- Seek Sayısı: {d.get('seeks', 0):,}
- Scan Sayısı: {d.get('scans', 0):,}

Bu index oluşturulmalı mı? Analiz et."""
    
    def _generate_fallback(self) -> str:
        d = self.index_data
        try:
            impact = float(d.get('impact', 0) or 0)
        except (TypeError, ValueError):
            impact = 0
        try:
            seeks = int(d.get('seeks', 0) or 0)
        except (TypeError, ValueError):
            seeks = 0
        
        analysis = f"""## 📊 Index Analizi

**Tablo:** {d.get('table', 'N/A')}

### Değerlendirme
"""
        # Impact assessment
        if impact >= 80:
            analysis += f"- ✅ **Yüksek Etki (%{impact:.0f})**: Bu index önemli performans kazanımı sağlayabilir\n"
        elif impact >= 50:
            analysis += f"- 🟡 **Orta Etki (%{impact:.0f})**: Değerlendirmeye değer bir öneri\n"
        else:
            analysis += f"- 🟠 **Düşük Etki (%{impact:.0f})**: Dikkatli değerlendirin\n"
        
        # Seek analysis
        if seeks > 10000:
            analysis += f"- ✅ **Yüksek Kullanım ({seeks:,} seek)**: Sık kullanılan bir sorgu pattern'i\n"
        elif seeks > 1000:
            analysis += f"- 🟡 **Orta Kullanım ({seeks:,} seek)**: Makul seviyede kullanım\n"
        else:
            analysis += f"- 🟠 **Düşük Kullanım ({seeks:,} seek)**: Az kullanılıyor olabilir\n"
        
        analysis += f"""
### Öneriler
1. Index oluşturmadan önce tablo boyutunu kontrol edin
2. Mevcut index'lerle çakışma olup olmadığını doğrulayın
3. Yazma yoğunluğunu değerlendirin (INSERT/UPDATE maliyeti)
"""
        return analysis


class IndexAdvisorView(BaseView):
    """Index Advisor view with modern enterprise design and AI analysis"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_indexes: List[Dict] = []
    
    @property
    def view_title(self) -> str:
        return "Index Advisor"
    
    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        # Title section
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(16)
        
        # Title and subtitle
        title_text_layout = QVBoxLayout()
        title_text_layout.setSpacing(4)
        
        title = QLabel("📊 Index Advisor")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_text_layout.addWidget(title)
        
        self.status_label = QLabel("Veritabanına bağlanın")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        self.status_label.setFont(QFont("Segoe UI", 13))
        title_text_layout.addWidget(self.status_label)
        
        title_layout.addLayout(title_text_layout)
        title_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh)
        title_layout.addWidget(refresh_btn)
        
        self._main_layout.addWidget(title_container)
        self._main_layout.addSpacing(20)
        
        # Summary cards
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)
        
        self._total_card = self._create_summary_card("Toplam Öneri", "0", Colors.PRIMARY)
        self._high_impact_card = self._create_summary_card("Yüksek Etkili", "0", Colors.SUCCESS)
        self._estimated_gain_card = self._create_summary_card("Tahmini Kazanım", "%0", Colors.WARNING)
        
        summary_layout.addWidget(self._total_card)
        summary_layout.addWidget(self._high_impact_card)
        summary_layout.addWidget(self._estimated_gain_card)
        summary_layout.addStretch()
        
        self._main_layout.addLayout(summary_layout)
        self._main_layout.addSpacing(20)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")
        
        # Left: Table card
        table_card = QFrame()
        table_card.setObjectName("tableCard")
        table_card.setStyleSheet(f"""
            QFrame#tableCard {{
                background-color: {Colors.SURFACE};
                border-radius: 16px;
                border: 1px solid {Colors.BORDER};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(15, 23, 42, 15))
        table_card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)
        
        # Card header
        card_header = QLabel("Missing Index Önerileri")
        card_header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 600;")
        card_layout.addWidget(card_header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Tablo", "Etki %", "Equality", "Inequality", "Include", "Seeks"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setFixedHeight(32)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.itemClicked.connect(self._on_index_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.SURFACE};
                border: none;
                gridline-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY}18;
            }}
            QHeaderView::section {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                padding: 6px 8px;
                border: none;
                border-bottom: 2px solid {Colors.BORDER};
                font-weight: 600;
                font-size: 12px;
            }}
        """)
        card_layout.addWidget(self.table)
        
        splitter.addWidget(table_card)
        
        # Right: Detail panel
        detail_card = QFrame()
        detail_card.setObjectName("detailCard")
        detail_card.setStyleSheet(f"""
            QFrame#detailCard {{
                background-color: {Colors.SURFACE};
                border-radius: 16px;
                border: 1px solid {Colors.BORDER};
            }}
        """)
        
        detail_shadow = QGraphicsDropShadowEffect()
        detail_shadow.setBlurRadius(20)
        detail_shadow.setXOffset(0)
        detail_shadow.setYOffset(4)
        detail_shadow.setColor(QColor(15, 23, 42, 15))
        detail_card.setGraphicsEffect(detail_shadow)
        
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(20, 20, 20, 20)
        detail_layout.setSpacing(12)
        
        # Detail header
        detail_header = QLabel("📝 Index Detayı")
        detail_header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 600;")
        detail_layout.addWidget(detail_header)
        
        # CREATE INDEX script
        script_label = QLabel("CREATE INDEX Script:")
        script_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 500;")
        detail_layout.addWidget(script_label)
        
        self._script_text = QTextEdit()
        self._script_text.setReadOnly(True)
        self._script_text.setPlaceholderText("Bir index seçin...")
        self._script_text.setMaximumHeight(150)
        self._script_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1E293B;
                color: #E2E8F0;
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        detail_layout.addWidget(self._script_text)
        
        # Copy button
        copy_btn = QPushButton("📋 Script'i Kopyala")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
            }}
        """)
        copy_btn.clicked.connect(self._copy_script)
        detail_layout.addWidget(copy_btn)
        
        # AI Analysis section
        ai_header = QHBoxLayout()
        ai_label = QLabel("🤖 AI Analiz")
        ai_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        ai_header.addWidget(ai_label)
        
        self._ai_btn = QPushButton("Analiz Et")
        self._ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        self._ai_btn.clicked.connect(self._run_ai_analysis)
        ai_header.addWidget(self._ai_btn)
        ai_header.addStretch()
        
        detail_layout.addLayout(ai_header)
        
        self._ai_result = QTextEdit()
        self._ai_result.setReadOnly(True)
        self._ai_result.setPlaceholderText("Index seçip 'Analiz Et' butonuna tıklayın...")
        self._ai_result.setStyleSheet(f"""
            QTextEdit {{
                background-color: #F8FAFC;
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }}
        """)
        detail_layout.addWidget(self._ai_result, 1)
        
        splitter.addWidget(detail_card)
        splitter.setSizes([600, 400])
        
        self._main_layout.addWidget(splitter, 1)
    
    def _create_summary_card(self, title: str, value: str, color: str) -> CircleStatCard:
        """Create a circle summary stat card - GUI-05 style"""
        return CircleStatCard(title, value, color)
    
    def _update_summary_card(self, card: CircleStatCard, value: str):
        """Update summary card value"""
        card.update_value(value)
    
    def on_show(self):
        if not self._is_initialized:
            return
        self.refresh()
        
    def refresh(self):
        if not self._is_initialized:
            return
        conn = get_connection_manager().active_connection
        if not conn or not conn.is_connected:
            self.status_label.setText("Lütfen önce bir veritabanına bağlanın.")
            self.status_label.setStyleSheet(f"color: {Colors.WARNING}; font-size: 14px; background: transparent;")
            return
            
        self.status_label.setText(f"📊 {conn.profile.database} için eksik index önerileri")
        self.status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 14px; background: transparent;")
        
        try:
            query = """
            SELECT TOP 30
                OBJECT_NAME(d.object_id) AS table_name,
                OBJECT_SCHEMA_NAME(d.object_id) AS schema_name,
                d.equality_columns,
                d.inequality_columns,
                d.included_columns,
                s.avg_user_impact,
                s.user_seeks,
                s.user_scans,
                s.last_user_seek,
                d.statement
            FROM sys.dm_db_missing_index_details AS d
            JOIN sys.dm_db_missing_index_groups AS g ON d.index_handle = g.index_handle
            JOIN sys.dm_db_missing_index_group_stats AS s ON g.index_group_handle = s.group_handle
            WHERE d.database_id = DB_ID()
            ORDER BY s.avg_user_impact * s.user_seeks DESC
            """
            results = conn.execute_query(query)
            
            self._current_indexes = []
            self.table.setRowCount(len(results))
            
            high_impact_count = 0
            total_impact = 0
            
            self.table.setSortingEnabled(False)
            for i, row in enumerate(results):
                idx_data = {
                    'table': row.get('table_name', ''),
                    'schema': row.get('schema_name', ''),
                    'equality': row.get('equality_columns', ''),
                    'inequality': row.get('inequality_columns', ''),
                    'include': row.get('included_columns', ''),
                    'impact': row.get('avg_user_impact', 0) or 0,
                    'seeks': row.get('user_seeks', 0) or 0,
                    'scans': row.get('user_scans', 0) or 0,
                    'statement': row.get('statement', '')
                }
                self._current_indexes.append(idx_data)
                
                impact = idx_data['impact']
                total_impact += impact
                if impact >= 70:
                    high_impact_count += 1
                
                # Table cells
                self.table.setItem(i, 0, QTableWidgetItem(str(idx_data['table'])))
                
                impact_item = NumericTableWidgetItem(f"{impact:.0f}%", float(impact))
                if impact >= 70:
                    impact_item.setForeground(QColor(Colors.SUCCESS))
                elif impact >= 40:
                    impact_item.setForeground(QColor(Colors.WARNING))
                self.table.setItem(i, 1, impact_item)
                
                self.table.setItem(i, 2, QTableWidgetItem(str(idx_data['equality'] or '-')))
                self.table.setItem(i, 3, QTableWidgetItem(str(idx_data['inequality'] or '-')))
                self.table.setItem(i, 4, QTableWidgetItem(str(idx_data['include'] or '-')))
                seeks_item = NumericTableWidgetItem(f"{idx_data['seeks']:,}", float(idx_data['seeks']))
                self.table.setItem(i, 5, seeks_item)

                numeric_font = QFont("Segoe UI", 10)
                impact_item.setFont(numeric_font)
                seeks_item.setFont(numeric_font)
            
            # Update summary cards
            self._update_summary_card(self._total_card, str(len(results)))
            self._update_summary_card(self._high_impact_card, str(high_impact_count))
            avg_impact = total_impact / len(results) if results else 0
            self._update_summary_card(self._estimated_gain_card, f"%{avg_impact:.0f}")
            self.table.setSortingEnabled(True)
                
        except Exception as e:
            logger.error(f"Failed to load index recommendations: {e}")
            self.status_label.setText(f"Hata: {str(e)}")
            self.status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 14px; background: transparent;")
    
    def _on_index_selected(self, item):
        """Handle index selection"""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._current_indexes):
            return
        
        idx = self._current_indexes[row]
        script = self._generate_create_index_script(idx)
        self._script_text.setPlainText(script)
        self._ai_result.clear()
    
    def _generate_create_index_script(self, idx: Dict) -> str:
        """Generate CREATE INDEX script"""
        table = idx.get('table', 'TableName')
        schema = idx.get('schema', '') or 'dbo'
        equality = idx.get('equality', '')
        inequality = idx.get('inequality', '')
        include = idx.get('include', '')
        
        if "." in table and not idx.get('schema'):
            parts = table.split(".", 1)
            schema = parts[0].strip("[]")
            table = parts[1].strip("[]")
        
        # Build column list
        columns = []
        if equality:
            columns.extend([c.strip() for c in equality.split(',')])
        if inequality:
            columns.extend([c.strip() for c in inequality.split(',')])
        
        col_str = ', '.join(columns) if columns else '[Column1]'
        
        # Build index name
        idx_name = f"IX_{table}_" + '_'.join([c.replace('[', '').replace(']', '') for c in columns[:2]])
        
        script = f"""CREATE NONCLUSTERED INDEX [{idx_name}]
ON [{schema}].[{table}] ({col_str})"""
        
        if include:
            script += f"\nINCLUDE ({include})"
        
        script += "\nWITH (ONLINE = ON, FILLFACTOR = 90);"
        
        return script
    
    def _copy_script(self):
        """Copy script to clipboard"""
        from PyQt6.QtWidgets import QApplication
        script = self._script_text.toPlainText()
        if script:
            QApplication.clipboard().setText(script)
    
    def _show_context_menu(self, position):
        """Show context menu"""
        row = self.table.currentRow()
        if row < 0:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 10px 20px;
                color: {Colors.TEXT_PRIMARY};
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)
        
        copy_action = QAction("📋 Script'i Kopyala", self)
        copy_action.triggered.connect(self._copy_script)
        menu.addAction(copy_action)
        
        ai_action = QAction("🤖 AI ile Analiz Et", self)
        ai_action.triggered.connect(self._run_ai_analysis)
        menu.addAction(ai_action)
        
        menu.exec(self.table.mapToGlobal(position))
    
    def _run_ai_analysis(self):
        """Run AI analysis on selected index"""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._current_indexes):
            self._ai_result.setMarkdown("⚠️ Lütfen önce bir index seçin.")
            return
        
        idx = self._current_indexes[row]
        self._ai_btn.setEnabled(False)
        self._ai_result.setMarkdown("⏳ AI analizi yapılıyor...")
        
        self._worker = IndexAnalysisWorker(idx)
        self._worker.finished.connect(self._on_ai_finished)
        self._worker.error.connect(self._on_ai_error)
        self._worker.start()
    
    def _on_ai_finished(self, result: str):
        """Handle AI analysis completion"""
        self._ai_result.setMarkdown(result)
        self._ai_btn.setEnabled(True)
    
    def _on_ai_error(self, error: str):
        """Handle AI analysis error"""
        self._ai_result.setMarkdown(f"⚠️ Hata: {error}")
        self._ai_btn.setEnabled(True)
