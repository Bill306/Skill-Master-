# Hedge Fund Agent Team — 工作流程示意图

## 完整工作流程 (Full Workflow)

```mermaid
flowchart TB
    subgraph TRIGGER["🔔 触发层 Trigger"]
        U["用户手动触发<br/>Manual Launch"]
        EM["事件监控 Event Monitor<br/>VIX飙升 / 止损触发 / 财报 / FOMC"]
    end

    subgraph DATA["📊 数据源 Data Sources"]
        YF["Yahoo Finance<br/>价格 / 基本面"]
        LB["Longbridge<br/>港股实时 / 北向资金"]
        TV["TradingView<br/>技术评级"]
        NEWS["AI News Digest<br/>新闻情绪"]
    end

    subgraph P0["Phase 0 — 历史回顾 (Historian)"]
        H["📜 Historian 历史学家"]
        H --> H1["回顾30天交易记录"]
        H --> H2["计算实际盈亏 P&L"]
        H --> H3["生成贝叶斯可信度评分<br/>Trust Weight 0.5x ~ 1.5x"]
    end

    subgraph P1["Phase 1 — 独立研究 (5个Agent并行)"]
        direction LR
        MA["🌍 Macro Analyst<br/>宏观分析师"]
        QR["📈 Quant Researcher<br/>量化研究员"]
        FA["💰 Fundamental Analyst<br/>基本面分析师"]
        SA["💬 Sentiment Analyst<br/>情绪分析师"]
        TR["🎯 Trader<br/>交易员"]
    end

    subgraph P1_OUT["Phase 1 输出"]
        direction LR
        MA_O["macro.json<br/>市场体制: RISK-ON/OFF<br/>3大主题 + 催化剂"]
        QR_O["quant.json<br/>动量/波动率/均值回归<br/>因子评分 + 异常检测"]
        FA_O["fundamental.json<br/>估值评级: BUY/SELL<br/>公允价值目标"]
        SA_O["sentiment.json<br/>情绪评分: -1.0 ~ +1.0<br/>VIX + 资金流向"]
        TR_O["trader.json<br/>入场/止损/止盈<br/>仓位大小 + 置信度"]
    end

    subgraph P2["Phase 2 — 交叉质疑 (Cross-Challenge)"]
        RT["🔴 Red Team 红队<br/>强制反对 · 不可同意"]
        RT --> RT1["每个LONG → 构建最强BEAR case"]
        RT --> RT2["每个SELL → 构建BULL case"]
        RT --> RT3["历史失败先例 + 隐藏风险"]
        CROSS["跨Agent质疑"]
        CROSS --> C1["Trader质疑Fundamental时机"]
        CROSS --> C2["Quant验证Sentiment信号"]
        CROSS --> C3["Macro约束所有建议"]
    end

    subgraph P3["Phase 3 — 风险审查 (Risk Review)"]
        RM["🛡️ Risk Manager 风控经理<br/>拥有 VETO 否决权"]
        RM --> RM1["VaR 95%/99%"]
        RM --> RM2["压力测试:<br/>2008金融危机 / COVID<br/>加息200bp / 中国硬着陆<br/>AI泡沫破裂"]
        RM --> RM3["合规检查:<br/>单仓 ≤10% / 行业 ≤30%<br/>国家 ≤50%"]
        RM --> RM4["❌ VETO 违规交易"]
    end

    subgraph P4["Phase 4 — 综合决策 (Synthesis)"]
        PM["👔 Portfolio Manager<br/>投资组合经理 (Lead)"]
        PM --> PM1["按可信度加权建议"]
        PM --> PM2["回应Red Team质疑"]
        PM --> PM3["解决Agent分歧"]
        PM --> PM4["生成最终投资备忘录"]
    end

    subgraph OUTPUT["📋 最终输出"]
        MEMO["investment_memo.md<br/>━━━━━━━━━━━━━━<br/>市场体制 + 可信度表<br/>交易建议 (入场/止损/目标)<br/>Red Team质疑 + PM回应<br/>风险报告 + 压力测试<br/>异议观点记录"]
        HIST["trade_history.jsonl<br/>持久化交易记录"]
        CRED["agent_credibility.json<br/>更新后的可信度评分"]
    end

    %% 连接线
    U --> P0
    EM --> P0

    YF --> P1
    LB --> P1
    TV --> P1
    NEWS --> P1

    P0 -->|"可信度评分注入所有Agent"| P1

    MA --> MA_O
    QR --> QR_O
    FA --> FA_O
    SA --> SA_O
    TR --> TR_O

    P1_OUT --> P2
    P2 --> P3
    P3 --> P4

    PM4 --> MEMO
    PM4 --> HIST
    PM4 --> CRED

    HIST -.->|"反馈循环<br/>30天后回顾"| H

    %% 样式
    classDef phase0 fill:#4a90d9,stroke:#2c5282,color:#fff
    classDef phase1 fill:#48bb78,stroke:#276749,color:#fff
    classDef phase2 fill:#ed8936,stroke:#c05621,color:#fff
    classDef phase3 fill:#e53e3e,stroke:#9b2c2c,color:#fff
    classDef phase4 fill:#805ad5,stroke:#553c9a,color:#fff
    classDef data fill:#38b2ac,stroke:#285e61,color:#fff
    classDef output fill:#d69e2e,stroke:#975a16,color:#fff

    class H phase0
    class MA,QR,FA,SA,TR phase1
    class RT,CROSS phase2
    class RM phase3
    class PM phase4
    class YF,LB,TV,NEWS data
    class MEMO,HIST,CRED output
```

