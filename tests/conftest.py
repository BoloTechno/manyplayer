import os
import gc
import pytest

# Ensure headless Qt operation in Linux test environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    """Single session-scoped QApplication to prevent PySide6 C++ destruction conflicts."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.closeAllWindows()
    app.processEvents()
    gc.collect()


@pytest.fixture(autouse=True)
def cleanup_widgets_after_each_test(qapp):
    yield
    qapp.closeAllWindows()
    qapp.processEvents()
    gc.collect()
