import sys

from PySide6.QtWidgets import QApplication

from config import CONFIG
from smartapi_service import SmartApiService
from instrument_loader import InstrumentLoader
from order_manager import OrderManager
from order_watcher import OrderWatcher
from dual_form_main_window_single_or_both import (
    DualMainWindow,
)


def main():
    app = QApplication(sys.argv)

    service = SmartApiService(CONFIG)
    service.login()

    loader = InstrumentLoader(
        CONFIG.data.instrument_master_url
    )

    manager = OrderManager(
        service,
        CONFIG,
    )

    watcher = OrderWatcher(
        service,
        manager,
        CONFIG,
    )

    window = DualMainWindow(
        loader=loader,
        service=service,
        manager=manager,
        watcher=watcher,
    )

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
