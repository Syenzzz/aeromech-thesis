#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 aeromech-thesis 打包成 WorkBuddy 开放平台可上传的技能 zip。

用法：
    python build_skill_package.py                # 默认打包并输出 dist/
    python build_skill_package.py --keep-stage   # 保留展开后的 staging 目录，便于检查
    python build_skill_package.py --no-flatten    # 保留三级目录（平台会拒绝，仅本地查阅）

平台规范（https://open.workbuddy.cn/docs/skill）：
    {skill-name}/
        SKILL.md          # 必须，frontmatter 必填 name/display_name/display_name_en/
                          #   description/description_zh/description_en/version/author
        references/       # 可选
        scripts/          # 可选
        templates/        # 可选
    zip ≤ 3MB

本脚本会做的处理：
    1. 复制 SKILL.md / references / scripts / README.md / CHANGELOG.md / .env.example
    2. 排除 __pycache__、*.pyc、*.log、tests/、.git 等非运行必需内容
    3. 向 SKILL.md frontmatter 补齐平台必填字段（保留原有 name / description 不变）
    4. 校验体积、frontmatter 完整性，输出 zip
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL_DIR = ROOT / "aeromech-thesis"
DIST_DIR = ROOT / "dist"

SKILL_NAME = "aeromech-thesis"
MAX_ZIP_BYTES = 3 * 1024 * 1024

# 只复制这些顶层条目（白名单，避免把测试产物 / 缓存带进包）
INCLUDE_TOP_LEVEL = [
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    ".env.example",
    "references",
    "scripts",
]

EXCLUDE_DIR_NAMES = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", "node_modules"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".bak"}

# 平台必填字段（除 name / description 这两个已有字段外的补充值）
FRONTMATTER_EXTRA = {
    "display_name": "航空机械毕业论文助手",
    "display_name_en": "Aviation Mechanical Thesis Assistant",
    "description_zh": (
        "面向航空机械与飞行器维修工程专业的毕业论文研究与写作助手："
        "从题目分析、研究方案、工程分析到章节撰写全程按状态机推进，"
        "内置学术诚信守卫、研究完整性校验与交付质量门禁。"
    ),
    "description_en": (
        "A research and writing assistant for aviation mechanical and maintenance "
        "engineering theses, covering topic analysis, research design, engineering "
        "analysis and chapter drafting, with built-in academic integrity guards "
        "and delivery quality gates."
    ),
    "author": "Syen",
    "allowed-tools": "Read, Write, Edit, Glob, Grep, Bash",
}

EXAMPLES_ZH = [
    "帮我做一个航空发动机维修方向的毕业论文选题，我是机电专业高职的",
    "我的课题是起落架液压系统故障诊断，帮我搭研究方案和论文框架",
    "帮我用 FMEA 分析飞机液压系统的常见故障，写成第三章",
]

EXAMPLES_EN = [
    "Give me a thesis topic on aircraft engine maintenance for a vocational mechatronics student",
    "My topic is landing gear hydraulic system fault diagnosis - help me design the research plan and outline",
    "Use FMEA to analyze common faults in aircraft hydraulic systems and write it up as chapter 3",
]


def detect_version(text: str) -> str:
    """从 SKILL.md 正文里提取 「版本：v1.6.5」 形式的版本号。"""
    m = re.search(r"版本[：:]\s*v?(\d+\.\d+\.\d+)", text)
    if m:
        return m.group(1)
    m = re.search(r"v(\d+\.\d+\.\d+)", text)
    return m.group(1) if m else "1.0.0"


def split_frontmatter(text: str) -> tuple[list[str], list[str]]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise SystemExit("[FAIL] SKILL.md 缺少 YAML frontmatter（首行必须是 ---）")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], lines[i + 1:]
    raise SystemExit("[FAIL] SKILL.md frontmatter 未闭合（缺少结束的 ---）")


def quote_if_needed(value: str) -> str:
    """含 YAML 敏感字符（冒号+空格、#、引号）时用双引号包裹。"""
    if any(ch in value for ch in [": ", " #", '"', "\n"]):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def build_frontmatter(text: str) -> tuple[str, dict[str, str]]:
    """补齐必填字段，返回新全文与字段字典（用于自检）。"""
    fm_lines, body = split_frontmatter(text)
    version = detect_version(text)

    existing_keys = []
    for line in fm_lines:
        m = re.match(r"^([A-Za-z_][\w-]*):", line)
        if m:
            existing_keys.append(m.group(1))

    extras: list[str] = []
    for key in ["display_name", "display_name_en", "description_zh", "description_en", "allowed-tools"]:
        if key not in existing_keys:
            extras.append(f"{key}: {quote_if_needed(FRONTMATTER_EXTRA[key])}")
    if "version" not in existing_keys:
        extras.append(f"version: {version}")
    if "author" not in existing_keys:
        extras.append(f"author: {FRONTMATTER_EXTRA['author']}")
    if "examples_zh" not in existing_keys:
        extras.append("examples_zh:")
        extras.extend(f'  - "{e}"' for e in EXAMPLES_ZH)
    if "examples_en" not in existing_keys:
        extras.append("examples_en:")
        extras.extend(f'  - "{e}"' for e in EXAMPLES_EN)

    new_fm = list(fm_lines) + extras
    new_text = "---\n" + "\n".join(new_fm) + "\n---\n" + "\n".join(body)

    fields: dict[str, str] = {}
    for line in new_fm:
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2)
    fields["_version"] = version
    return new_text, fields


