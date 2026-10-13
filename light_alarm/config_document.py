"""Validate and atomically save the YAML file selected at startup."""

import copy
import os
import shutil
import tempfile
from pathlib import Path

import yaml

from light_alarm.config import Settings


class ConfigDocument:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.reload()

    def reload(self):
        content = self.path.read_bytes()
        try:
            data = yaml.safe_load(content.decode("utf-8-sig"))
        except (yaml.YAMLError, UnicodeError) as error:
            raise ValueError("Không đọc được YAML. Kiểm tra cú pháp và mã hóa UTF-8 của file.") from error
        if not isinstance(data, dict):
            raise ValueError("Cấu hình YAML phải là một mapping.")
        self.data, self._original = data, content
        return copy.deepcopy(data)

    def save(self, data):
        settings = Settings.from_mapping(data, self.path)
        if self.path.read_bytes() != self._original:
            raise ValueError("File YAML đã thay đổi bên ngoài ứng dụng. Bấm Đọc lại trước khi lưu.")
        content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".config-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            shutil.copy2(self.path, self.path.with_suffix(self.path.suffix + ".bak"))
            os.replace(temporary, self.path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.data = copy.deepcopy(data)
        self._original = self.path.read_bytes()
        return settings
