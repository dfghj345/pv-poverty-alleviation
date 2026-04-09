from __future__ import annotations

import re
from decimal import Decimal
from typing import Optional, TypedDict


class PolicyParsed(TypedDict):
    province: str
    electricity_price: Decimal
    is_market_price: bool


_PRICE_RE = re.compile(r"(\d\.\d{4})")
_PROVINCE_RE = re.compile(r"([一-龥]{2,8}(省|市|自治区|回族自治区|维吾尔自治区|壮族自治区))")


class DataCleaner:
    @staticmethod
    def parse_policy_text(text: Optional[str]) -> PolicyParsed:
        raw = text or ""

        price_match = _PRICE_RE.search(raw)
        province_match = _PROVINCE_RE.search(raw)

        province = (
            province_match.group(1).replace("省", "").replace("市", "")
            if province_match
            else "Unknown"
        )
        electricity_price = Decimal(price_match.group(1)) if price_match else Decimal("0.3500")

        return {
            "province": province,
            "electricity_price": electricity_price,
            "is_market_price": ("竞价" in raw) or ("市场化" in raw),
        }