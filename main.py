#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ren'Py 整文件翻译工具 — 将完整 .rpy 文件发给 AI，由 AI 自行识别可翻译内容

核心优势：
  - AI 看到完整文件上下文，自行判断什么该翻什么不该翻
  - 不会误翻 screen 关键字、变量名、配置值
  - 跨文件术语一致性（自动维护术语表）
  - 翻译安全校验（变量、标签、缩进、代码结构检查）

用法：
  python main.py --game-dir "E:\\Games\\MyGame" --provider xai --api-key YOUR_KEY
  python main.py --game-dir "E:\\Games\\MyGame" --provider openai --api-key YOUR_KEY --model gpt-4o
  python main.py --resume   # 从上次中断处继续

文件流程：
  扫描 .rpy → 拆分大文件 → 发送 AI 翻译 → JSON 回传 → Patch 回原文件 → 校验
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("multi_engine_translator")


# ============================================================
# Logging 配置
# ============================================================

class _FlushStreamHandler(logging.StreamHandler):
    """每条日志后自动 flush，确保多线程下实时输出。"""
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logging(verbose: bool = False, quiet: bool = False, log_file: str = ""):
    """配置全局 logging。verbose=DEBUG, quiet=WARNING, 默认=INFO。"""
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    fmt = "%(message)s"
    handlers: list[logging.Handler] = [_FlushStreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=level, format=fmt, handlers=handlers, force=True)


# ============================================================
# CLI 参数校验
# ============================================================

def _positive_int(value: str) -> int:
    """argparse type: 正整数。"""
    iv = int(value)
    if iv <= 0:
        raise argparse.ArgumentTypeError(f"必须为正整数: {value}")
    return iv


def _positive_float(value: str) -> float:
    """argparse type: 正浮点数。"""
    fv = float(value)
    if fv <= 0:
        raise argparse.ArgumentTypeError(f"必须为正数: {value}")
    return fv


def _ratio_float(value: str) -> float:
    """argparse type: 0~1 之间的比例值。"""
    fv = float(value)
    if not (0 < fv <= 1.0):
        raise argparse.ArgumentTypeError(f"必须在 (0, 1.0] 范围内: {value}")
    return fv


