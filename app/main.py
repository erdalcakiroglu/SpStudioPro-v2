"""
SQL Performance AI Platform - Entry Point

AI-Powered SQL Server Performance Analysis and Optimization Tool
"""

import sys
import os
from pathlib import Path
import PyQt6

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
    from PyQt6.QtWidgets import QApplication, QDialog
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QFont
    
    # Import app modules
    from app.core.config import get_settings, ensure_app_dirs, update_settings
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
        retention_days=settings.logging.retention_days,
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
    
    # Set default font (guard against invalid point size)
    font = QFont("Segoe UI")
    try:
        font_size = int(getattr(settings.ui, "font_size", 0) or 0)
    except Exception:
        font_size = 0
    if font_size > 0:
        font.setPointSize(font_size)
    app.setFont(font)
    
    # Show splash screen first
    splash = None
    try:
        from app.ui.splash_screen import SplashScreen
        splash = SplashScreen()
        splash.show()
        splash.set_progress(5, "Başlatılıyor...")
    except Exception as e:
        logger.warning(f"Splash screen failed to load: {e}")

    # Apply theme
    apply_theme(settings.ui.theme)
    logger.info(f"Theme applied: {settings.ui.theme.value}")
    if splash:
        splash.set_progress(15, "Tema uygulanıyor...")
        # Smooth step-by-step progress during splash delay
        progress_timer = QTimer(splash)
        progress_timer.setInterval(200)
        progress_state: dict[str, float] = {"value": 15.0}
        progress_target = 90
        progress_steps = max(1, int(10_000 / progress_timer.interval()))
        progress_increment = (progress_target - progress_state["value"]) / progress_steps

        def _tick_progress() -> None:
            if not splash:
                return
            progress_state["value"] = min(
                progress_target, progress_state["value"] + progress_increment
            )
            splash.set_progress(int(progress_state["value"]))

        progress_timer.timeout.connect(_tick_progress)
        progress_timer.start()
    
    # Create and show main window (after splash delay)
    window = None

    def show_main_window() -> None:
        nonlocal window
        try:
            # Stop splash progress updates before showing main window
            if splash and hasattr(splash, "findChild"):
                for child in splash.findChildren(QTimer):
                    child.stop()
            # License check (first run)
            if not getattr(settings.ui, "license_accepted", False):
                from app.ui.license_dialog import LicenseDialog
                if splash:
                    splash.set_progress(70, "Lisans onayi bekleniyor...")
                license_dialog = LicenseDialog(require_accept=True)
                result = license_dialog.exec()
                if result != QDialog.DialogCode.Accepted or not license_dialog.accepted:
                    logger.info("License declined. Exiting application.")
                    app.quit()
                    return
                update_settings(ui={"license_accepted": True})
            # Create main window
            window = MainWindow()
            # Resize to 84% of screen (20% larger than 70%) and center
            screen = app.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                target_w = int(geom.width() * 0.84)
                target_h = int(geom.height() * 0.84)
                window.resize(target_w, target_h)
                x = geom.x() + (geom.width() - target_w) // 2
                y = geom.y() + (geom.height() - target_h) // 2
                window.move(x, y)
            if splash:
                splash.set_progress(80, "SQL Performance AI being ready...")
                splash.finish(window)
            else:
                window.show()
            logger.info("Main window displayed")
        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "Fatal Error",
                f"An unexpected error occurred:\n\n{str(e)}\n\nPlease check the logs for details."
            )
            app.quit()

    if splash:
        splash.set_progress(60, "SQL Performance AI being ready...")
        QTimer.singleShot(10_000, show_main_window)
    else:
        show_main_window()

    # Run event loop
    exit_code = app.exec()

    logger.info(f"Application exiting with code: {exit_code}")
    return exit_code


def run_debug() -> int:
    """Run in debug mode with additional logging"""
    os.environ['SQLPERFAI_LOGGING__LEVEL'] = 'DEBUG'
    return main()


if __name__ == "__main__":
    sys.exit(main())
