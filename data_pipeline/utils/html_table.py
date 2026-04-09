from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List, Optional


@dataclass(slots=True)
class TableCell:
    text: str


class SimpleTableParser(HTMLParser):
    """
    轻量 HTML 表格解析器（stdlib only）：
    - 支持按 <table class="..."> 过滤
    - 提取每个 <tr> 的 <td> 文本
    目标是让 parse 可离线测试，不追求完美 HTML 兼容。
    """

    def __init__(self, *, table_class: Optional[str] = None) -> None:
        super().__init__(convert_charrefs=True)
        self._table_class = table_class
        self._in_target_table = False
        self._in_tr = False
        self._in_td = False
        self._td_buf: List[str] = []
        self._cur_row: List[str] = []
        self.rows: List[List[str]] = []

    def handle_starttag(self, tag: str, attrs):  # type: ignore[override]
        if tag == "table":
            cls = None
            for k, v in attrs:
                if k == "class":
                    cls = v
                    break
            if self._table_class is None:
                self._in_target_table = True
            else:
                self._in_target_table = bool(cls and self._table_class in cls.split())

        if not self._in_target_table:
            return

        if tag == "tr":
            self._in_tr = True
            self._cur_row = []
        elif tag == "td" and self._in_tr:
            self._in_td = True
            self._td_buf = []

    def handle_endtag(self, tag: str) -> None:
        if not self._in_target_table:
            if tag == "table":
                self._in_target_table = False
            return

        if tag == "td" and self._in_td:
            self._in_td = False
            cell = "".join(self._td_buf).strip()
            self._cur_row.append(cell)
            self._td_buf = []
        elif tag == "tr" and self._in_tr:
            self._in_tr = False
            if self._cur_row:
                self.rows.append(self._cur_row)
            self._cur_row = []
        elif tag == "table":
            self._in_target_table = False

    def handle_data(self, data: str) -> None:
        if self._in_target_table and self._in_td:
            self._td_buf.append(data)


def extract_table_rows(html: str, *, table_class: Optional[str] = None) -> List[List[str]]:
    p = SimpleTableParser(table_class=table_class)
    p.feed(html)
    return p.rows

