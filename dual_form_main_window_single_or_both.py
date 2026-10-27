from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QLabel,
    QCheckBox,
)

from models import Contract, OrderForm, ArmedOrder
from multi_order_manager import MultiOrderManager


class DualLegPanel(QGroupBox):
    def __init__(self, name, loader, service, manager, parent=None):
        super().__init__(name, parent)
        self.name = name
        self.loader = loader
        self.service = service
        self.manager = manager
        self.contract = None
        self.contract_rows = []
        self.spot_cache = None
        self.spot_cache_time = 0

        form = QFormLayout(self)
        self.mode = QComboBox()
        self.mode.addItems(["OPTION", "FUTURE"])
        self.expiry = QComboBox()
        self.option_type = QComboBox()
        self.option_type.addItems(["CE", "PE"])
        self.strike = QComboBox()
        self.ltp = QLineEdit()
        self.ltp.setReadOnly(True)
        self.quantity = QSpinBox()
        self.quantity.setRange(1, 100000)
        self.trigger = QLineEdit()
        self.limit = QLineEdit()
        self.target = QLineEdit()
        self.stop = QLineEdit()
        self.load = QPushButton("LOAD EXPIRIES")
        self.contracts_button = QPushButton("LOAD CONTRACTS")

        for label, widget in [
            ("Mode", self.mode),
            ("Expiry", self.expiry),
            ("Type", self.option_type),
            ("Strike", self.strike),
            ("LTP", self.ltp),
            ("Quantity", self.quantity),
            ("Trigger", self.trigger),
            ("Limit", self.limit),
            ("TP", self.target),
            ("SL", self.stop),
        ]:
            form.addRow(label, widget)

        form.addRow(self.load, self.contracts_button)
        self.mode.currentTextChanged.connect(
            self._mode_changed
        )
        self.option_type.currentTextChanged.connect(
            self.load_contracts
        )
        self.expiry.currentTextChanged.connect(
            self.load_contracts
        )
        self.strike.currentIndexChanged.connect(
            self.select_contract
        )
        self.load.clicked.connect(self.load_expiries)
        self.contracts_button.clicked.connect(
            self.load_contracts
        )
        self._mode_changed()

    def _exchange(self):
        if self.mode.currentText() == "FUTURE":
            return self.manager.config.future_exchange.get(
                self.name,
                "NFO",
            )
        return self.manager.config.option_exchange.get(
            self.name,
            "NFO",
        )

    def _mode_changed(self):
        future = self.mode.currentText() == "FUTURE"
        self.option_type.setEnabled(not future)
        self.strike.setEnabled(not future)
        self.expiry.clear()
        self.strike.clear()
        self.contract = None

    def load_expiries(self):
        self.load.setEnabled(False)
        try:
            expiries = self.loader.expiries(
                self.name,
                self._exchange(),
                self.mode.currentText(),
            )
            self.expiry.clear()
            self.expiry.addItems(expiries)
        except Exception as error:
            self.ltp.setText(f"ERROR: {error}")
        finally:
            self.load.setEnabled(True)

    def _spot_ltp(self):
        import time

        if (
            self.spot_cache is not None
            and time.time() - self.spot_cache_time < 5
        ):
            return self.spot_cache

        symbols = {
            "NIFTY": ("NSE", "Nifty 50", "99926000"),
            "SENSEX": ("BSE", "SENSEX", "99919000"),
        }
        exchange, symbol, token = symbols[self.name]
        response = self.service.ltp(
            exchange,
            symbol,
            token,
        )
        self.spot_cache = float(
            response["data"]["ltp"]
        )
        self.spot_cache_time = time.time()
        return self.spot_cache

    def load_contracts(self):
        if not self.expiry.currentText():
            return

        mode = self.mode.currentText()
        contracts = self.loader.contracts(
            underlying=self.name,
            exchange=self._exchange(),
            mode=mode,
            expiry=self.expiry.currentText(),
            option_type=(
                self.option_type.currentText()
                if mode == "OPTION"
                else None
            ),
            window=(
                self.manager.config.defaults
                .strike_window_each_side
            ),
        )
        rows = contracts.to_dict("records")

        if (
            self.name in ("NIFTY", "SENSEX")
            and mode == "OPTION"
        ):
            try:
                spot = self._spot_ltp()
                rows.sort(
                    key=lambda row: abs(
                        float(row["strike_num"]) - spot
                    )
                )
            except Exception:
                pass

        self.contract_rows = rows
        self.strike.clear()

        for row in rows:
            strike = row.get("strike_num", "")
            self.strike.addItem(
                f"{strike} | {row.get('symbol', '')}",
                row,
            )

        if self.strike.count():
            self.strike.setCurrentIndex(0)
            self.select_contract()

    def select_contract(self):
        self.contract = self.strike.currentData()
        if not self.contract:
            return

        row = self.contract
        try:
            response = self.service.ltp(
                row["exch_seg"],
                row["symbol"],
                str(row["token"]),
            )
            self.ltp.setText(
                f"{float(response['data']['ltp']):.2f}"
            )
        except Exception as error:
            self.ltp.setText(f"ERROR: {error}")

    def build_leg(self):
        if not self.contract:
            raise ValueError(
                f"Select {self.name} contract"
            )

        def number(widget, label):
            value = widget.text().strip()
            if not value:
                raise ValueError(
                    f"{self.name}: {label} required"
                )
            return float(value)

        row = self.contract
        contract = Contract(
            underlying=self.name,
            exchange=str(row["exch_seg"]),
            mode=self.mode.currentText(),
            expiry=self.expiry.currentText(),
            option_type=(
                self.option_type.currentText()
                if self.mode.currentText() == "OPTION"
                else None
            ),
            strike=row.get("strike_num"),
            tradingsymbol=str(row["symbol"]),
            symboltoken=str(row["token"]),
            tick_size=float(
                row.get("tick_size", 0) or 0
            ),
            lot_size=int(
                float(row.get("lotsize", 0) or 0)
            ),
        )
        form = OrderForm(
            transaction_type="BUY",
            quantity=self.quantity.value(),
            trigger_price=number(self.trigger, "Trigger"),
            limit_price=number(self.limit, "Limit"),
            tp_price=number(self.target, "TP"),
            sl_price=number(self.stop, "SL"),
        )
        armed = ArmedOrder(
            entry_order_id="",
            contract=contract,
            form=form,
            state="NEW",
        )
        return {
            "name": self.name,
            "contract": contract,
            "form": form,
            "armed": armed,
        }


