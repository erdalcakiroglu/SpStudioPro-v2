"""
SQL Performance AI Platform - Entry Point

AI-Powered SQL Server Performance Analysis and Optimization Tool
"""

import sys
import os
from pathlib import Path

# Add app to path for imports
APP_DIR = Path(__file__).parent
if str(APP_DIR.parent) not in sys.path:
    sys.path.insert(0, str(APP_DIR.parent))


def setup_environment() -> None:
    """Setup environment variables and paths"""
    # Enable high DPI scaling
    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
    
    # Windows: Enable ANSI colors in console
    if sys.platform == 'win32':
        os.system('')  # Enable VT100 escape sequences


def main() -> int:
    """Main application entry point"""
    
    # Setup environment first
    setup_environment()
    
    # Import PyQt6 after environment setup
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    
    # Import app modules
    from app.core.config import get_settings, ensure_app_dirs
    from app.core.logger import setup_logging, get_logger
    from app.ui.main_window import MainWindow
    from app.ui.theme import apply_theme
    from app import __version__, __app_name__
    
    # Ensure app directories exist
    app_dir = ensure_app_dirs()
    
    # Load settings
    settings = get_settings()
    
    # Setup logging
    setup_logging(
        level=settings.logging.level,
        log_dir=settings.logs_dir,
        file_enabled=settings.logging.file_enabled,
        max_file_size_mb=settings.logging.max_file_size_mb,
        backup_count=settings.logging.backup_count,
    )
    
    logger = get_logger('main')
    logger.info(f"Starting {__app_name__} v{__version__}")
    logger.info(f"App directory: {app_dir}")
    logger.info(f"Python version: {sys.version}")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("SQL Perf AI")
    
    # Set default font
    font = QFont("Segoe UI", settings.ui.font_size)
    app.setFont(font)
    
    # Apply theme
    apply_theme(settings.ui.theme)
    logger.info(f"Theme applied: {settings.ui.theme.value}")
    
    # Create and show main window
    try:
        window = MainWindow()
        window.show()
        logger.info("Main window displayed")
        
        # Run event loop
        exit_code = app.exec()
        
        logger.info(f"Application exiting with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        
        # Show error dialog
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\nPlease check the logs for details."
        )
        return 1


def run_debug() -> int:
    """Run in debug mode with additional logging"""
    os.environ['SQLPERFAI_LOGGING__LEVEL'] = 'DEBUG'
    return main()


if __name__ == "__main__":
    sys.exit(main())
