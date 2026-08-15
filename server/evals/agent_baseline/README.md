# Agent Baseline Evaluation

这一目录保存真实模型内容 Agent 的第一轮脱敏评测资料。

## 文件

- `cases.json`：评测输入和人工预期边界。
- `scorecard.md`：人工评分规则和硬失败条件。
- `runs/`：runner 产生的单次或多次模型运行记录。
- 每条 run record 包含 `automatic_hard_failures` 初筛标签；它只用于回归筛查，不替代人工评分。
- `scores/`：与 run 一一对应的人工评分、硬失败和人工修订稿。
- `baseline-report.md`：人工完成评分后的汇总报告。

## 运行

在 `server/` 目录执行：

```sh
MODEL_PROVIDER=deepseek uv run python scripts/run_agent_eval.py \
  --repetitions 2 \
  --run-id baseline-20260809
```

默认关闭模型响应缓存，确保重复尝试是真实的模型调用；结果只写入 `runs/<run-id>.json`。运行失败也会写入记录，不会静默丢弃。

评测资料只允许使用脱敏文本，不得加入真实照片、姓名、联系方式、精确地址、API key 或完整模型请求消息。

后续 Agent、事实检查或安全规则发生变化时，必须使用同一批案例重新运行，并新增独立的 `runs/`、`scores/` 记录后更新 `baseline-report.md`，不得覆盖历史基线。
