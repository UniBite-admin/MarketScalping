from __future__ import annotations

import json
import os
import re
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


MARKET_RE = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+$")
DEFAULT_BASE_URL = "https://api.bitvavo.com/v2"
DEFAULT_SOURCE = "bitvavo_public_historical_trades"
MAX_LIMIT = 1000
MAX_WINDOW_MS = 24 * 60 * 60 * 1000
DEFAULT_ACCESS_WINDOW_MS = "10000"


@dataclass(frozen=True)
class BitvavoHistoricalTrade:
    trade_id: str
    event_time_utc: str
    market: str
    price: Decimal
    amount: Decimal
    side: str
    source: str = DEFAULT_SOURCE
    raw_timestamp_ms: int | None = None
    raw_payload_json: str | None = None

    def to_json_record(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "event_time_utc": self.event_time_utc,
            "market": self.market,
            "price": str(self.price),
            "amount": str(self.amount),
            "side": self.side,
            "source": self.source,
            "raw_timestamp_ms": self.raw_timestamp_ms,
            "raw_payload_json": self.raw_payload_json,
        }


@dataclass(frozen=True)
class TradeCollectionResult:
    market: str
    start_timestamp_ms: int
    end_timestamp_ms: int
    limit: int
    fetched: int
    accepted: int
    rejected: int
    duplicated: int
    rejection_reasons: tuple[tuple[str, int], ...]
    output_path: str | None
    records: tuple[BitvavoHistoricalTrade, ...]
    collection_status: str = "success"
    window_complete: bool = True
    integrity_issues: tuple[str, ...] = ()
    dataset_status: str = "VALIDATED"
    validation_result: str = "SUCCESS"
    page_count: int = 0
    page_sizes: tuple[int, ...] = ()
    pagination_cursor: str | None = None
    coverage_exhausted: bool = False
    pagination_mode: str = "single_request"
    pagination_status: str = "not_required"


class BitvavoTradeCollectorError(RuntimeError):
    pass


