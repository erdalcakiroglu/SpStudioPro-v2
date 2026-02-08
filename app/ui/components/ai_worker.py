import asyncio
from PyQt6.QtCore import QThread, pyqtSignal
from app.ai.analysis_service import AIAnalysisService
from app.models.query_stats_models import QueryStats
from typing import Optional, Dict, Any

class AIAnalysisWorker(QThread):
    """AI analizi için arka plan işçisi - Log destekli"""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, str)  # (stage, message)
    
    def __init__(self, query_stats: QueryStats = None, plan_xml: Optional[str] = None, context: Dict[str, Any] = None):
        super().__init__()
        self.query_stats = query_stats
        self.plan_xml = plan_xml
        self._context = context
        self.service = AIAnalysisService()
        
    def run(self):
        """Analizi başlatır"""
        try:
            # Stage: Context hazırlanıyor
            self.progress.emit('context', 'Preparing query context...')
            
            # Async servisi senkron QThread içinde çalıştırmak için yeni bir event loop kullanıyoruz
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Stage: AI servisine bağlanılıyor
            self.progress.emit('connect', 'Connecting to AI service...')
            
            # Stage: Analiz ediliyor
            self.progress.emit('analyze', 'Analyzing query...')
            
            if self.query_stats:
                result = loop.run_until_complete(
                    self.service.analyze_query(self.query_stats, self.plan_xml)
                )
            elif self._context:
                # Context-based analysis için basit prompt
                self.progress.emit('metrics', 'Evaluating metrics...')
                result = loop.run_until_complete(
                    self._analyze_from_context()
                )
            else:
                raise ValueError("No query_stats or context provided")
            
            # Stage: Optimizasyon önerileri
            self.progress.emit('optimize', 'Preparing optimization recommendations...')

            # Stage: Formatlanıyor
            self.progress.emit('format', 'Formatting results...')
            
            self.finished.emit(result)
            loop.close()
        except Exception as e:
            self.error.emit(str(e))
    
    async def _analyze_from_context(self) -> str:
        """Context dictionary'den analiz yap"""
        if not self._context:
            raise ValueError("No context provided")

        return await self.service.analyze_from_context(self._context)