class DualMainWindow(QWidget):
    def __init__(self, loader, service, manager, watcher):
        super().__init__()
        self.loader = loader
        self.service = service
        self.manager = manager
        self.watcher = watcher
        self.setWindowTitle(
            "NIFTY + SENSEX Entry Manager"
        )
        self.resize(1350, 850)

        self.nifty = DualLegPanel(
            "NIFTY", loader, service, manager
        )
        self.sensex = DualLegPanel(
            "SENSEX", loader, service, manager
        )

        self.nifty_enabled = QCheckBox(
            "Include NIFTY"
        )
        self.sensex_enabled = QCheckBox(
            "Include SENSEX"
        )
        self.nifty_enabled.setChecked(True)
        self.sensex_enabled.setChecked(True)

        self.place_both = QPushButton(
            "PLACE SELECTED ENTRIES TOGETHER"
        )
        self.disarm = QPushButton(
            "DISARM SELECTED PROTECTIONS"
        )
        self.disarm.setEnabled(False)
        self.status = QLabel("Status: Ready")
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        self.multi = MultiOrderManager(
            manager,
            watcher,
            self.log,
        )

        nifty_layout = QVBoxLayout()
        nifty_layout.addWidget(self.nifty_enabled)
        nifty_layout.addWidget(self.nifty)

        sensex_layout = QVBoxLayout()
        sensex_layout.addWidget(self.sensex_enabled)
        sensex_layout.addWidget(self.sensex)

        panels = QHBoxLayout()
        panels.addLayout(nifty_layout)
        panels.addLayout(sensex_layout)

        root = QVBoxLayout(self)
        root.addLayout(panels)
        root.addWidget(self.place_both)
        root.addWidget(self.disarm)
        root.addWidget(self.status)
        root.addWidget(self.log_box)

        self.place_both.clicked.connect(
            self.place_selected_entries
        )
        self.disarm.clicked.connect(
            self.disarm_selected
        )

    def log(self, message):
        self.log_box.append(str(message))

    def place_selected_entries(self):
        self.place_both.setEnabled(False)
        try:
            selected = []

            if self.nifty_enabled.isChecked():
                selected.append(self.nifty.build_leg())

            if self.sensex_enabled.isChecked():
                selected.append(self.sensex.build_leg())

            if not selected:
                raise ValueError(
                    "Select NIFTY or SENSEX first"
                )

            group = self.multi.place_group(
                "NIFTY_SENSEX",
                selected,
            )
            self.status.setText(
                f"Status: {group['state']}"
            )
            self.disarm.setEnabled(True)

        except Exception as error:
            self.log(f"ENTRY ERROR: {error}")
            self.status.setText(
                "Status: Entry failed"
            )
        finally:
            self.place_both.setEnabled(True)

    def disarm_selected(self):
        try:
            result = self.multi.disarm_group(
                "NIFTY_SENSEX"
            )
            self.log(f"DISARM RESULT: {result}")
            self.disarm.setEnabled(False)
        except Exception as error:
            self.log(f"DISARM ERROR: {error}")
