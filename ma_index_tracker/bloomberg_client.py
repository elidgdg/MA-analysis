from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import blpapi


class BloombergClient:
    """
    Minimal Bloomberg Desktop API client.

    Works with Bloomberg Terminal/Desktop API on the same logged-in machine.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8194,
        timeout_ms: int = 10000,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout_ms = timeout_ms

    def _start_session(self) -> blpapi.Session:
        options = blpapi.SessionOptions()
        options.setServerHost(self.host)
        options.setServerPort(self.port)

        session = blpapi.Session(options)
        if not session.start():
            raise RuntimeError("Failed to start Bloomberg session.")

        if not session.openService("//blp/refdata"):
            session.stop()
            raise RuntimeError("Failed to open Bloomberg //blp/refdata service.")

        return session

    def reference_data(
        self,
        security: str,
        fields: list[str],
    ) -> dict[str, Any]:
        """
        Fetch Bloomberg reference data for one security.

        Returns a dict like:
        {
            "security": "NSC US Equity",
            "PX_LAST": 250.12,
            "NAME": "Norfolk Southern Corp",
            ...
        }
        """
        session = self._start_session()
        try:
            service = session.getService("//blp/refdata")
            request = service.createRequest("ReferenceDataRequest")

            request.getElement("securities").appendValue(security)
            field_el = request.getElement("fields")
            for field in fields:
                field_el.appendValue(field)

            session.sendRequest(request)

            result: dict[str, Any] = {"security": security}

            while True:
                event = session.nextEvent(self.timeout_ms)

                for msg in event:
                    if msg.hasElement("responseError"):
                        raise RuntimeError(f"Bloomberg response error: {msg}")

                    if msg.messageType() == blpapi.Name("ReferenceDataResponse"):
                        security_data_array = msg.getElement("securityData")

                        for i in range(security_data_array.numValues()):
                            sec_data = security_data_array.getValueAsElement(i)

                            if sec_data.hasElement("securityError"):
                                raise RuntimeError(
                                    f"Security error for {security}: {sec_data.getElement('securityError')}"
                                )

                            field_data = sec_data.getElement("fieldData")
                            for field in fields:
                                if field_data.hasElement(field):
                                    result[field] = self._element_to_python(
                                        field_data.getElement(field)
                                    )
                                else:
                                    result[field] = None

                if event.eventType() == blpapi.Event.RESPONSE:
                    break

            return result
        finally:
            session.stop()

    def historical_data(
        self,
        security: str,
        fields: list[str],
        start_date: str,
        end_date: str,
        periodicity_selection: str = "DAILY",
    ) -> list[dict[str, Any]]:
        """
        Fetch Bloomberg historical data for one security.

        Dates must be YYYY-MM-DD or YYYYMMDD.

        Returns rows like:
        [
            {
                "date": "2025-07-23",
                "PX_LAST": 250.1,
                "PX_VOLUME": 1234567,
            },
            ...
        ]
        """
        session = self._start_session()
        try:
            service = session.getService("//blp/refdata")
            request = service.createRequest("HistoricalDataRequest")

            request.getElement("securities").appendValue(security)
            field_el = request.getElement("fields")
            for field in fields:
                field_el.appendValue(field)

            request.set("startDate", self._normalise_date(start_date))
            request.set("endDate", self._normalise_date(end_date))
            request.set("periodicitySelection", periodicity_selection)

            session.sendRequest(request)

            rows: list[dict[str, Any]] = []

            while True:
                event = session.nextEvent(self.timeout_ms)

                for msg in event:
                    if msg.hasElement("responseError"):
                        raise RuntimeError(f"Bloomberg response error: {msg}")

                    if msg.messageType() == blpapi.Name("HistoricalDataResponse"):
                        if msg.hasElement("securityData"):
                            security_data = msg.getElement("securityData")

                            if security_data.hasElement("securityError"):
                                raise RuntimeError(
                                    f"Security error for {security}: {security_data.getElement('securityError')}"
                                )

                            field_data_array = security_data.getElement("fieldData")

                            for i in range(field_data_array.numValues()):
                                row_el = field_data_array.getValueAsElement(i)
                                row: dict[str, Any] = {}

                                if row_el.hasElement("date"):
                                    if row_el.hasElement("date"):
                                        dt = row_el.getElementAsDatetime("date")
                                        row["date"] = str(dt)

                                for field in fields:
                                    if row_el.hasElement(field):
                                        row[field] = self._element_to_python(
                                            row_el.getElement(field)
                                        )
                                    else:
                                        row[field] = None

                                rows.append(row)

                if event.eventType() == blpapi.Event.RESPONSE:
                    break

            return rows
        finally:
            session.stop()

    @staticmethod
    def _normalise_date(value: str) -> str:
        """
        Convert YYYY-MM-DD to YYYYMMDD. Leave YYYYMMDD unchanged.
        """
        value = value.strip()
        if "-" in value:
            return value.replace("-", "")
        return value

    @staticmethod
    def _element_to_python(element: blpapi.Element) -> Any:
        """
        Best-effort conversion from Bloomberg Element to Python value.
        """
        if element.isNull():
            return None

        datatype = element.datatype()

        if datatype == blpapi.DataType.BOOL:
            return element.getValueAsBool()
        if datatype == blpapi.DataType.INT32:
            return element.getValueAsInteger()
        if datatype == blpapi.DataType.INT64:
            return element.getValueAsInteger()
        if datatype == blpapi.DataType.FLOAT32:
            return element.getValueAsFloat()
        if datatype == blpapi.DataType.FLOAT64:
            return element.getValueAsFloat()
        if datatype == blpapi.DataType.STRING:
            return element.getValueAsString()
        if datatype == blpapi.DataType.CHAR:
            return element.getValueAsString()
        if datatype == blpapi.DataType.DATE:
            return str(element.getValueAsDatetime().date())
        if datatype == blpapi.DataType.DATETIME:
            return str(element.getValueAsDatetime())
        if datatype == blpapi.DataType.TIME:
            return str(element.getValueAsDatetime().time())

        try:
            return element.getValue()
        except Exception:
            return str(element)