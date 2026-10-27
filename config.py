from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SmartApiConfig:
    api_key: str = "BW8tznBr"
    client_id: str = "M173002"
    mpin_or_pin: str = "7856"
    totp_secret: str = "T3ZSXQE2RXR4UIBVE5FP3COUTQ"


@dataclass
class AppDefaults:
    default_underlying: str = "NIFTY"
    strike_window_each_side: int = 10
    auto_select_current_expiry: bool = True
    max_watch_seconds: int = 300
    poll_interval_seconds: float = 0.5


@dataclass
class OrderDefaults:
    variety: str = "STOPLOSS"
    duration: str = "DAY"

    option_producttype: str = "CARRYFORWARD"
    future_producttype: str = "CARRYFORWARD"

    option_entry_ordertype: str = "STOPLOSS_LIMIT"
    future_entry_ordertype: str = "STOPLOSS_LIMIT"

    emergency_exit_producttype: str = "CARRYFORWARD"
    emergency_exit_ordertype: str = "MARKET"


@dataclass
class RiskControls:
    allow_partial_fill_exit_placement: bool = False
    retry_count: int = 3
    retry_delay_seconds: float = 0.5
    emergency_market_exit_if_sl_fails: bool = False


@dataclass
class DataSources:
    instrument_master_url: str = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
    use_order_update_websocket: bool = True
    use_market_data_websocket: bool = True


@dataclass
class AppConfig:
    smartapi: SmartApiConfig = field(default_factory=SmartApiConfig)
    defaults: AppDefaults = field(default_factory=AppDefaults)
    orders: OrderDefaults = field(default_factory=OrderDefaults)
    risk: RiskControls = field(default_factory=RiskControls)
    data: DataSources = field(default_factory=DataSources)
    option_exchange: Dict[str, str] = field(
        default_factory=lambda: {"NIFTY": "NFO", "SENSEX": "BFO", "CRUDEOILM": "MCX"})
    future_exchange: Dict[str, str] = field(
        default_factory=lambda: {"CRUDEOILM": "MCX"})


CONFIG = AppConfig()
