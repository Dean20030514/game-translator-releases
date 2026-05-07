#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyInstaller 打包脚本：将 GUI 入口打包为单个 .exe。

用法:
    python build.py              # 打包
    python build.py --clean-only # 只清理构建产物，不打包
    python build.py --clean      # 清理后再打包（PyInstaller --clean 语义）

产出:
    dist/多引擎游戏汉化工具.exe

注意:
    - 需要先安装 PyInstaller: pip install pyinstaller
    - 打包后的 .exe 包含所有 Python 文件，用户无需安装 Python
    - resources/fonts/ 下的字体文件会一并打包
    - --clean-only 仅删 dist/ + build/ + *.spec（开发者体验；r45 新增）
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def clean_build_artifacts() -> int:
    """Round 45 Commit 4: delete PyInstaller build outputs.

    Removes:
      - dist/ (final .exe lives here)
      - build/ (PyInstaller intermediates)
      - *.spec (PyInstaller config cache)

    Returns exit code 0 on success.  Prints per-item status.  Safe to
    re-run (missing paths silently no-op via ignore_errors).
    """
    targets_dirs = [
        PROJECT_ROOT / "dist",
        PROJECT_ROOT / "build",
    ]
    spec_files = list(PROJECT_ROOT.glob("*.spec"))

    print("=" * 60)
    print("清理 PyInstaller 构建产物")
    print("=" * 60)

    for d in targets_dirs:
        if d.exists():
            # Round 45 audit-tail: defense-in-depth against accidental
            # symlink traversal.  shutil.rmtree on Python 3.8+ already
            # refuses to follow symlinks into directories, but an
            # explicit is_symlink() check stops the operation earlier
            # and makes the intent visible in the audit trail.  Low
            # probability (user would need to `ln -s dist/ ~/Documents/`
            # themselves), but the cost of the check is zero.
            if d.is_symlink():
                print(
                    f"  [跳过]   {d.relative_to(PROJECT_ROOT)}/ "
                    f"是 symlink，拒绝跨 symlink 删除（指向 {d.resolve()}）"
                )
                continue
            try:
                shutil.rmtree(d, ignore_errors=False)
                print(f"  [已删除] {d.relative_to(PROJECT_ROOT)}/")
            except OSError as e:
                print(f"  [警告]   {d.relative_to(PROJECT_ROOT)}/: {e}")
        else:
            print(f"  [跳过]   {d.relative_to(PROJECT_ROOT)}/ (不存在)")

    for spec in spec_files:
        try:
            spec.unlink()
            print(f"  [已删除] {spec.name}")
        except OSError as e:
            print(f"  [警告]   {spec.name}: {e}")

    if not spec_files and not any(d.exists() for d in targets_dirs):
        print("  [信息]   无构建产物可清理")

    print("=" * 60)
    return 0


