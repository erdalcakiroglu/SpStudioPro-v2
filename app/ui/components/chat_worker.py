"""
Chat Worker - Background thread for AI chat processing
"""

import asyncio
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal

from app.ai.chat_service import get_chat_service
from app.core.logger import get_logger

logger = get_logger('ui.chat_worker')


class ChatWorker(QThread):
    """
    Worker thread for processing chat messages with AI
    """
    
    # Signals
    response_ready = pyqtSignal(str)  # AI response text
    error_occurred = pyqtSignal(str)  # Error message
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self._message = message
        self._chat_service = get_chat_service()
    
    def run(self):
        """Process the message in background thread"""
        self.processing_started.emit()
        
        try:
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Process message
                response = loop.run_until_complete(
                    self._chat_service.process_message(self._message)
                )
                
                self.response_ready.emit(response)
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Chat worker error: {e}")
            self.error_occurred.emit(str(e))
        
        finally:
            self.processing_finished.emit()
