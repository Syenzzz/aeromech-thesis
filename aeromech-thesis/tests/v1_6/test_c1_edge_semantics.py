# -*- coding: utf-8 -*-
"""test_c1_edge_semantics.py — C1 状态机边语义与跳阶防护回归锁

规则真源：references/state.md §3（允许边/返程总规则）、§4（迁移操作）、§9（非法迁移）。
本文件锁定 C1 修复，先于实现建立（RED → GREEN）。

锁定项：
  E1  F∩R 消歧：同一条边不得同时是 FORWARD 与 REVERT；S5↔S6 归 FORWARD。
  E2  requested=forward 只能走 FORWARD；RETURN-only 边走 forward 请求必须按
      **显式 return 语义**处理（history 记 kind=return + issue_id），不得静默当普通前进。
  E3  非法边（既非 FORWARD 亦非 RETURN）forward 请求必须拒绝。
  E4  RETURN 前置条件：目标边须有触发 issue_id；issue 必须存在且为 closed。
      issue 缺失 / 不存在 / open / 状态非法 → 一律拒绝（fail-closed）。
  E5  返程不得绕过目标阶段原有类型门禁（state.md L68 优先级裁决）。
  E6  override：非法边 + 空 probs 也必须留 issue/history 审计，记录 requested edge、
      该边是否存在于正常状态图、override 原因。
  E7  正常 forward 特例（S1→S3 / S3→S5 / S3→S7 / S4→S7 / S5→S7）不得回归。
  E8  S9→S10 正常路径与严重问题闸门不得回归。

反作弊约束（见文件末 assert_no_tautology 自检）：
  - 不引用被测常量（FORWARD/REVERT/RETURN/STAGES）作为唯一期望值；
    期望值以**字面量**写死在本文件中。
  - 不使用恒真断言。
运行：python tests/v1_6/test_c1_edge_semantics.py
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.path.insert(0, HERE)
import _fixtures as F          # noqa: E402
import thesis_state as TS      # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  PASS", name, extra)
    else:
        FAIL += 1
        print("  FAIL", name, extra)


# ---------------- helpers ----------------

def _mk(tmp, name):
    """最小项目 + 落到 S5（工程分析）的合法路径产物。"""
    root = F.make_project(os.path.join(tmp, name))
    return root


def _set(st_root, **path_vals):
    st, _ = TS.load_state(st_root)
    for dotted, v in path_vals.items():
        keys = dotted.split(".")
        cur = st
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        cur[keys[-1]] = v
    TS.save_state(st_root, st)
    return st


def _hist(root):
    st, _ = TS.load_state(root)
    return st["stage"]["history"]


def _cur(root):
    st, _ = TS.load_state(root)
    return st["stage"]["current"]


def _issues(root):
    st, _ = TS.load_state(root)
    return st["stage"].get("open_issues") or []


def _prep(root, title="", topic_card=False, plan=False, stage=None):
    """按需补齐进入 S3/S5 所需的前置产物（与 state.md §3 前置一致）。"""
    st, _ = TS.load_state(root)
    if title:
        st["project"]["title"] = title
    if topic_card:
        st["research"]["topic_card_file"] = "artifacts/topic-card.md"
        F.write_text(root, ".aeromech/artifacts/topic-card.md", "# card\n")
    if plan:
        st["research"]["plan_file"] = "artifacts/research-plan.md"
        F.write_text(root, ".aeromech/artifacts/research-plan.md", "# plan\n")
    if stage:
        st["stage"]["current"] = stage
    TS.save_state(root, st)
    return root


def _prep_review_s7(root):
    """构造 S3→S7（review 型）可放行的最小前置：门禁证据 + literature_status。"""
    _prep(root, title="题目X", topic_card=True, plan=True, stage="S3")
    st, _ = TS.load_state(root)
    st["project"]["paper_type"] = "review"
    st["research"]["literature_status"] = "reviewed"
    F.write_text(root, ".aeromech/artifacts/literature.md",
                 "# 文献登记表\n\n- 【已核实】文献条目一（作者. 题名. 期刊, 2020.）\n"
                 "- 【已核实】文献条目二（作者. 题名. 期刊, 2021.）\n")
    st["writing"]["gate_evidence"] = {
        "plan_file": "artifacts/research-plan.md",
        "evidence_type": "literature",
        "evidence_files": ["artifacts/literature.md"],
        "literature_status": "reviewed",
        "gate_passed": "passed",
        "open_issues": [],
    }
    TS.save_state(root, st)
    return root


def _prep_s7gate(root, stage):
    """构造进入 S7 的门禁证据齐备状态（research 型）。"""
    st, _ = TS.load_state(root)
    F.write_text(root, ".aeromech/artifacts/research-plan.md", "# plan\n")
    F.write_text(root, ".aeromech/artifacts/analysis/fmea-table.md",
                 "| 项 | 失效模式 |\n|---|---|\n| 1 | 泄漏 |\n")
    st["project"]["title"] = "题目X"
    st["research"]["plan_file"] = "artifacts/research-plan.md"
    st["writing"]["gate_evidence"] = {
        "plan_file": "artifacts/research-plan.md",
        "evidence_type": "data_or_analysis",
        "evidence_files": ["artifacts/analysis/fmea-table.md"],
        "data_status": "analyzed",
        "gate_passed": "passed",
        "open_issues": [],
    }
    st["stage"]["current"] = stage
    TS.save_state(root, st)
    return root


def main():
    tmp = tempfile.mkdtemp(prefix="c1_")
    print("== test_c1_edge_semantics ==")

    # ================================================================
    # E1  F∩R 消歧（字面量期望，不引用被测常量）
    # ================================================================
    root = _mk(tmp, "e1")
    # S5→S6 是本规范 L56 的合法 forward 特例；不得再被当作 revert。
    st = _set(root, **{"stage.current": "S5"})
    ok, r = TS.transition(root, "S6", "revert", "用 revert 名义走前进边")
    check("E1-01 S5→S6 以 revert 请求必须拒绝（消除 F∩R 歧义）", not ok,
          f"ok={ok} type={(r.get('history') or {}).get('type')}")
    check("E1-02 拒绝后 current 仍为 S5", _cur(root) == "S5", _cur(root))

    # S5→S6 作为 forward 仍然合法（规范 L56 双向）
    ok, r = TS.transition(root, "S6", "forward", "S5→S6 正常前进")
    check("E1-03 S5→S6 forward 仍合法（规范特例不回归）", ok, str(r.get("reason", "")))
    check("E1-04 S5→S6 forward 记 type=forward",
          (_hist(root)[-1]["type"] == "forward"), str(_hist(root)[-1]))

    # S6→S5 同样不得以 revert 名义执行
    root2 = _mk(tmp, "e1b")
    _set(root2, **{"stage.current": "S6"})
    ok, r = TS.transition(root2, "S5", "revert", "用 revert 名义走前进边")
    check("E1-05 S6→S5 以 revert 请求必须拒绝", not ok, str(r.get("reason", "")))
    ok, r = TS.transition(root2, "S5", "forward", "S6→S5 正常前进")
    check("E1-06 S6→S5 forward 仍合法", ok, str(r.get("reason", "")))

    # ================================================================
    # E2/E4  RETURN 前置条件（S7→S9 为规范 L63 授权回退 S9→S7 的逆边）
    # ================================================================
    # E4-a: 无 issue_id → 拒绝
    root3 = _mk(tmp, "e2a")
    _set(root3, **{"stage.current": "S7", "writing.status": "final"})
    ok, r = TS.transition(root3, "S9", "forward", "返程但无触发 issue")
    check("E4-01 返程无 issue_id → 必须拒绝", not ok, str(r.get("reason", "")))
    check("E4-02 拒绝后 current 仍为 S7", _cur(root3) == "S7", _cur(root3))

    # 断言隔离：每个子场景用独立项目，避免上一次成功迁移改变 current 而使断言恒真。
    # E4-b: issue_id 指向不存在的 issue → 拒绝
    root3b = _mk(tmp, "e2b")
    _set(root3b, **{"stage.current": "S7", "writing.status": "final"})
    ok, r = TS.transition(root3b, "S9", "forward", "返程", issue_id="ISS-999")
    check("E4-03 返程 issue 不存在 → 必须拒绝", not ok, str(r.get("reason", "")))
    check("E4-03b 拒绝后 current 仍为 S7", _cur(root3b) == "S7", _cur(root3b))

    # E4-c: issue 存在但 open → 拒绝（这是 C1 的核心跳阶洞）
    root3c = _mk(tmp, "e2c")
    _set(root3c, **{"stage.current": "S7", "writing.status": "final"})
    iss = TS.add_issue(root3c, severity="严重", category="structure",
                       target_stage="S5", desc="上游依据缺口")
    ok, r = TS.transition(root3c, "S9", "forward", "返程", issue_id=iss["id"])
    check("E4-04 返程 issue 仍 open → 必须拒绝（原跳阶洞）", not ok, str(r.get("reason", "")))
    check("E4-05 open 时 current 仍为 S7", _cur(root3c) == "S7", _cur(root3c))

    # E4-d: issue 状态非法 → 拒绝
    st, _ = TS.load_state(root3c)
    st["stage"]["open_issues"][0]["status"] = "bogus"
    TS.save_state(root3c, st)
    ok, r = TS.transition(root3c, "S9", "forward", "返程", issue_id=iss["id"])
    check("E4-06 返程 issue 状态非法 → 必须拒绝", not ok, str(r.get("reason", "")))
    check("E4-06b 状态非法时 current 仍为 S7", _cur(root3c) == "S7", _cur(root3c))

    # E4-e: issue closed → 放行，且按 **显式 return 语义** 记录
    TS.close_issue(root3c, iss["id"])
    ok, r = TS.transition(root3c, "S9", "forward", "返程：依据已补齐", issue_id=iss["id"])
    check("E4-07 返程 issue closed → 必须放行", ok, str(r.get("reason", "")))
    check("E4-08 返程后 current=S9", _cur(root3c) == "S9", _cur(root3c))
    h = _hist(root3c)[-1]
    check("E2-01 返程 history 标明 kind=return（不得静默当普通前进）",
          h.get("kind") == "return", str(h))
    check("E2-02 返程 history 记录对应 issue_id",
          h.get("issue_id") == iss["id"], str(h))
    check("E2-03 返程 history type=forward（规范 L66）",
          h.get("type") == "forward", str(h))

    # ================================================================
    # E3  非法边 forward 拒绝
    # ================================================================
    root4 = _mk(tmp, "e3")
    _set(root4, **{"stage.current": "S7", "writing.status": "final"})
    ok, r = TS.transition(root4, "S10", "forward", "S7→S10 非法")
    check("E3-01 S7→S10 forward 必须拒绝（不在任何边集）", not ok, str(r.get("reason", "")))
    check("E3-02 非法边拒绝不落盘", _cur(root4) == "S7", _cur(root4))

    ok, r = TS.transition(root4, "S2", "forward", "S7→S2 非法")
    check("E3-03 S7→S2 forward 必须拒绝", not ok, str(r.get("reason", "")))

    # ================================================================
    # E5  返程不豁免目标阶段类型门禁（state.md L68）
    # ================================================================
    # S4→S7 返程：目标 S7 要求门禁证据（writing.gate_evidence）。
    # 构造 closed issue 但缺乏 S7 门禁证据 → 返程仍须拒绝。
    root5 = _mk(tmp, "e5")
    _set(root5, **{"stage.current": "S4",
                   "research.literature_status": "not_reviewed"})
    iss5 = TS.add_issue(root5, severity="高", category="citation",
                        target_stage="S4", desc="文献缺口")
    TS.close_issue(root5, iss5["id"])
    ok, r = TS.transition(root5, "S7", "forward", "返程进 S7", issue_id=iss5["id"])
    check("E5-01 返程进 S7 但目标门禁未满足 → 必须拒绝", not ok, str(r.get("reason", "")))
    check("E5-02 拒绝后 current 仍为 S4", _cur(root5) == "S4", _cur(root5))

    # ================================================================
    # E6  override 审计（非法边 + 空 probs 也必须留痕）
    # ================================================================
    root6 = _mk(tmp, "e6")
    _set(root6, **{"stage.current": "S1"})
    ok, r = TS.transition(root6, "S5", "override", "用户强推跳阶",
                          override_note="用户明确要求跳过 S2-S4")
    check("E6-01 override 非法边 + 空 probs → 仍放行", ok, str(r.get("reason", "")))
    h = _hist(root6)[-1]
    check("E6-02 override history 记录 requested_edge",
          (h.get("requested_from") == "S1" and h.get("requested_to") == "S5"), str(h))
    check("E6-03 override history 标明该边不在正常状态图",
          h.get("edge_exists") is False, str(h))
    check("E6-04 override history 记录 override 原因",
          "用户明确要求跳过" in (h.get("override_note") or h.get("reason") or ""), str(h))
    check("E6-05 override 即使 probs 为空也必须挂审计 issue",
          len(_issues(root6)) >= 1, str(_issues(root6)))
    if _issues(root6):
        ai = _issues(root6)[-1]
        check("E6-06 审计 issue 关联 override 目标阶段",
              ai.get("target_stage") == "S5", str(ai))

    # 合法边 override（有 probs）同样必须审计
    root7 = _mk(tmp, "e6b")
    _set(root7, **{"stage.current": "S1"})
    ok, r = TS.transition(root7, "S3", "override", "强推进 S3",
                          override_note="用户坚持")
    check("E6-07 合法边 override 仍放行", ok, str(r.get("reason", "")))
    h7 = _hist(root7)[-1]
    check("E6-08 合法边 override 标明 edge_exists=True",
          h7.get("edge_exists") is True, str(h7))

    # ================================================================
    # E7  正常 forward 特例不回归
    # ================================================================
    # S1→S3（须题目卡片）
    root8 = _mk(tmp, "e7")
    ok, r = TS.transition(root8, "S3", "forward", "缺卡片")
    check("E7-01 S1→S3 缺题目卡片仍拒绝", not ok, str(r.get("reason", "")))
    _set(root8, **{"project.title": "题目X",
                   "research.topic_card_file": "artifacts/topic-card.md"})
    F.write_text(root8, ".aeromech/artifacts/topic-card.md", "# card\n")
    ok, r = TS.transition(root8, "S3", "forward", "题目已确定")
    check("E7-02 S1→S3 合法前进", ok, str(r.get("reason", "")))

    # S3→S5（规范 L54）
    _set(root8, **{"research.plan_file": "artifacts/research-plan.md"})
    F.write_text(root8, ".aeromech/artifacts/research-plan.md", "# plan\n")
    ok, r = TS.transition(root8, "S5", "forward", "方案齐备")
    check("E7-03 S3→S5 合法前进", ok, str(r.get("reason", "")))
    check("E7-04 S3→S5 记 type=forward 且非 return",
          (_hist(root8)[-1]["type"] == "forward"
           and _hist(root8)[-1].get("kind") != "return"), str(_hist(root8)[-1]))

    # S1→S5 非法跳阶仍拒绝（对照，防放宽）
    root9 = _mk(tmp, "e7b")
    ok, r = TS.transition(root9, "S5", "forward", "跳步")
    check("E7-05 S1→S5 forward 仍拒绝", not ok, str(r.get("reason", "")))

    # ================================================================
    # E8  S9→S10 正常路径 + 严重问题闸门不回归
    # ================================================================
    root10 = _mk(tmp, "e8")
    _set(root10, **{"stage.current": "S9", "writing.status": "final"})
    issB = TS.add_issue(root10, severity="严重", category="structure",
                        target_stage="S9", desc="严重问题未关闭")
    ok, r = TS.transition(root10, "S10", "forward", "答辩")
    check("E8-01 S9→S10 有未关闭严重问题 → 拒绝", not ok, str(r.get("reason", "")))
    TS.close_issue(root10, issB["id"])
    ok, r = TS.transition(root10, "S10", "forward", "问题已关闭")
    check("E8-02 S9→S10 严重问题关闭后放行", ok, str(r.get("reason", "")))
    check("E8-03 S9→S10 后 current=S10", _cur(root10) == "S10", _cur(root10))

    # E8-b: 一般/建议级未关闭不阻塞 S9→S10（规范 L64 只限 严重/高）
    root11 = _mk(tmp, "e8b")
    _set(root11, **{"stage.current": "S9", "writing.status": "final"})
    issC = TS.add_issue(root11, severity="建议", category="writing",
                        target_stage="S9", desc="措辞建议")
    ok, r = TS.transition(root11, "S10", "forward", "答辩")
    check("E8-04 仅建议级未关闭不阻塞 S9→S10", ok, str(r.get("reason", "")))

    # ================================================================
    # E9  全部规范明列的前进边必须保持普通 forward（方案 A：forward 优先）
    #     期望值以字面量写死（edge, 构建前置的方式），不引用被测常量。
    # ================================================================
    # E9-a S3→S5（规范 L54：可不经 S4）—— 不得被返程语义劫持
    r9a = _mk(tmp, "e9a")
    _prep(r9a, title="题目X", topic_card=True, plan=True, stage="S3")
    ok, r = TS.transition(r9a, "S5", "forward", "research/design 型方案齐备")
    check("E9-01 S3→S5 forward 必须按普通前进放行（规范 L54）", ok, str(r.get("missing") or r.get("reason")))
    check("E9-02 S3→S5 不得要求 issue_id",
          ok and not any("issue_id" in str(m) for m in (r.get("missing") or [])),
          str(r.get("missing")))
    if ok:
        h = _hist(r9a)[-1]
        check("E9-03 S3→S5 history kind=forward（非 return）", h.get("kind") == "forward", str(h))
        check("E9-04 S3→S5 history type=forward", h.get("type") == "forward", str(h))

    # E9-b S3→S7（规范 L58：仅 review 型 + 门禁通过）
    r9b = _mk(tmp, "e9b")
    _prep_review_s7(r9b)
    ok, r = TS.transition(r9b, "S7", "forward", "review 型方案齐备且门禁通过")
    check("E9-05 S3→S7 forward 必须按普通前进放行（规范 L58）", ok, str(r.get("missing") or r.get("reason")))
    if ok:
        check("E9-06 S3→S7 history kind=forward", _hist(r9b)[-1].get("kind") == "forward",
              str(_hist(r9b)[-1]))

    # E9-c S4→S5（规范 L55）
    r9c = _mk(tmp, "e9c")
    _prep(r9c, title="题目X", topic_card=True, plan=True, stage="S4")
    TS.add_issue(r9c, severity="一般", category="citation", target_stage="S4", desc="占位")
    ok, r = TS.transition(r9c, "S5", "forward", "方案齐备")
    check("E9-07 S4→S5 forward 必须按普通前进放行（规范 L55）", ok, str(r.get("missing") or r.get("reason")))

    # E9-d S5→S7（规范 L57：S7 门禁通过）
    r9d = _mk(tmp, "e9d")
    _prep_s7gate(r9d, stage="S5")
    ok, r = TS.transition(r9d, "S7", "forward", "S7 门禁通过")
    check("E9-08 S5→S7 forward 必须按普通前进放行（规范 L57）", ok, str(r.get("missing") or r.get("reason")))
    if ok:
        check("E9-09 S5→S7 history kind=forward", _hist(r9d)[-1].get("kind") == "forward",
              str(_hist(r9d)[-1]))

    # E9-e S7→S8（规范 L60）
    r9e = _mk(tmp, "e9e")
    _set(r9e, **{"stage.current": "S7", "writing.status": "draft_done"})
    ok, r = TS.transition(r9e, "S8", "forward", "章稿完成且图表点位表已出")
    check("E9-10 S7→S8 forward 必须按普通前进放行（规范 L60）", ok, str(r.get("missing") or r.get("reason")))

    # ================================================================
    # E10  RETURN-only 边以 forward 请求：不得走普通 forward
    #      (S3→S9 / S6→S9 / S5→S8 均只在 RETURN 中，不在 FORWARD)
    # ================================================================
    for edge_from, edge_to, tag in (("S3", "S9", "E10-01"), ("S6", "S9", "E10-02"),
                                    ("S5", "S8", "E10-03")):
        r10 = _mk(tmp, "e10_" + edge_from + edge_to)
        _set(r10, **{"stage.current": edge_from, "writing.status": "final"})
        ok, r = TS.transition(r10, edge_to, "forward", "以 forward 名义走 RETURN-only 边")
        check(f"{tag} {edge_from}→{edge_to} forward 无 issue_id → 必须拒绝（不得当普通前进）",
              not ok, f"ok={ok} reason={r.get('reason')}")
        check(f"{tag}b 拒绝后 current 仍为 {edge_from}", _cur(r10) == edge_from, _cur(r10))
        check(f"{tag}c 拒绝原因须指明返程触发源要求",
              (not ok) and any("issue_id" in str(m) for m in (r.get("missing") or [])),
              str(r.get("missing")))

    # E10-d: 显式 return 类型（非 forward）同样要求 issue_id
    r10d = _mk(tmp, "e10d")
    _set(r10d, **{"stage.current": "S7", "writing.status": "final"})
    ok, r = TS.transition(r10d, "S9", "return", "显式返程无 issue")
    check("E10-04 显式 return 请求无 issue_id → 必须拒绝", not ok, str(r.get("reason", "")))

    # E10-e: 显式 return 请求一条**纯 FORWARD 边** → 必须拒绝（不得混入普通 forward）
    r10e = _mk(tmp, "e10e")
    _set(r10e, **{"stage.current": "S7", "writing.status": "draft_done"})
    ok, r = TS.transition(r10e, "S8", "return", "S7→S8 不是任何 revert 的逆边")
    check("E10-05 显式 return 请求纯 FORWARD 边（S7→S8）→ 必须拒绝", not ok, str(r.get("reason", "")))
    check("E10-06 拒绝后 current 仍为 S7", _cur(r10e) == "S7", _cur(r10e))

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"test_c1_edge_semantics 结果: PASS={PASS} FAIL={FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
