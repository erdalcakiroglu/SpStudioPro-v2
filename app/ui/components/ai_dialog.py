from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QTextEdit, QLabel, QProgressBar, QFrame,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from app.ui.theme import Colors


class AIAnalysisDialog(QDialog):
    """AI Analiz sonuçlarını gösteren dialog - Log panelli"""
    
    # Analiz aşamaları
    STAGES = {
        'init': ('🔄', 'Başlatılıyor...'),
        'context': ('📋', 'Sorgu bağlamı hazırlanıyor...'),
        'connect': ('🔗', 'AI servisine bağlanılıyor...'),
        'analyze': ('🧠', 'Sorgu analiz ediliyor...'),
        'metrics': ('📊', 'Metrikler değerlendiriliyor...'),
        'optimize': ('⚡', 'Optimizasyon önerileri hazırlanıyor...'),
        'format': ('📝', 'Sonuç formatlanıyor...'),
        'complete': ('✅', 'Analiz tamamlandı!'),
        'error': ('❌', 'Hata oluştu'),
    }

    STAGE_ORDER = [
        'init', 'context', 'connect', 'analyze', 'metrics', 'optimize', 'format', 'complete'
    ]
    
    def __init__(self, context: Union[str, Dict[str, Any]], parent=None, auto_start: bool = True):
        super().__init__(parent)
        
        # Handle both string (query_name) and dict (context) inputs
        if isinstance(context, str):
            self.query_name = context
            self._context = {'query_name': context}
        else:
            self.query_name = context.get('query_name', 'Query')
            self._context = context
        
        self._result: Optional[str] = None
        self._log_entries: List[str] = []
        self._current_stage: str = 'init'
        self._worker = None
        self._auto_start = auto_start
        self._stage_progress = {stage: idx for idx, stage in enumerate(self.STAGE_ORDER)}
        
        self.setWindowTitle(f"AI Analizi: {self.query_name}")
        self.setMinimumSize(900, 650)
        self._setup_ui()
        
        # İlk log entry
        self.add_log('init')
        
        # Auto-start analysis if enabled
        if auto_start:
            QTimer.singleShot(100, self._start_analysis)
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Başlık
        header = QHBoxLayout()
        self.title_label = QLabel(f"🤖 AI Performans Analizi: {self.query_name}")
        self.title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {Colors.SECONDARY};")
        header.addWidget(self.title_label)
        header.addStretch()
        
        # Current stage indicator
        self._stage_label = QLabel("🔄 Başlatılıyor...")
        self._stage_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 12px;
                padding: 4px 12px;
                background-color: {Colors.PRIMARY_LIGHT};
                border-radius: 12px;
            }}
        """)
        header.addWidget(self._stage_label)
        layout.addLayout(header)
        
        # Yükleme göstergesi
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet(f"""
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
        layout.addWidget(self.progress_bar)

        # Bilgilendirme alanı
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
        self._info_label = QLabel("İşlem adımı: Başlatılıyor... (0%)")
        self._info_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        info_layout.addWidget(self._info_label)
        info_layout.addStretch()
        layout.addWidget(info_frame)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
                height: 8px;
            }
        """)
        
        # Sonuç alanı
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
        
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setPlaceholderText("AI analizi hazırlanıyor, lütfen bekleyin...")
        self.result_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                font-size: 13px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        result_layout.addWidget(self.result_area)
        splitter.addWidget(result_container)
        
        # Log paneli
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
        
        self._clear_log_btn = QPushButton("Temizle")
        self._clear_log_btn.setFixedHeight(22)
        self._clear_log_btn.setStyleSheet("""
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
        self._clear_log_btn.clicked.connect(self._clear_log)
        log_header.addWidget(self._clear_log_btn)
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
        splitter.addWidget(log_container)
        
        # Set splitter sizes (70% result, 30% log)
        splitter.setSizes([400, 150])
        layout.addWidget(splitter)
        
        # Butonlar
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Raporu Kaydet")
        self.save_btn.clicked.connect(self._save_report)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #f3f4f6;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_MUTED};
            }}
        """)

        self.copy_btn = QPushButton("📋 Metni Kopyala")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.copy_btn.setEnabled(False)
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #f3f4f6;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_MUTED};
            }}
        """)
        
        self.view_report_btn = QPushButton("📄 Raporu Gör")
        self.view_report_btn.clicked.connect(self.accept)
        self.view_report_btn.setVisible(False)
        self.view_report_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)

        self.close_btn = QPushButton("Kapat")
        self.close_btn.clicked.connect(self.reject)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #f3f4f6;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
            }}
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.copy_btn)
        button_layout.addWidget(self.view_report_btn)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
    
    def add_log(self, stage: str, message: str = None):
        """Log paneline yeni bir entry ekler"""
        self._current_stage = stage
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        icon, default_msg = self.STAGES.get(stage, ('ℹ️', message or 'İşlem devam ediyor...'))
        display_msg = message or default_msg
        
        # Color based on stage
        if stage == 'error':
            color = '#ef4444'
        elif stage == 'complete':
            color = '#22c55e'
        else:
            color = '#94a3b8'
        
        log_line = f'<span style="color: #64748b;">[{timestamp}]</span> <span style="color: {color};">{icon} {display_msg}</span>'
        self._log_entries.append(log_line)
        
        # Update log area
        self._log_area.setHtml('<br>'.join(self._log_entries))
        
        # Scroll to bottom
        scrollbar = self._log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Update stage label
        self._stage_label.setText(f"{icon} {display_msg}")

        # Update progress value for known stages
        if stage in self._stage_progress:
            idx = self._stage_progress[stage]
            total = max(len(self.STAGE_ORDER) - 1, 1)
            progress = int((idx / total) * 100)
            self.progress_bar.setValue(progress)
            self._info_label.setText(f"İşlem adımı: {display_msg} ({progress}%)")
        
        if stage == 'complete':
            self._stage_label.setStyleSheet(f"""
                QLabel {{
                    color: #166534;
                    font-size: 12px;
                    padding: 4px 12px;
                    background-color: #dcfce7;
                    border-radius: 12px;
                }}
            """)
        elif stage == 'error':
            self._stage_label.setStyleSheet(f"""
                QLabel {{
                    color: #991b1b;
                    font-size: 12px;
                    padding: 4px 12px;
                    background-color: #fef2f2;
                    border-radius: 12px;
                }}
            """)
    
    def _clear_log(self):
        """Log panelini temizler"""
        self._log_entries.clear()
        self._log_area.clear()
    
    def _start_analysis(self):
        """AI analizini başlat"""
        try:
            from app.ui.components.ai_worker import AIAnalysisWorker
            
            self.add_log('context', 'Sorgu bağlamı hazırlanıyor...')
            
            # Worker oluştur
            self._worker = AIAnalysisWorker(context=self._context)
            self._worker.progress.connect(self._on_worker_progress)
            self._worker.finished.connect(self._on_worker_finished)
            self._worker.error.connect(self._on_worker_error)
            
            # Worker'ı başlat
            self._worker.start()
            
        except ImportError as e:
            self.add_log('error', f'AI modülü yüklenemedi: {e}')
            self.set_error(f"AI modülü yüklenemedi: {e}")
        except Exception as e:
            self.add_log('error', str(e))
            self.set_error(str(e))
    
    def _on_worker_progress(self, stage: str, message: str):
        """Worker progress sinyali"""
        self.add_log(stage, message)
    
    def _on_worker_finished(self, result: str):
        """Worker tamamlandığında"""
        self.set_result(result)
    
    def _on_worker_error(self, error_msg: str):
        """Worker hata verdiğinde"""
        self.set_error(error_msg)
        
    def set_result(self, markdown_text: str):
        """Analiz sonucunu ekrana yansıtır"""
        self._result = markdown_text
        self.progress_bar.setValue(100)
        self.result_area.setMarkdown(markdown_text)
        self.copy_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.view_report_btn.setVisible(True)
        self.add_log('complete')
    
    def get_result(self) -> Optional[str]:
        """Return the analysis result"""
        return self._result
        
    def set_error(self, error_msg: str):
        """Hata mesajını gösterir"""
        self._result = None
        self.progress_bar.setValue(0)
        self.result_area.setText(f"❌ Hata: {error_msg}")
        self.result_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                font-size: 13px;
                color: #ef4444;
            }}
        """)
        self.add_log('error', error_msg)
        
    def _copy_to_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.result_area.toPlainText())
        self.add_log('init', 'Sonuç panoya kopyalandı')

    def _save_report(self):
        """Save the report to a file in formatted form."""
        if not self._result:
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
                content = self.result_area.toHtml()
            elif selected_filter.startswith("Text"):
                content = self.result_area.toPlainText()
            else:
                content = self._result

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.add_log('init', f'Rapor kaydedildi: {file_path}')
        except Exception as e:
            QMessageBox.warning(self, "Rapor", f"Rapor kaydedilemedi: {e}")