## 简化流程图 (Simplified)

```mermaid
flowchart LR
    H["📜 Historian<br/>Phase 0"]
    -->|可信度| R["🔬 5个研究Agent<br/>Phase 1 (并行)"]
    -->|研究报告| RT["🔴 Red Team<br/>Phase 2"]
    -->|质疑报告| RM["🛡️ Risk Manager<br/>Phase 3"]
    -->|风控审查| PM["👔 PM 综合决策<br/>Phase 4"]
    -->|投资备忘录| OUT["📋 Output"]
    OUT -.->|"反馈循环"| H
```

## Agent 职责速查表

| Phase | Agent | 职责 | 核心输出 |
|-------|-------|------|---------|
| 0 | Historian 历史学家 | 回顾历史交易, 计算P&L, 生成可信度评分 | `agent_credibility.json` |
| 1 | Macro Analyst 宏观分析师 | 央行政策, 收益率曲线, 通胀, 市场体制分类 | `macro.json` |
| 1 | Quant Researcher 量化研究员 | 动量因子, 波动率, 均值回归, 相关性矩阵 | `quant.json` |
| 1 | Fundamental Analyst 基本面分析师 | 财报分析, 估值模型(DCF), 行业对比 | `fundamental.json` |
| 1 | Sentiment Analyst 情绪分析师 | 新闻情绪, VIX, 资金流向, 北向资金 | `sentiment.json` |
| 1 | Trader 交易员 | 技术分析(RSI/MACD/BB), 入场/止损/止盈 | `trader.json` |
| 2 | Red Team 红队 | **强制反对**, 构建反向论点, 寻找失败先例 | `red_team.json` |
| 3 | Risk Manager 风控经理 | VaR, 压力测试, 合规检查, **否决权(VETO)** | `risk.json` |
| 4 | Portfolio Manager 组合经理 | 加权综合, 回应质疑, 最终决策 | `investment_memo.md` |

## 团队配置选项

```mermaid
flowchart TB
    subgraph FULL_V2["完整版 v2 (8 Agents · ~150-200K tokens)"]
        direction LR
        f2["Historian + Macro + Quant + Fundamental<br/>+ Sentiment + Trader + Red Team + Risk"]
    end

    subgraph FULL_V1["标准版 v1 (6 Agents · ~80-120K tokens)"]
        direction LR
        f1["Macro + Quant + Fundamental<br/>+ Sentiment + Trader + Risk"]
    end

    subgraph QUICK["快速版 (3 Agents · ~40-60K tokens)"]
        direction LR
        q["Researcher + Risk + Trader"]
    end

    subgraph EVENT["事件驱动配置"]
        direction LR
        E1["🚨 紧急 (VIX飙升)<br/>Macro + Risk + Trader"]
        E2["📊 财报 (Earnings)<br/>Fundamental + Sentiment<br/>+ Trader + Red Team"]
        E3["🏛️ FOMC/CPI<br/>Macro + Quant<br/>+ Risk + Trader"]
    end
```

## 数据源映射

```mermaid
flowchart LR
    subgraph SOURCES["数据源"]
        YF["Yahoo Finance 🆓<br/>无需API Key"]
        LB["Longbridge 🔑<br/>需要API Key"]
        TV["TradingView 🆓<br/>tradingview-ta"]
        ND["AI News Digest 📰"]
    end

    subgraph COVERAGE["覆盖范围"]
        US["🇺🇸 美股<br/>NVDA, MSFT, AAPL<br/>GOOGL, META, AMZN"]
        HK["🇭🇰 港股<br/>9988, 0700, 9888<br/>3690, 1810"]
        CR["₿ 加密货币<br/>BTC, ETH, SOL"]
        MC["📊 宏观指标<br/>VIX, DXY, Gold<br/>Oil, US10Y"]
    end

    YF --> US
    YF --> HK
    YF --> CR
    YF --> MC
    LB --> HK
    LB --> US
    TV --> US
    TV --> HK
    TV --> CR
    ND --> US
    ND --> HK
```