def _read_project_version() -> str:
    """r65 B2 fix: read pyproject.toml::version for PyInstaller --version-file.

    Single source of truth (matches main.py r64 S4 pattern). Falls back to
    "0.0.0" if pyproject.toml is missing/unparseable.
    """
    import re

    pyproject = PROJECT_ROOT / "pyproject.toml"
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return "0.0.0"
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def _write_version_info(version: str) -> Path:
    """r65 B2 fix: generate PyInstaller version-info template.

    Pre-r65 the .exe had no Windows version metadata even after r62 v2.0.0
    bump. PyInstaller's ``--version-file`` accepts a Windows VS_VERSION_INFO
    template; we generate it from pyproject.toml::version on every build so
    the .exe Properties → Details shows the real version.

    Tuple format requires (major, minor, patch, build) — pad with 0 if
    fewer parts.
    """
    parts = version.split(".")
    while len(parts) < 4:
        parts.append("0")
    major, minor, patch, build = parts[:4]

    template = f"""# UTF-8
# r65 B2 generated; do NOT hand-edit. Regenerated each build from pyproject.toml::version.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [StringStruct(u'CompanyName', u'Multi-Engine Game Translator'),
           StringStruct(u'FileDescription', u'Pure-Python multi-engine game translator (LLM-based zh-only)'),
           StringStruct(u'FileVersion', u'{version}'),
           StringStruct(u'InternalName', u'multi-engine-game-translator'),
           StringStruct(u'LegalCopyright', u'MIT License'),
           StringStruct(u'OriginalFilename', u'多引擎游戏汉化工具.exe'),
           StringStruct(u'ProductName', u'Multi-Engine Game Translator'),
           StringStruct(u'ProductVersion', u'{version}')]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [0x0409, 1200])])
  ]
)
"""
    out = PROJECT_ROOT / "version_info.txt"
    out.write_text(template, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    # Round 45 Commit 4: --clean-only subcommand
    if "--clean-only" in argv:
        return clean_build_artifacts()

    # 收集所有需要打包的 Python 模块（非测试、非工具）
    hidden_imports = [
        # core infrastructure
        "core",
        "core.api_client",
        "core.config",
        "core.glossary",
        "core.prompts",
        "core.translation_db",
        "core.translation_utils",
        # translators
        "translators",
        "translators.direct",
        "translators.tl_mode",
        "translators.retranslator",
        "translators.screen",
        "translators.tl_parser",
        "translators.renpy_text_utils",
        # file_processor
        "file_processor",
        "file_processor.splitter",
        "file_processor.patcher",
        "file_processor.checker",
        "file_processor.validator",
        # core (round 27 A-H-5: font_patch moved from tools/ to core/)
        "core.font_patch",
        # tools
        "tools",
        "tools.renpy_upgrade_tool",
        "tools.review_generator",
        "tools.rpa_packer",
        "tools.translation_editor",
        # pipeline
        "pipeline",
        "pipeline.helpers",
        "pipeline.gate",
        "pipeline.stages",
        # engines
        "engines",
        "engines.engine_base",
        "engines.engine_detector",
        "engines.generic_pipeline",
        "engines.renpy_engine",
        "engines.rpgmaker_engine",
        "engines.csv_engine",
        # entry points
        "main",
        "one_click_pipeline",
        "start_launcher",
    ]

    # 数据文件
    datas = []
    # 字体资源
    fonts_dir = PROJECT_ROOT / "resources" / "fonts"
    if fonts_dir.exists():
        datas.append((str(fonts_dir), "resources/fonts"))
    # 示例配置
    example_config = PROJECT_ROOT / "renpy_translate.example.json"
    if example_config.exists():
        datas.append((str(example_config), "."))
    # prompt presets
    presets_dir = PROJECT_ROOT / "prompt_presets"
    if presets_dir.exists():
        datas.append((str(presets_dir), "prompt_presets"))

    # r65 B2 fix: generate version-info.txt from pyproject.toml::version
    # so the .exe carries Windows version metadata (visible in
    # Properties → Details after build).
    project_version = _read_project_version()
    version_info_path = _write_version_info(project_version)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",
        "多引擎游戏汉化工具",
        "--icon",
        "NONE",
        "--noconfirm",
        "--clean",
        # r65 B2: embed Windows version metadata
        "--version-file",
        str(version_info_path),
    ]

    for imp in hidden_imports:
        cmd += ["--hidden-import", imp]
    for src, dst in datas:
        cmd += ["--add-data", f"{src};{dst}"]

    cmd.append(str(PROJECT_ROOT / "gui.py"))

    print("=" * 60)
    print("PyInstaller 打包")
    print("=" * 60)
    print("入口: gui.py")
    print(f"Hidden imports: {len(hidden_imports)}")
    print(f"Data files: {len(datas)}")
    print()

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode == 0:
        exe_path = PROJECT_ROOT / "dist" / "多引擎游戏汉化工具.exe"
        print()
        print("=" * 60)
        print(f"打包成功: {exe_path}")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"文件大小: {size_mb:.1f} MB")
        print("=" * 60)
    else:
        print()
        print("[ERROR] 打包失败")

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
