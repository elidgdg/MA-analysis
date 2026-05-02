from __future__ import annotations

from typing import Any

import blpapi


class BloombergClient:
    """
    Minimal Bloomberg Desktop API client.
    Supports:
    - reference data
    - historical data
    - recursive conversion of bulk/sequence elements to Python
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
                                    dt = row_el.getElementAsDatetime("date")
                                    row["date"] = dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

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
        value = value.strip()
        if "-" in value:
            return value.replace("-", "")
        return value

    @classmethod
    def _element_to_python(cls, element: blpapi.Element) -> Any:
        """
        Recursively convert Bloomberg Element to native Python.
        Handles:
        - scalars
        - arrays
        - sequences / bulk fields
        """
        if element.isNull():
            return None

        # Arrays / repeated values
        if element.isArray():
            out = []
            for i in range(element.numValues()):
                try:
                    sub = element.getValueAsElement(i)
                    out.append(cls._element_to_python(sub))
                except Exception:
                    try:
                        out.append(element.getValue(i))
                    except Exception:
                        out.append(str(element.getValueAsString(i)))
            return out

        # Sequences / complex nested objects
        if element.isComplexType():
            out: dict[str, Any] = {}
            for i in range(element.numElements()):
                sub = element.getElement(i)
                out[str(sub.name())] = cls._element_to_python(sub)
            return out

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
            dt = element.getValueAsDatetime()
            return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)
        if datatype == blpapi.DataType.DATETIME:
            dt = element.getValueAsDatetime()
            return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)
        if datatype == blpapi.DataType.TIME:
            dt = element.getValueAsDatetime()
            return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

        try:
            return element.getValue()
        except Exception:
            try:
                return element.getValueAsString()
            except Exception:
                return str(element)