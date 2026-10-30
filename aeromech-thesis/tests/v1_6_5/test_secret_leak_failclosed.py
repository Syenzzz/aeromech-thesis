# -*- coding: utf-8 -*-
"""test_secret_leak_failclosed.py — C4/H9 回归锁：扫描面不可用不得伪装 PASS

背景（2026-10-02 审查发现的 fail-open）：
  旧 `secret_leak_qa` 在 git 不可用时 `except: return` —— 一个文件都不扫，
  却照常返回 `status="PASS"`、退出码 0；docx/pdf 文本层提取失败也 yield 空串
  并计入"已扫描"。结果是"没能扫描"被当成"没有问题"。
  且该模块**未接入 delivery_gate**，报告缺失不会阻断交付。

本测试锁死修复后的语义：
  · 正常扫描 → PASS，且报告含 scanned_files
  · git 不可用（repo/diff scope）→ UNAVAILABLE，非 PASS，退出码 3
  · artifacts 目录不存在 → UNAVAILABLE，非 PASS
  · 任一 scope 不可用 → delivery_gate 该域 ERROR → 终局不透 PASS
  · 现有检测规则不得降级（真实 Key 仍判 FAIL）

全部走真实函数调用与真实子进程，不使用 mock 替代被测逻辑。
运行：python tests/v1_6_5/test_secret_leak_failclosed.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.abspath(os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, os.path.join(HERE, "..", "v1_6"))
import delivery_gate as DG
import secret_leak_qa as SL

PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS", name, extra)
    else:
        FAIL += 1
        print("  FAIL", name, extra)


def _run_cli(root, scope):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "secret_leak_qa.py"),
                        root, "--scope", scope],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="slfc_")
    print("== test_secret_leak_failclosed ==")

    # ---------- 1. 正常扫描 → PASS（含 scanned_files） ----------
    good = os.path.join(tmp, "good")
    os.makedirs(os.path.join(good, ".aeromech", "artifacts"), exist_ok=True)
    with open(os.path.join(good, ".aeromech", "artifacts", "x.md"), "w",
              encoding="utf-8") as f:
        f.write("普通内容，无凭据。\n")
    r1 = SL.run(good, "artifacts")
    check("C4-01 正常扫描（artifacts）→ PASS", r1["status"] == "PASS", r1["status"])
    check("C4-02 报告含 scanned_files 且 >0", r1.get("scanned_files", 0) > 0,
          str(r1.get("scanned_files")))
    check("C4-03 正常扫描时 unavailable_scopes 为空",
          r1.get("unavailable_scopes") == [], str(r1.get("unavailable_scopes")))

    # ---------- 2. git 不可用 → 非 PASS ----------
    # 非 git 目录下 repo/diff scope 必然不可用
    nongit = os.path.join(tmp, "nongit")
    os.makedirs(os.path.join(nongit, ".aeromech"), exist_ok=True)
    r2 = SL.run(nongit, "repo")
    check("C4-04 git 不可用时 repo scope → 非 PASS",
          r2["status"] != "PASS", r2["status"])
    check("C4-05 明确标为 UNAVAILABLE", r2["status"] == "UNAVAILABLE", r2["status"])
    check("C4-06 列出 unavailable_scopes（含原因）",
          len(r2.get("unavailable_scopes") or []) > 0 and
          "git" in " ".join(r2["unavailable_scopes"]).lower(),
          str(r2.get("unavailable_scopes"))[:80])
    rc2, out2 = _run_cli(nongit, "repo")
    check("C4-07 CLI 退出码非 0（UNAVAILABLE=3）", rc2 == 3, f"rc={rc2}")
    check("C4-08 CLI 输出不再出现 PASS", "PASS" not in out2, out2.strip()[:60])

    r2b = SL.run(nongit, "diff")
    check("C4-09 git 不可用时 diff scope → 非 PASS",
          r2b["status"] != "PASS", r2b["status"])

    r2c = SL.run(nongit, "all")
    check("C4-10 all scope 在 git 不可用时 → 非 PASS",
          r2c["status"] != "PASS", r2c["status"])
    check("C4-11 all scope 明确列出不可用的子面",
          len(r2c.get("unavailable_scopes") or []) >= 2,
          str(len(r2c.get("unavailable_scopes") or [])))

    # ---------- 3. artifacts 不可用 → 非 PASS ----------
    noart = os.path.join(tmp, "noartifacts")
    os.makedirs(noart, exist_ok=True)          # 无 .aeromech
    r3 = SL.run(noart, "artifacts")
    check("C4-12 .aeromech 不存在时 artifacts scope → 非 PASS",
          r3["status"] != "PASS", r3["status"])
    check("C4-13 明确标为 UNAVAILABLE", r3["status"] == "UNAVAILABLE", r3["status"])

    # ---------- 4. 检测规则不得降级：真实 Key 仍判 FAIL ----------
    leak = os.path.join(tmp, "leak")
    os.makedirs(os.path.join(leak, ".aeromech", "artifacts"), exist_ok=True)
    with open(os.path.join(leak, ".aeromech", "artifacts", "cfg.md"), "w",
              encoding="utf-8") as f:
        f.write('api_key = "sk-live-9f8e7d6c5b4a39281706f5e4d3c2b1a0"\n')
    r4 = SL.run(leak, "artifacts")
    check("C4-14 真实 Key 仍判 FAIL（规则未降级）", r4["status"] == "FAIL", r4["status"])
    check("C4-15 FAIL 有明细", len(r4.get("failures") or []) > 0,
          str(len(r4.get("failures") or [])))
    rc4, _ = _run_cli(leak, "artifacts")
    check("C4-16 FAIL 时 CLI 退出码 1", rc4 == 1, f"rc={rc4}")

    # 高熵 → WARN（非 FAIL）仍保留
    warn_dir = os.path.join(tmp, "warn")
    os.makedirs(os.path.join(warn_dir, ".aeromech", "artifacts"), exist_ok=True)
    with open(os.path.join(warn_dir, ".aeromech", "artifacts", "h.md"), "w",
              encoding="utf-8") as f:
        f.write("token abcDEF123ghiJKL456mnoPQR789stuVWX\n")
    r5 = SL.run(warn_dir, "artifacts")
    check("C4-17 高熵串仍记为 WARN（不误判 FAIL）", r5["status"] == "WARN", r5["status"])

    # ---------- 5. delivery_gate 接入 ----------
    check("C4-18 secret_leak 已登记为 gate 域",
          any(d == "secret_leak" for _f, d, _s in DG.FORMAT_REPORTS))

    gate = os.path.join(tmp, "gate")
    os.makedirs(os.path.join(gate, ".aeromech", "artifacts", "qa"), exist_ok=True)
    with open(os.path.join(gate, ".aeromech", "state.yaml"), "w", encoding="utf-8") as f:
        f.write("schema_version: '1.0'\nproject:\n  title: T\n  major: M\n"
                "  paper_type: research\nstage:\n  current: S9\n  history: []\n"
                "  open_issues: []\n")
    with open(os.path.join(gate, "毕业论文.docx"), "wb") as f:
        f.write(b"PK fake")
    # UNAVAILABLE 报告 → 该域必须 ERROR，终局不透 PASS
    with open(os.path.join(gate, ".aeromech", "artifacts", "qa",
                           "secret-leak-report.md"), "w", encoding="utf-8") as f:
        f.write("# Secret Leak QA\n\n"
                "- SEC-SCAN 凭据泄漏扫描: UNAVAILABLE | scope=all scanned_files=0 "
                "named_only=0 FAIL=0 WARN=0\n"
                "  - [UNAVAILABLE] repo scope 不可用：git 不可用\n")
    res5 = DG.aggregate(gate)
    d5 = {x["gate_id"]: x for x in res5["items"]}
    check("C4-19 gate 将 UNAVAILABLE 报告解析入域",
          "G-FMT-secret_leak" in d5, str(sorted(k for k in d5 if "secret" in k)))
    check("C4-20 该域记 ERROR（不可用≠通过）",
          d5.get("G-FMT-secret_leak", {}).get("status") == "ERROR",
          str(d5.get("G-FMT-secret_leak", {}).get("status")))
    check("C4-21 终局不得为 PASS",
          res5["status"] not in ("PASS", "PASS_WITH_WARNINGS"), res5["status"])

    # PASS 报告 → 该域 PASS（不误伤正常路径）
    gate2 = os.path.join(tmp, "gate2")
    shutil.copytree(gate, gate2)
    with open(os.path.join(gate2, ".aeromech", "artifacts", "qa",
                           "secret-leak-report.md"), "w", encoding="utf-8") as f:
        f.write("# Secret Leak QA\n\n"
                "- SEC-SCAN 凭据泄漏扫描: PASS | scope=all scanned_files=271 "
                "named_only=98 FAIL=0 WARN=0\n")
    d6 = {x["gate_id"]: x for x in DG.aggregate(gate2)["items"]}
    check("C4-22 正常 PASS 报告 → 该域 PASS（不误伤）",
          d6.get("G-FMT-secret_leak", {}).get("status") == "PASS",
          str(d6.get("G-FMT-secret_leak", {}).get("status")))

    # 报告缺失 + 交付物在场 → 证据缺失（沿用 A3 语义，不得静默消失）
    gate3 = os.path.join(tmp, "gate3")
    shutil.copytree(gate, gate3)
    os.remove(os.path.join(gate3, ".aeromech", "artifacts", "qa",
                           "secret-leak-report.md"))
    d7 = {x["gate_id"]: x for x in DG.aggregate(gate3)["items"]}
    check("C4-23 报告缺失且已构建 → 记 FAIL（未执行≠通过）",
          d7.get("G-FMT-secret_leak", {}).get("status") == "FAIL",
          str(d7.get("G-FMT-secret_leak", {}).get("status")))

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"test_secret_leak_failclosed 结果: PASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