class BitvavoTradeCollector:
    """Collects a bounded historical window of Bitvavo public BTC-EUR trades.

    The collector validates and stores raw trade data only. It does not normalize
    the records into replay input and does not depend on live market streaming.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        source: str = DEFAULT_SOURCE,
        default_output_dir: str | Path = Path("data") / "raw" / "bitvavo_trades",
        fetcher: Callable[[Request], Any] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.source = source
        self.default_output_dir = Path(default_output_dir)
        self.fetcher = fetcher or urlopen

    def collect_window(
        self,
        market: str,
        start_timestamp_ms: int,
        end_timestamp_ms: int,
        limit: int = MAX_LIMIT,
        output_path: str | Path | None = None,
    ) -> TradeCollectionResult:
        if not MARKET_RE.match(market):
            raise BitvavoTradeCollectorError(f"invalid market: {market!r}")

        if limit < 1 or limit > MAX_LIMIT:
            raise BitvavoTradeCollectorError(f"limit must be between 1 and {MAX_LIMIT}")

        if start_timestamp_ms < 0 or end_timestamp_ms < 0:
            raise BitvavoTradeCollectorError("timestamps must be non-negative")

        if end_timestamp_ms <= start_timestamp_ms:
            raise BitvavoTradeCollectorError("end_timestamp_ms must be greater than start_timestamp_ms")

        if (end_timestamp_ms - start_timestamp_ms) > MAX_WINDOW_MS:
            raise BitvavoTradeCollectorError("time window must not exceed 24 hours")

        accepted_records: list[BitvavoHistoricalTrade] = []
        rejection_reasons: dict[str, int] = {}
        seen_trade_ids: set[str] = set()
        duplicated = 0
        page_sizes: list[int] = []
        page_count = 0
        last_cursor: str | None = None
        previous_last_trade_id: str | None = None
        coverage_exhausted = False
        pagination_mode = "single_request"
        pagination_status = "not_required"

        while True:
            if page_count >= self._max_pagination_pages(limit):
                raise BitvavoTradeCollectorError("maximum pagination iterations exceeded before window exhaustion was proven")

            page_count += 1
            response = self._fetch_trades(
                market,
                start_timestamp_ms,
                end_timestamp_ms,
                limit,
                trade_id_from=last_cursor,
            )
            payload = self._decode_response(response)
            raw_rows = self._extract_trade_rows(payload)
            page_sizes.append(len(raw_rows))
            pagination_mode = "tradeIdFrom"
            pagination_status = "continuing"

            if not raw_rows:
                if page_count == 1:
                    coverage_exhausted = True
                    pagination_status = "zero_trade_window"
                    break
                coverage_exhausted = True
                pagination_status = "empty_page_after_full_page" if page_sizes[-2] == limit else "empty_page"
                break

            page_trade_ids: list[str] = []
            page_seen_ids: set[str] = set()
            boundary_overlap_seen = False
            no_valid_rows = True
            for raw_row in raw_rows:
                trade, rejection_reason, is_duplicate = self._parse_trade_row(raw_row, market)
                if trade is None:
                    rejection_reasons[rejection_reason] = rejection_reasons.get(rejection_reason, 0) + 1
                    if is_duplicate:
                        duplicated += 1
                    continue

                if trade.raw_timestamp_ms is not None:
                    if trade.raw_timestamp_ms < start_timestamp_ms or trade.raw_timestamp_ms > end_timestamp_ms:
                        rejection_reasons["timestamp_outside_requested_window"] = rejection_reasons.get("timestamp_outside_requested_window", 0) + 1
                        continue

                if previous_last_trade_id is not None and trade.trade_id == previous_last_trade_id and not boundary_overlap_seen:
                    boundary_overlap_seen = True
                    continue

                if trade.trade_id in page_seen_ids:
                    duplicated += 1
                    continue

                if trade.trade_id in seen_trade_ids:
                    duplicated += 1
                    continue

                if previous_last_trade_id is not None and trade.trade_id == previous_last_trade_id:
                    raise BitvavoTradeCollectorError("pagination did not advance: repeated trade ID across pages")

                seen_trade_ids.add(trade.trade_id)
                page_seen_ids.add(trade.trade_id)
                accepted_records.append(trade)
                page_trade_ids.append(trade.trade_id)
                no_valid_rows = False

            if page_count > 1 and not page_trade_ids:
                raise BitvavoTradeCollectorError("pagination made no progress: continuation page contained only previously seen trade IDs")

            if no_valid_rows:
                if previous_last_trade_id is not None and boundary_overlap_seen and not page_trade_ids:
                    raise BitvavoTradeCollectorError("pagination boundary overlap without forward progress")
                break

            if page_trade_ids and previous_last_trade_id is not None and page_trade_ids[0] == previous_last_trade_id:
                raise BitvavoTradeCollectorError("pagination cursor did not progress; first trade ID repeated")

            previous_last_trade_id = page_trade_ids[-1]
            last_cursor = page_trade_ids[-1]

            if page_count == 1:
                if len(raw_rows) < limit:
                    coverage_exhausted = True
                    pagination_status = "short_page_proves_exhaustion"
                    break
                if len(raw_rows) == limit:
                    continue
                coverage_exhausted = True
                pagination_status = "page_count_below_limit"
                break

            if page_count > 1:
                continue

            coverage_exhausted = True
            pagination_status = "page_count_below_limit"
            break

        accepted_records.sort(key=lambda record: (record.raw_timestamp_ms, record.trade_id))

        integrity_issues: list[str] = []
        collection_status = "success"
        window_complete = coverage_exhausted

        if "timestamp_outside_requested_window" in rejection_reasons:
            collection_status = "blocked"
            window_complete = False
            integrity_issues.append("timestamp_outside_requested_window")
        elif rejection_reasons:
            collection_status = "rejected"
            window_complete = False
            integrity_issues.append("invalid_rows_present")

        if accepted_records:
            timestamps = [record.raw_timestamp_ms for record in accepted_records if record.raw_timestamp_ms is not None]
            if timestamps:
                min_ts = min(timestamps)
                max_ts = max(timestamps)
                if min_ts < start_timestamp_ms or max_ts > end_timestamp_ms:
                    integrity_issues.append("timestamp_outside_requested_window")
                    collection_status = "blocked"
                    window_complete = False

        if page_count > 0 and page_sizes and page_sizes[-1] == limit and not coverage_exhausted:
            collection_status = "blocked"
            window_complete = False
            integrity_issues.append("pagination_not_exhausted")

        if not accepted_records and not rejection_reasons and page_count == 0:
            collection_status = "success"
            window_complete = True
            integrity_issues = []

        if not accepted_records and page_count > 0 and not rejection_reasons:
            collection_status = "success"
            window_complete = True
            integrity_issues = []

        resolved_output_path = self._resolve_output_path(
            market=market,
            start_timestamp_ms=start_timestamp_ms,
            end_timestamp_ms=end_timestamp_ms,
            output_path=output_path,
        )
        if resolved_output_path is not None:
            self._write_jsonl(resolved_output_path, accepted_records)

        if page_count == 0 or (page_count == 1 and page_sizes and page_sizes[0] == 0):
            dataset_status = "EMPTY_VALID_DATASET"
            validation_result = "SUCCESS"
        elif collection_status in {"rejected", "blocked"} or bool(integrity_issues) or len(accepted_records) == 0:
            dataset_status = "REJECTED"
            validation_result = "REJECTED"
        else:
            dataset_status = "VALIDATED"
            validation_result = "SUCCESS"

        return TradeCollectionResult(
            market=market,
            start_timestamp_ms=start_timestamp_ms,
            end_timestamp_ms=end_timestamp_ms,
            limit=limit,
            fetched=len(accepted_records),
            accepted=len(accepted_records),
            rejected=sum(rejection_reasons.values()),
            duplicated=duplicated,
            rejection_reasons=tuple(sorted(rejection_reasons.items())),
            output_path=str(resolved_output_path) if resolved_output_path is not None else None,
            records=tuple(accepted_records),
            collection_status=collection_status,
            window_complete=window_complete,
            integrity_issues=tuple(integrity_issues),
            dataset_status=dataset_status,
            validation_result=validation_result,
            page_count=page_count,
            page_sizes=tuple(page_sizes),
            pagination_cursor=last_cursor,
            coverage_exhausted=coverage_exhausted,
            pagination_mode=pagination_mode,
            pagination_status=pagination_status,
        )

    def _fetch_trades(
        self,
        market: str,
        start_timestamp_ms: int,
        end_timestamp_ms: int,
        limit: int,
        trade_id_from: str | None = None,
    ) -> Any:
        query_map: dict[str, str] = {
            "start": str(start_timestamp_ms),
            "end": str(end_timestamp_ms),
            "limit": str(limit),
        }
        if trade_id_from is not None:
            query_map["tradeIdFrom"] = str(trade_id_from)
        query = urlencode(query_map)
        endpoint_path = f"/{market}/trades"
        url = f"{self.base_url}{endpoint_path}?{query}"

        headers = {"Accept": "application/json"}
        auth_headers = self._build_auth_headers(method="GET", full_url=url)
        headers.update(auth_headers)

        request = Request(url, method="GET", headers=headers)

        try:
            return self.fetcher(request)
        except HTTPError as exc:
            raise BitvavoTradeCollectorError(f"Bitvavo HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise BitvavoTradeCollectorError(f"Bitvavo network error: {exc.reason}") from exc

    @staticmethod
    def _build_auth_headers(method: str, full_url: str) -> dict[str, str]:
        api_key = os.getenv("BITVAVO_API_KEY")
        api_secret = os.getenv("BITVAVO_API_SECRET")
        if not api_key or not api_secret:
            return {}

        timestamp_ms = str(int(datetime.now(timezone.utc).timestamp() * 1000))
        split_result = urlsplit(full_url)
        path_with_query = split_result.path
        if split_result.query:
            path_with_query += f"?{split_result.query}"

        signing_payload = f"{timestamp_ms}{method}{path_with_query}"
        signature = hmac.new(
            api_secret.encode("utf-8"),
            signing_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "Bitvavo-Access-Key": api_key,
            "Bitvavo-Access-Timestamp": timestamp_ms,
            "Bitvavo-Access-Signature": signature,
            "Bitvavo-Access-Window": DEFAULT_ACCESS_WINDOW_MS,
        }

    @staticmethod
    def _max_pagination_pages(limit: int) -> int:
        if limit <= 0:
            return 1
        return 1000

    @staticmethod
    def _decode_response(response: Any) -> Any:
        if hasattr(response, "read"):
            raw_bytes = response.read()
            if isinstance(raw_bytes, bytes):
                raw_text = raw_bytes.decode("utf-8")
            else:
                raw_text = str(raw_bytes)
            return json.loads(raw_text)

        if isinstance(response, (bytes, bytearray)):
            return json.loads(response.decode("utf-8"))

        if isinstance(response, str):
            return json.loads(response)

        return response

    @staticmethod
    def _extract_trade_rows(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]

        if isinstance(payload, dict):
            for key in ("data", "trades", "result"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [row for row in value if isinstance(row, dict)]

        raise BitvavoTradeCollectorError("unexpected Bitvavo response shape")

    def _parse_trade_row(self, row: dict[str, Any], market: str) -> tuple[BitvavoHistoricalTrade | None, str, bool]:
        if not isinstance(row, dict):
            return None, "invalid_trade_row", False

        trade_id = row.get("trade_id", row.get("tradeId", row.get("id")))
        if not isinstance(trade_id, str) or not trade_id.strip():
            return None, "missing_trade_id", False
        trade_id = trade_id.strip()

        timestamp_ms_raw = row.get("timestamp", row.get("timestamp_ms", row.get("time")))
        timestamp_ms = self._parse_timestamp_ms(timestamp_ms_raw)
        if timestamp_ms is None:
            return None, "invalid_timestamp", False

        price = self._parse_decimal(row.get("price"))
        if price is None:
            return None, "invalid_price", False
        if price <= 0:
            return None, "non_positive_price", False

        amount = self._parse_decimal(row.get("amount"))
        if amount is None:
            return None, "invalid_amount", False
        if amount <= 0:
            return None, "non_positive_amount", False

        side = row.get("side")
        if not isinstance(side, str):
            return None, "invalid_side", False
        side = side.strip().lower()
        if side not in {"buy", "sell"}:
            return None, "invalid_side", False

        event_time_utc = self._unix_ms_to_iso_utc(timestamp_ms)
        payload_json = json.dumps(row, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        return (
            BitvavoHistoricalTrade(
                trade_id=trade_id,
                event_time_utc=event_time_utc,
                market=market,
                price=price,
                amount=amount,
                side=side,
                source=self.source,
                raw_timestamp_ms=timestamp_ms,
                raw_payload_json=payload_json,
            ),
            "",
            False,
        )

    @staticmethod
    def _parse_timestamp_ms(raw: Any) -> int | None:
        if raw is None or raw == "":
            return None
        try:
            timestamp_ms = int(raw)
        except (TypeError, ValueError):
            return None
        if timestamp_ms < 0:
            return None
        return timestamp_ms

    @staticmethod
    def _parse_decimal(raw: Any) -> Decimal | None:
        if raw is None or raw == "":
            return None
        try:
            value = Decimal(str(raw).strip())
        except (InvalidOperation, AttributeError):
            return None

        if not value.is_finite():
            return None
        return value

    @staticmethod
    def _unix_ms_to_iso_utc(timestamp_ms: int) -> str:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat(timespec="milliseconds")

    def _resolve_output_path(
        self,
        market: str,
        start_timestamp_ms: int,
        end_timestamp_ms: int,
        output_path: str | Path | None,
    ) -> Path | None:
        if output_path is not None:
            return Path(output_path)

        self.default_output_dir.mkdir(parents=True, exist_ok=True)
        start_label = self._unix_ms_to_path_fragment(start_timestamp_ms)
        end_label = self._unix_ms_to_path_fragment(end_timestamp_ms)
        filename = f"{market}_{start_label}_{end_label}.jsonl"
        return self.default_output_dir / filename

    @staticmethod
    def _unix_ms_to_path_fragment(timestamp_ms: int) -> str:
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        milliseconds = dt.microsecond // 1000
        return f"{dt.strftime('%Y%m%dT%H%M%S')}.{milliseconds:03d}Z"

    @staticmethod
    def _write_jsonl(path: Path, records: list[BitvavoHistoricalTrade]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            for record in records:
                handle.write(json.dumps(record.to_json_record(), ensure_ascii=True, separators=(",", ":")) + "\n")