def copy_tree(src: Path, dst: Path, flatten: bool, mapping: dict[str, str]) -> None:
    """按白名单复制，并记录被扁平化的路径映射。"""
    for item in INCLUDE_TOP_LEVEL:
        src_path = src / item
        if not src_path.exists():
            print(f"  [skip] 不存在：{item}")
            continue

        if src_path.is_file():
            shutil.copy2(src_path, dst / src_path.name)
            continue

        for path in src_path.rglob("*"):
            if path.is_dir():
                continue
            if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
                continue
            if path.suffix.lower() in EXCLUDE_SUFFIXES:
                continue

            rel = path.relative_to(src)
            # 只在 references/{agents,knowledge,templates}/x.md 这一层做扁平化，
            # 且必须用相对路径推导目标，否则 path.parent.parent 是绝对路径会把文件写回源目录。
            if (
                flatten
                and len(rel.parts) == 3
                and rel.parts[0] == "references"
                and rel.parts[1] in {"agents", "knowledge", "templates"}
            ):
                prefix = {"agents": "agent", "knowledge": "kb", "templates": "tpl"}[rel.parts[1]]
                new_rel = Path("references") / f"{prefix}-{path.name}"
                mapping[rel.as_posix()] = new_rel.as_posix()
                rel = new_rel

            target = dst / rel
            if not target.resolve().is_relative_to(dst.resolve()):
                raise SystemExit(f"[FAIL] 目标路径越界：{target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def rewrite_references(root: Path, mapping: dict[str, str]) -> None:
    """扁平化模式下，同步替换 md / py 里的引用路径。

    先替换具体文件路径（references/agents/topic.md -> references/agent-topic.md），
    再兜底把残留的目录级引用（references/knowledge/）收敛为 references/。
    """
    if not mapping:
        return
    file_pattern = re.compile("|".join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)))
    dir_pattern = re.compile(r"references/(?:agents|knowledge|templates)/")
    changed = 0
    dir_hits = 0
    for path in root.rglob("*"):
        if path.is_dir() or path.suffix.lower() not in {".md", ".py", ".json", ".yaml", ".yml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        new_text = file_pattern.sub(lambda m: mapping[m.group(0)], text)
        new_text, n = dir_pattern.subn("references/", new_text)
        dir_hits += n
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
    print(f"  路径引用替换：{changed} 个文件" + (f"（含 {dir_hits} 处目录级引用）" if dir_hits else ""))


def make_zip(stage: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(stage.parent).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-stage", action="store_true", help="保留展开目录")
    parser.add_argument(
        "--no-flatten",
        dest="flatten",
        action="store_false",
        help="保留 references 三级子目录（平台会报「目录层级超限」，仅本地查阅用）",
    )
    parser.set_defaults(flatten=True)
    args = parser.parse_args()

    if not SKILL_DIR.is_dir():
        raise SystemExit(f"[FAIL] 找不到技能目录：{SKILL_DIR}")

    stage = DIST_DIR / SKILL_NAME
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    print(f"[1/4] 复制文件 -> {stage}")
    mapping: dict[str, str] = {}
    copy_tree(SKILL_DIR, stage, args.flatten, mapping)

    print("[2/4] 补齐 SKILL.md frontmatter")
    skill_md = stage / "SKILL.md"
    new_text, fields = build_frontmatter(skill_md.read_text(encoding="utf-8"))
    skill_md.write_text(new_text, encoding="utf-8")

    if mapping:
        print(f"[2.5] 扁平化 {len(mapping)} 个 references 文件")
        rewrite_references(stage, mapping)

    print("[3/4] 自检")
    required = [
        "name",
        "display_name",
        "display_name_en",
        "description",
        "description_zh",
        "description_en",
        "version",
        "author",
    ]
    missing = [k for k in required if not fields.get(k, "").strip()]
    if missing:
        print(f"  [FAIL] frontmatter 缺字段：{', '.join(missing)}")
        return 1
    print(f"  frontmatter 必填字段 {len(required)}/{len(required)} OK，版本 {fields['_version']}")

    py_count = len(list((stage / "scripts").glob("*.py")))
    md_count = len(list((stage / "references").rglob("*.md")))
    print(f"  scripts: {py_count} 个 .py，references: {md_count} 个 .md")

    print("[4/4] 打包")
    version = fields["_version"]
    zip_path = DIST_DIR / f"{SKILL_NAME}-v{version}.zip"
    make_zip(stage, zip_path)

    size = zip_path.stat().st_size
    size_mb = size / 1024 / 1024
    print(f"  {zip_path.name}  {size_mb:.2f} MB")
    if size > MAX_ZIP_BYTES:
        print(f"  [FAIL] 超过平台 3MB 上限")
        return 1
    print(f"  体积校验 OK（上限 3MB，已用 {size_mb / 3 * 100:.1f}%）")

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    top_level = sorted({n.split("/")[0] for n in names})
    print(f"  zip 顶层：{top_level}")
    if top_level != [SKILL_NAME]:
        print(f"  [FAIL] zip 顶层必须只有一个目录 {SKILL_NAME}/")
        return 1
    if f"{SKILL_NAME}/SKILL.md" not in names:
        print("  [FAIL] zip 内缺少 {0}/SKILL.md".format(SKILL_NAME))
        return 1

    if not args.keep_stage:
        shutil.rmtree(stage)

    print(f"\n[DONE] {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
