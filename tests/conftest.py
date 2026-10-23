"""Shared test setup. Qt runs on the offscreen platform so tests never open windows."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """The one QApplication for the test run. Widgets and QPixmap need it."""
    return QApplication.instance() or QApplication([])
