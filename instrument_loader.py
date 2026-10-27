from pathlib import Path
from datetime import datetime
import requests
import pandas as pd


class InstrumentLoader:
    def __init__(self, url, cache_file="instrument_master.json"):
        self.url = url
        self.cache_file = Path(cache_file)
        self.df = pd.DataFrame()

    def _download(self):
        headers = {"User-Agent": "Mozilla/5.0",
                   "Accept": "application/json,text/plain,*/*"}
        response = requests.get(self.url, headers=headers, timeout=(10, 180))
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise RuntimeError(
                f"Unexpected response type: {type(data).__name__}")
        self.cache_file.write_text(response.text, encoding="utf-8")
        print(
            f"Downloaded {len(data)} instruments at {datetime.now():%Y-%m-%d %H:%M:%S}")
        return data

    def load(self):
        try:
            data = self._download()
        except Exception as error:
            print(f"Live download failed: {error}")
            if not self.cache_file.exists():
                raise RuntimeError(
                    "No live instrument data and no cache file exists.") from error
            import json
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            print(f"Using cached file: {self.cache_file}")
        self.df = pd.DataFrame(data)
        return self.df

    def prepare(self):
        if self.df.empty:
            self.load()
        for col in ["exch_seg", "name", "symbol", "token", "expiry", "instrumenttype", "strike", "lotsize", "tick_size"]:
            if col not in self.df.columns:
                self.df[col] = ""
        expiry_text = self.df["expiry"].astype(str).str.strip()
        expiry_text = expiry_text.mask(
            expiry_text.isin(["", "0", "0.0", "nan", "None"]))
        parsed = pd.to_datetime(
            expiry_text, errors="coerce", format="mixed", dayfirst=True)
        self.df["expiry_dt"] = parsed
        self.df["strike_num"] = pd.to_numeric(
            self.df["strike"], errors="coerce").fillna(0) / 100
        return self.df

    def _base_filter(self, underlying, exchange):
        df = self.prepare()

        x = df[
            df["exch_seg"]
            .astype(str)
            .str.upper()
            .eq(exchange.upper())
        ].copy()

        symbol_upper = x["symbol"].astype(str).str.upper()
        name_upper = x["name"].astype(str).str.upper()
        underlying_upper = underlying.upper()

        if underlying_upper == "NIFTY":
            valid = name_upper.eq(
                "NIFTY") | symbol_upper.str.startswith("NIFTY")
            valid &= ~symbol_upper.str.startswith("NIFTYFPI")
            valid &= ~symbol_upper.str.startswith("NIFTYIT")
            valid &= ~symbol_upper.str.startswith("NIFTYBANK")
            x = x[valid]

        elif underlying_upper == "SENSEX":
            x = x[name_upper.eq("SENSEX")]

        elif underlying_upper == "CRUDEOILM":
            valid = (
                name_upper.eq("CRUDEOILM")
                | symbol_upper.str.startswith("CRUDEOILM")
            )
            x = x[valid]

        else:
            x = x[name_upper.eq(underlying_upper)]

        return x

    def expiries(self, underlying, exchange, mode):
        x = self._base_filter(underlying, exchange)
        pattern = "OPT" if mode.upper() == "OPTION" else "FUT"
        x = x[x["instrumenttype"].astype(
            str).str.upper().str.contains(pattern, na=False)]
        return sorted(x["expiry_dt"].dropna().dt.strftime("%Y-%m-%d").unique().tolist())

    def contracts(self, underlying, exchange, mode, expiry=None, option_type=None, atm=None, window=10):
        x = self._base_filter(underlying, exchange)
        pattern = "OPT" if mode.upper() == "OPTION" else "FUT"
        x = x[x["instrumenttype"].astype(
            str).str.upper().str.contains(pattern, na=False)]
        if option_type:
            x = x[x["symbol"].astype(str).str.upper(
            ).str.endswith(option_type.upper())]
        if expiry:
            x = x[x["expiry_dt"].dt.strftime("%Y-%m-%d").eq(expiry)]
        if atm is not None and mode.upper() == "OPTION":
            strikes = sorted(x["strike_num"].dropna().unique(
            ).tolist(), key=lambda v: abs(v - float(atm)))
            x = x[x["strike_num"].isin(strikes[:2 * window + 1])]
        return x.sort_values(["expiry_dt", "strike_num"], na_position="last")
