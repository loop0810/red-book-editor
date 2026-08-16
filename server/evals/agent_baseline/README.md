# Agent Baseline Evaluation

这一目录保存真实模型内容 Agent 的第一轮脱敏评测资料。

## 文件

- `cases.json`：评测输入和人工预期边界。
- `scorecard.md`：人工评分规则和硬失败条件。
- `quality-gate-manifest.json`：P1-06 的版本绑定、成本要求和阻断阈值。
- `runs/`：runner 产生的单次或多次模型运行记录。
- 每条 run record 包含 `automatic_hard_failures` 初筛标签；它只用于回归筛查，不替代人工评分。
- 新生成的 run 使用 schema version 4，并包含 `evaluation_context`、`agent_diagnostics`：阶段、步骤、修订、工具调用、重复错误、稳定失败代码、模型调用和 token usage；历史 schema 1/2/3 记录保持可读，但不能直接通过 P1-06 quality gate。
- `scores/`：与 run 一一对应的人工评分、硬失败和人工修订稿。
- `baseline-report.md`：人工完成评分后的汇总报告。
- `reports/`：质量门禁生成的 JSON/Markdown 指标和基线对比报告。

## 运行

在 `server/` 目录执行：

```sh
MODEL_PROVIDER=deepseek DEEPSEEK_MODEL=deepseek-v4-flash uv run python -m scripts.run_agent_eval \
  --repetitions 2 \
  --run-id baseline-20260809
```

价格和模型输出上限通过运行环境注入：

```sh
MODEL_PROVIDER=deepseek \
DEEPSEEK_MODEL=deepseek-v4-flash \
MODEL_MAX_TOKENS=2048 \
MODEL_TIMEOUT_SECONDS=180 \
MODEL_MAX_RETRIES=0 \
EVAL_INPUT_COST_USD_PER_MILLION=0.14 \
EVAL_OUTPUT_COST_USD_PER_MILLION=0.28 \
uv run python -m scripts.run_agent_eval \
  --repetitions 2 \
  --run-id baseline-20260809
```

默认关闭模型响应缓存，确保重复尝试是真实的模型调用；结果只写入 `runs/<run-id>.json`。运行失败也会写入记录，不会静默丢弃。

评测资料只允许使用脱敏文本，不得加入真实照片、姓名、联系方式、精确地址、API key 或完整模型请求消息。

完成同一批案例的人工评分后，从 `server/` 执行阻断式质量门禁：

```sh
EVAL_INPUT_COST_USD_PER_MILLION=0.14 \
EVAL_OUTPUT_COST_USD_PER_MILLION=0.28 \
make eval-quality-gate RUN_ID=baseline-20260809 SCORE_ID=baseline-20260809
```

也可以提供 `BASELINE_RUN_ID` 和 `BASELINE_SCORE_ID` 生成按案例、评分维度、运行诊断、token 和成本的对比。版本摘要、usage、价格、人工评分或任何门禁阈值缺失都会返回非零退出码；价格从运行环境显式传入，不把供应商价格假设写死在代码中。真实模型运行可从本地 `key.json` 读取 key 后注入进程环境，`key.json` 不得提交。

后续 Agent、事实检查或安全规则发生变化时，必须使用同一批案例重新运行，并新增独立的 `runs/`、`scores/` 记录后更新 `baseline-report.md`，不得覆盖历史基线。
