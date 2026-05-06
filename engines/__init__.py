#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""引擎抽象层 + 实现包。

公共 API 从 engine_base / engine_detector 导出。
各引擎实现通过 engine_detector.create_engine() 延迟导入。
"""

from engines.engine_base import (
    EngineProfile,
    TranslatableUnit,
    EngineBase,
    RENPY_PROFILE,
    RPGMAKER_MV_PROFILE,
    CSV_PROFILE,
    UNITY_XUNITY_PROFILE,
    ENGINE_PROFILES,
)
from engines.engine_detector import (
    EngineType,
    detect_engine_type,
    detect_engine,
    create_engine,
    resolve_engine,
)

__all__ = [
    "EngineProfile",
    "TranslatableUnit",
    "EngineBase",
    "RENPY_PROFILE",
    "RPGMAKER_MV_PROFILE",
    "CSV_PROFILE",
    "UNITY_XUNITY_PROFILE",
    "ENGINE_PROFILES",
    "EngineType",
    "detect_engine_type",
    "detect_engine",
    "create_engine",
    "resolve_engine",
]
