# Long-Context Alternatives: Evidence Plan

## User goals under evaluation

This investigation treats the desired product as a system for handling large bodies of text, prompt material, documents, and long-running agent history while preserving important instructions, separating less-trusted material, and making context delivery inspectable.

## Claims that require evidence

No alternative will be described as **more effective** unless a source reports measured outcomes on a relevant task or a proposed local experiment measures it. No alternative will be described as **more efficient** unless a source reports, or a local experiment measures, a relevant resource outcome such as token usage, latency, memory, throughput, or retrieval cost.

The report will distinguish three labels:

| Label | Meaning |
|---|---|
| **Established in cited evaluation** | A primary source reports a relevant result under a stated benchmark and setup. |
| **Plausible design option** | The mechanism is described or widely used, but no directly comparable evidence supports superiority for this product goal. |
| **Unverified for this product** | No cited or local experiment establishes the claim for the desired workload. |

## Decision criteria

The comparison will separate, rather than collapse, the following outcomes:

1. **Task-grounded context recall:** whether necessary information can be retrieved or used at the relevant turn.
2. **Instruction retention and source handling:** whether important, trusted constraints remain identifiable and available without treating untrusted text as authoritative.
3. **Cost and delay:** input/context tokens, retrieval work, memory footprint, and end-to-end latency.
4. **Auditability and reproducibility:** whether the exact delivered context and policy decisions can be inspected and replayed.
5. **Operational scope:** whether the evidence covers retrieval, summarization, long-context models, model behavior, tool actions, or only a simulator.

## Candidate approaches

The research will examine direct long-context prompting, retrieval-augmented generation, hierarchical summaries/memory, cache and prefix reuse, structure-aware document processing, and provenance-aware context control. It will not assume that any one method replaces the others; the evidence must support the scope of each claim.

## Verified findings: direct context, retrieval, and routing

- Li et al. (EMNLP 2024) report a comparison across public datasets and three recent LLMs: with sufficient resources, their long-context condition outperformed RAG on average, while RAG had substantially lower cost. Their proposed model self-routing hybrid reduced computation while retaining performance comparable to its long-context condition. This is evidence for that paper’s setup, not a universal ranking.
- Xu et al. (ICLR 2024) report that simple retrieval augmentation with a 4K context model reached comparable performance to their 16K extended model on their long-context tasks with less computation; retrieval also improved their tested models at extended context sizes. This supports evaluating a retrieval-plus-context hybrid rather than assuming that a larger window replaces retrieval.
- LaRA (2025) evaluated 2,326 cases across four practical QA categories and three naturally occurring long-text types, finding that the best LC-versus-RAG choice depended on model, length, task, and retrieved-chunk characteristics. It directly rejects a universal routing rule.
- SummHay (EMNLP 2024) reports a difficult multi-document synthesis setting: even an oracle document-relevance signal did not close the gap to its estimated human joint score, and the reported full-context models without a retriever scored below 20% on its metric. This is evidence that fitting text in the context window does not by itself establish reliable use of the needed information.

Sources: Li et al. 2024, https://aclanthology.org/2024.emnlp-industry.66/ ; Xu et al. 2024, https://proceedings.iclr.cc/paper_files/paper/2024/hash/d75f29006df67df084e6586f1cb8458c-Abstract-Conference.html ; Li et al. 2025, https://arxiv.org/abs/2502.09977 ; Laban et al. 2024, https://aclanthology.org/2024.emnlp-main.552/.

## Verified findings: compression and hierarchical memory

Jiang et al. (ACL 2024) report prompt-compression results rather than a general guarantee of safe deletion. In their evaluations, LongLLMLingua improved NaturalQuestions performance by up to 21.4% while using roughly four times fewer tokens for GPT-3.5-Turbo, reported 94.0% cost reduction on LooGLE, and reported 1.4–2.6× end-to-end latency acceleration for approximately 10k-token prompts compressed 2–6×. These are method- and benchmark-specific numbers; they do not establish that compression preserves this product’s principal constraints.

Ravaut et al. (ACL 2024) describe uneven position utilization in long inputs and introduce hierarchical and incremental summarization as evaluated alternatives for long-document summarization. Their abstract supports treating position sensitivity as a real evaluation concern, but it does not establish that hierarchy is superior for every task or input type.

Chen et al. (ICLR 2025) report that MELODI, a learned hierarchical memory architecture, outperformed its stated dense-memory baseline across its tested long-context datasets while reducing memory footprint eightfold. That is evidence for the evaluated model architecture, not evidence that an application-layer text summary will have the same result.

Sources: Jiang et al. 2024, https://aclanthology.org/2024.acl-long.91/ ; Ravaut et al. 2024, https://aclanthology.org/2024.acl-long.153/ ; Chen et al. 2025, https://proceedings.iclr.cc/paper_files/paper/2025/hash/a8e3197f627b9c88f86c0d3eb1ade5d7-Abstract-Conference.html.

## Verified findings: trusted and untrusted context

InjecAgent (ACL Findings 2024) evaluates 1,054 indirect-prompt-injection cases spanning 17 user tools and 62 attacker tools. The paper reports that a ReAct-prompted GPT-4 configuration had 23.6% attack success in its base setting and 47.0% in its enhanced setting. The result demonstrates vulnerability in the studied tool-agent configurations; it does not prove that every model or architecture has those rates.

This evidence supports an important boundary for the project: provenance labels and structured regions can make the source and intended handling of text inspectable, but labeling alone cannot be claimed to make untrusted text semantically non-influential to an LLM. Any claim of reduced injection success therefore requires a real-agent benchmark with attack success and benign-task metrics.

Agent Security Bench (ICLR 2025) evaluated attacks and defenses across ten scenarios, more than 400 tools, 27 attack/defense types, and seven metrics. It reports limited effectiveness for the defenses it studied and includes a utility-security balance metric. This supports measuring benign task utility and attack outcomes together, rather than treating a drop in attack success as sufficient evidence.

Sources: Zhan et al. 2024, https://aclanthology.org/2024.findings-acl.624/ ; Zhang et al. 2025, https://proceedings.iclr.cc/paper_files/paper/2025/hash/5750f91d8fb9d5c02bd8ad2c3b44456b-Abstract-Conference.html.

## Verified findings: prompt-prefix caching

Official provider documentation establishes a narrow but useful efficiency fact: repeated **exact prompt prefixes** can be reused, reducing billed or processed input work when cache conditions are met. OpenAI documents exact-prefix matching, a 1,024-token minimum for GPT-5.6 and later, and `cached_tokens`/`cache_write_tokens` telemetry. Anthropic documents automatic or explicit prefix caching, a default five-minute cache lifetime, and block-level cache controls. Gemini documents implicit context caching for supported models and exposes cached-token usage.

This supports a design option: hold stable, verified policy/context material in an exact, immutable prefix and place changing material after it. It does **not** establish that caching improves retrieval quality, instruction following, safety, or provenance. It may also be incompatible with frequent in-prefix compaction because changes before a cache breakpoint prevent reuse.

Sources: OpenAI, https://developers.openai.com/api/docs/guides/prompt-caching ; Anthropic, https://platform.claude.com/docs/en/build-with-claude/prompt-caching ; Google, https://ai.google.dev/gemini-api/docs/caching.
