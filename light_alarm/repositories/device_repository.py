"""SQL persistence for warning light devices."""

from contextlib import contextmanager

import pyodbc


class DeviceRepository:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def connection(self):
        # ODBC braces escape separators in passwords and other connection values.
        def quote(value):
            return "{" + str(value).replace("}", "}}") + "}"

        db = self.settings.database
        driver = str(db["SQL_DRIVER"]).strip()
        if driver.startswith("{") and driver.endswith("}"):
            driver = driver[1:-1].replace("}}", "}")
        fields = {
            "DRIVER": driver, "SERVER": db["SQL_SERVER"],
            "DATABASE": db["SQL_DATABASE"], "UID": db["SQL_USER"],
            "PWD": db["SQL_PASSWORD"],
        }
        connection = pyodbc.connect(
            ";".join(f"{key}={quote(value)}" for key, value in fields.items()),
            timeout=self.settings.database_timeout,
        )
        try:
            connection.timeout = self.settings.database_timeout
            yield connection
        finally:
            connection.close()

    def _fetch(self, query, parameters=(), one=False):
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, parameters)
                columns = [column[0] for column in cursor.description]
                if one:
                    row = cursor.fetchone()
                    return dict(zip(columns, row)) if row is not None else None
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            finally:
                cursor.close()

    def _write(self, query, parameters):
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(query, parameters)
                affected = cursor.rowcount
                connection.commit()
                return affected
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()

    def get_lines(self):
        return self._fetch("SELECT DISTINCT line FROM dbo.dv_warning_light_devices ORDER BY line")

    def get_all(self):
        return self._fetch("SELECT * FROM dbo.dv_warning_light_devices ORDER BY keyid")

    def get_by_id(self, keyid):
        return self._fetch("SELECT * FROM dbo.dv_warning_light_devices WHERE keyid = ?", (keyid,), one=True)

    def get_by_line(self, line):
        return self._fetch("SELECT * FROM dbo.dv_warning_light_devices WHERE line = ? ORDER BY keyid", (line,))

    def get_device_office(self):
        return self.get_by_line("OFFICE")

    def create(self, user_code_created, station_name, ip, port, line, remark=None):
        return self._write(
            "INSERT INTO dbo.dv_warning_light_devices "
            "(user_code_created, station_name, ip, port, line, remark) VALUES (?, ?, ?, ?, ?, ?)",
            (user_code_created, station_name, ip, port, line, remark),
        )

    def update(self, keyid, user_code_updated, station_name, ip, port, line, remark=None):
        return self._write(
            "UPDATE dbo.dv_warning_light_devices SET user_code_updated = ?, station_name = ?, "
            "ip = ?, port = ?, line = ?, remark = ?, updated = GETDATE() WHERE keyid = ?",
            (user_code_updated, station_name, ip, port, line, remark, keyid),
        )

    def delete(self, keyid):
        return self._write("DELETE FROM dbo.dv_warning_light_devices WHERE keyid = ?", (keyid,))