def _parse_target_langs(raw: str) -> list[str]:
    """Round 35 Subtask 1: parse ``--target-lang`` into a list.

    ``"zh"``        → ``["zh"]``             (single lang, round-34 behaviour)
    ``"zh-tw"``     → ``["zh-tw"]``          (BCP-47 hyphen preserved)
    ``"zh,ja"``     → ``["zh", "ja"]``       (comma-separated multi-lang)
    ``"zh, ja ,ja"`` → ``["zh", "ja"]``      (whitespace stripped, dupes kept
                                              as-is for operator visibility)
    ``""`` / ``None`` / ``",,,"`` → ``["zh"]`` (safe default fallback)

    The outer translation loop in :func:`main` iterates over this list,
    swapping ``args.target_lang`` + refreshing ``args.lang_config`` each
    time, so downstream code that reads the singular form stays
    unchanged from round 34.
    """
    if not raw:
        return ["zh"]
    langs = [lang.strip() for lang in str(raw).split(",") if lang.strip()]
    return langs or ["zh"]


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Ren'Py 整文件翻译工具 — AI 自主识别翻译内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--game-dir", required=True, help="游戏目录（自动检测 game/ 子目录，自动排除 renpy/ 引擎文件）")
    parser.add_argument("--output-dir", default=None, help="输出目录 (默认: output)")
    parser.add_argument("--provider", default=None, choices=['xai', 'grok', 'openai', 'deepseek', 'claude', 'gemini', 'custom'],
                        help="API 提供商（custom 需配合 --custom-module 使用）")
    parser.add_argument("--custom-module", default="", metavar="NAME",
                        help="自定义翻译引擎模块名（位于 custom_engines/ 目录，如 my_engine）。"
                             "自 round 52 起，所有 custom plugin 自动走 subprocess 沙箱；"
                             "plugin 文件必须实现 _plugin_serve() 处理 --plugin-serve 参数（参考 example_echo.py）")
    parser.add_argument("--emit-runtime-hook", action="store_true",
                        help="在输出目录额外生成 translations.json + "
                             "zz_tl_inject_hook.rpy，供运行时注入模式使用（opt-in）。"
                             "默认关闭，静态 .rpy 改写流程不受影响")
    parser.add_argument("--runtime-hook-schema", choices=["v1", "v2"], default="v1",
                        help="translations.json schema 版本（仅在 --emit-runtime-hook 开启时生效）："
                             "v1=flat {en: zh}（默认，向后兼容）；"
                             "v2=nested {en: {zh, zh-tw, ja}} 多语言信封，支持 "
                             "RENPY_TL_INJECT_LANG 运行时切换语言")
    parser.add_argument("--api-key", default="", help="API 密钥（dry-run 模式可不填）")
    parser.add_argument("--model", default=None, help="模型名称 (留空使用默认)")
    parser.add_argument("--genre", default=None, choices=['adult', 'visual_novel', 'rpg', 'general'],
                        help="翻译风格 (默认: adult)")
    parser.add_argument("--rpm", type=_positive_int, default=None, help="每分钟请求数限制 (默认: 60)")
    parser.add_argument("--rps", type=_positive_int, default=None, help="每秒请求数限制 (默认: 5)")
    parser.add_argument("--timeout", type=_positive_float, default=None, help="API 超时秒数 (默认: 180)")
    parser.add_argument("--temperature", type=float, default=None, help="生成温度 (默认: 0.1, 低=一致性高)")
    parser.add_argument("--max-chunk-tokens", type=_positive_int, default=None,
                        help="每个分块最大 token 数 (默认: 4000)")
    parser.add_argument("--resume", action="store_true", help="从上次中断处继续")
    parser.add_argument("--dict", nargs="*", default=None, metavar="PATH",
                        help="外部词典文件（CSV/JSONL，可多个）")
    parser.add_argument("--ui-button-whitelist", nargs="*", default=None, metavar="PATH",
                        help="UI 按钮白名单扩展文件（.txt 每行一词 + # 注释 / .json list，可多个）。"
                             "扩展的按钮会在 Python 端 is_common_ui_button 返回 True，并在启用 "
                             "--emit-runtime-hook 时通过 sidecar ui_button_whitelist.json 同步到 "
                             "inject_hook.rpy 运行时")
    parser.add_argument("--copy-assets", action="store_true",
                        help="复制非 .rpy 资源文件到输出目录")
    parser.add_argument("--workers", type=int, default=None,
                        help="每文件内 chunk 并发线程数 (默认: 1)")
    parser.add_argument("--file-workers", type=int, default=None,
                        help="文件级并行翻译线程数 (默认: 1, >1 时多文件同时翻译)")
    parser.add_argument("--exclude", nargs="*", default=None, metavar="PATTERN",
                        help="排除匹配的文件 (glob 模式)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅扫描统计，不实际翻译（预估费用）")
    parser.add_argument("--max-response-tokens", type=_positive_int, default=None,
                        help="API 最大响应 token 数 (默认: 32768)")
    parser.add_argument("--log-file", default="", metavar="PATH",
                        help="保存详细日志到文件")
    parser.add_argument("--target-lang", default=None,
                        help="目标语言 (默认: zh 简体中文)。Round 35: "
                             "支持逗号分隔多语言（如 ``--target-lang zh,ja,zh-tw``）"
                             "触发外层语言循环，每语言跑一次流水线；"
                             "API 成本 N 倍。Round 39: ``--tl-mode`` / "
                             "``--retranslate`` 也已支持非 zh 目标语言 "
                             "（per-language prompt + 响应字段别名读取）")
    parser.add_argument("--input-price", type=float, default=None, metavar="USD",
                        help="手动指定输入价格 (每百万 tokens, 美元)")
    parser.add_argument("--output-price", type=float, default=None, metavar="USD",
                        help="手动指定输出价格 (每百万 tokens, 美元)")
    parser.add_argument("--tl-priority", action="store_true",
                        help="启用 tl 优先模式：若检测到 tl/ 目录，则仅翻译 tl 下的脚本")
    parser.add_argument("--stage", default="single",
                        help="内部使用：由一键流水线指定当前运行阶段")
    parser.add_argument("--patch-font", action="store_true", default=False,
                        help="启用自动字体补丁")
    parser.add_argument("--font-file", default="", metavar="PATH",
                        help="指定字体文件路径")
    parser.add_argument("--font-config", default="", metavar="PATH",
                        help="字体配置文件路径（font_config.json，可设置字号/布局参数）")
    parser.add_argument("--retranslate", action="store_true",
                        help="补翻模式：扫描残留英文对话行，精准补翻")
    parser.add_argument("--min-dialogue-density", type=_ratio_float, default=None, metavar="RATIO",
                        help="对话密度阈值 (默认: 0.20)")
    parser.add_argument("--tl-mode", action="store_true",
                        help="tl 模式：翻译 tl/<lang>/ 空槽位")
    parser.add_argument("--tl-lang", default=None, metavar="LANG",
                        help="tl 语言子目录名 (默认: chinese)")
    parser.add_argument("--cot", action="store_true",
                        help="启用 CoT 思维链翻译（直译→校正→意译，质量更高但费用+30-50%%）")
    parser.add_argument("--verbose", action="store_true",
                        help="输出详细调试信息（DEBUG 级别）")
    parser.add_argument("--quiet", action="store_true",
                        help="仅输出警告和错误（WARNING 级别）")
    parser.add_argument("--no-clean-rpyc", action="store_true",
                        help="跳过 tl-mode 翻译后的 .rpyc 缓存清理")
    parser.add_argument("--tl-screen", action="store_true",
                        help="翻译 screen 中的裸英文字符串（text/textbutton/Tooltip）")
    parser.add_argument("--engine", default="auto",
                        choices=["auto", "renpy", "rpgmaker", "csv", "jsonl"],
                        help="游戏引擎类型 (默认: auto 自动检测)")
    parser.add_argument("--config", default="", metavar="PATH",
                        help="配置文件路径（默认自动查找 renpy_translate.json）")

    args = parser.parse_args()

    setup_logging(
        verbose=args.verbose,
        quiet=args.quiet,
        log_file=args.log_file,
    )

    # 智能检测游戏目录
    game_dir = Path(args.game_dir)
    if (game_dir / "game").exists():
        root_rpys = [f for f in game_dir.glob('*.rpy')]
        if root_rpys:
            logger.info(f"[INFO] 根目录和 game/ 都包含 .rpy 文件，扫描整个目录")
        else:
            game_dir = game_dir / "game"

    if not game_dir.exists():
        logger.error(f"[ERROR] 游戏目录不存在: {game_dir}")
        sys.exit(1)

    # 加载配置文件，与 CLI 参数合并（CLI 优先）
    from core.config import Config
    cfg = Config(game_dir=game_dir, cli_args=args, config_path=args.config)

    # 用 Config 三层合并填充 args 中为 None 的参数
    args.game_dir = str(game_dir)
    args.output_dir = cfg.get("output_dir", "output")
    args.provider = cfg.get("provider", "xai")
    args.model = cfg.get("model", "")
    args.genre = cfg.get("genre", "adult")
    args.workers = cfg.get("workers", 1)
    args.file_workers = cfg.get("file_workers", 1)
    args.rpm = cfg.get("rpm", 60)
    args.rps = cfg.get("rps", 5)
    args.timeout = cfg.get("timeout", 180.0)
    args.temperature = cfg.get("temperature", 0.1)
    args.max_chunk_tokens = cfg.get("max_chunk_tokens", 4000)
    args.max_response_tokens = cfg.get("max_response_tokens", 32768)
    args.target_lang = cfg.get("target_lang", "zh")
    # Round 35 Subtask 1: ``--target-lang zh,ja,zh-tw`` comma-separated
    # splits into a list of per-language runs.  Single-language syntax
    # (``--target-lang zh`` / ``--target-lang zh-tw``) stays a 1-element
    # list so the outer loop below has a single iteration — round-34
    # behaviour is byte-identical.  BCP-47 tags use hyphens not commas,
    # so ``zh-tw`` is unambiguously a single language code.
    args.target_langs = _parse_target_langs(args.target_lang)
    # args.target_lang stays the first (or only) language so downstream
    # code that reads the singular form keeps working during the first
    # iteration of the outer loop.
    args.target_lang = args.target_langs[0]
    args.min_dialogue_density = cfg.get("min_dialogue_density", 0.20)
    args.tl_lang = cfg.get("tl_lang", "chinese")
    if args.dict is None:
        args.dict = cfg.get("dict", []) or []
    if args.exclude is None:
        args.exclude = cfg.get("exclude", []) or []
    # Round 32 Commit 2: UI-button whitelist extension files.  Loader is
    # best-effort (missing files / bad JSON log warning + skip), so we
    # can always call through regardless of CLI / config presence.  MUST
    # complete before engine.run(args) spawns the ThreadPoolExecutor.
    if args.ui_button_whitelist is None:
        args.ui_button_whitelist = cfg.get("ui_button_whitelist", []) or []
    if args.ui_button_whitelist:
        from file_processor import load_ui_button_whitelist
        load_ui_button_whitelist(args.ui_button_whitelist)

    # 解析目标语言配置
    from core.lang_config import get_language_config
    args.lang_config = get_language_config(args.target_lang)
    logger.debug(f"[LANG] 目标语言: {args.lang_config.native_name} ({args.lang_config.code})")

    # API Key 解析优先级（高 → 低）：
    #   1. --api-key CLI（显式传入；向后兼容）
    #   2. _RENPY_TRANSLATOR_CHILD_API_KEY 子进程专用环境变量（GUI/launcher 用，读完立即 pop
    #      防止继承到下游 subprocess，避免出现在进程列表中）
    #   3. 配置文件的 api_key_env / api_key_file
    if not args.api_key:
        args.api_key = os.environ.pop("_RENPY_TRANSLATOR_CHILD_API_KEY", "")
    if not args.api_key:
        args.api_key = cfg.resolve_api_key()

    # dry-run 模式不需要 API key
    if not args.dry_run and not args.api_key:
        logger.error("[ERROR] 非 dry-run 模式必须提供 --api-key（或在配置文件中设置 api_key_env）")
        sys.exit(1)

    tl_mode = getattr(args, "tl_mode", False)
    if args.retranslate and tl_mode:
        logger.error("[ERROR] --retranslate 和 --tl-mode 互斥，不能同时使用")
        sys.exit(1)

    # Round 39: the r35 multi-language guard that rejected
    # ``--tl-mode --target-lang ja`` / ``--retranslate --target-lang ko``
    # is removed now that ``core.prompts.build_tl_system_prompt`` and
    # ``build_retranslate_system_prompt`` branch on ``lang_config.code``
    # to emit a generic English template for non-zh targets, and the
    # response readers in ``tl_mode._translate_chunk`` /
    # ``retranslator.retranslate_file`` use
    # ``core.lang_config.resolve_translation_field`` to read the
    # per-language field back out of the AI response.  Multi-language
    # tl-mode / retranslate runs now genuinely work end-to-end.

    # Round 28 A-H-3 Minimal: unified engine routing.  Every engine
    # (Ren'Py + auto + rpgmaker + csv + jsonl) now goes through the same
    # ``engines.resolve_engine(...).run(args)`` entry.  Ren'Py-specific
    # branching (tl_mode / tl_screen / retranslate / direct) lives inside
    # ``engines/renpy_engine.py::RenPyEngine.run`` so this file holds one
    # source of truth for the dispatch.
    engine_arg = getattr(args, "engine", "auto") or "auto"
    from engines.engine_detector import resolve_engine as _resolve_engine
    engine = _resolve_engine(engine_arg, Path(args.game_dir))
    if engine is None:
        logger.error(f"[ERROR] 无法创建引擎: {engine_arg}")
        sys.exit(1)

    # Round 35 Subtask 1: outer language loop.  Single-language runs take
    # this path exactly once (no observable behaviour change from r34).
    # Multi-language runs iterate once per language, re-using the same
    # ``engine`` instance but swapping ``args.target_lang`` + refreshing
    # ``args.lang_config``.  API cost scales N× the source file size; the
    # warning prints up front so the operator can Ctrl-C before anything
    # is spent.
    if len(args.target_langs) > 1:
        logger.warning(
            "[MULTI-LANG] 即将对 %d 种语言 %s 各跑一次翻译流水线，"
            "API 成本约为单语言的 %d 倍。按 Ctrl-C 取消。",
            len(args.target_langs), args.target_langs, len(args.target_langs),
        )
    # Round 37 M3: save pre-loop state so any post-loop reader (future
    # reporting code, integration tests, CLI chaining) observes the
    # canonical first-language value rather than the last iteration's
    # residue.  No current reader depends on this invariant but future
    # extensions would silently regress without it, so the save/restore
    # pair is a cheap defensive guard.
    _saved_target_lang = args.target_lang
    _saved_lang_config = args.lang_config
    try:
        for _idx, _lang in enumerate(args.target_langs):
            args.target_lang = _lang
            # lang_config 依赖 target_lang；每次迭代刷新，direct-mode 的 system
            # prompt 才会匹配新语言。
            args.lang_config = get_language_config(_lang)
            if len(args.target_langs) > 1:
                logger.info(
                    "[MULTI-LANG] === 语言 %d/%d: %s (%s) ===",
                    _idx + 1, len(args.target_langs), _lang,
                    args.lang_config.native_name,
                )
            engine.run(args)
    finally:
        args.target_lang = _saved_target_lang
        args.lang_config = _saved_lang_config


if __name__ == "__main__":
    main()
