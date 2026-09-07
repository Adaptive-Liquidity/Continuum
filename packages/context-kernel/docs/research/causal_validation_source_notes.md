# Research Notes: Causal Validation of the Context Kernel

## Confirmed validation gap

The current simulator cannot support an empirical claim about context survival because its simulated driver selects safe or violating actions from the adapter identity rather than from the context delivered to a model. It establishes receipt, replay, interception, and reporting plumbing only. A valid effectiveness claim needs randomized interventions in the context path and an action-generating system whose distribution can change in response to those interventions.

## Source findings

### AgentDojo — dynamic environment rather than static prompt set

- URL: https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html
- AgentDojo describes an extensible environment for evaluating agents that execute tools over untrusted data, rather than a static test suite.
- The publication reports realistic tasks, security test cases, and attack/defense paradigms, while observing that task success can fail even without attacks. This supports measuring **benign utility/task completion** separately from **attack resistance**.
- Relevance: a context-kernel study should use stateful task environments with independent task and security outcomes, not a single synthetic success signal.

### LongBench — varied, standardized long-context evaluation

- URL: https://aclanthology.org/2024.acl-long.172/
- LongBench standardizes 21 datasets across six task categories and evaluates contexts of substantial length. Its abstract reports that retrieval can improve weaker models but does not eliminate long-context difficulty.
- Relevance: the proposed study should cross context lengths, task types, position of critical constraints, and memory/compaction regimes. It should not rely on a single needle-like scenario or one context pressure setting.

### InjecAgent — broad indirect-injection coverage and outcome taxonomy

- URL: https://aclanthology.org/2024.findings-acl.624/
- InjecAgent evaluates tool-integrated agents under indirect prompt injection using 1,054 cases spanning 17 user tools and 62 attacker tools. Its stated attack outcomes distinguish direct harm from private-data exfiltration.
- Relevance: the context-kernel study should stratify outcomes by security property and effect class, not collapse all failures into one binary survival metric. It should also vary injection channel, attacker intent, and tool surface.

### RULER — configurable length and task-complexity sweeps

- URL: https://arxiv.org/abs/2404.06654
- RULER explicitly argues that a vanilla needle-in-a-haystack test is only superficial long-context evaluation. It varies sequence length, number and type of needles, multi-hop tracing, and aggregation; its abstract reports that performance may drop sharply as length and complexity increase.
- Relevance: the context-kernel study should sweep context length, location, distractor density, number of conflicting claims, compaction schedule, multi-step dependency, and retrieval demand. A single deterministic pressure setting is not enough.

### REAL — deterministic simulations can measure real agent behavior when the agent drives state changes

- URL: https://proceedings.neurips.cc/paper_files/paper/2025/hash/c63819755591ea972f8570beffca6b1b-Abstract-Datasets_and_Benchmarks_Track.html
- REAL uses deterministic replicas of real websites for multi-turn tasks that require both information retrieval and state-changing actions. Its abstract emphasizes programmatic checks of website state for action tasks and reproducible testing of black-box agents.
- Relevance: deterministic simulation is not the problem. The simulation can support valid evidence if the **model actually chooses actions from the intervention-controlled observations** and the outcome is measured from environment state. The kernel evaluation should retain a simulator but replace adapter-conditioned policy with a model-driven actor.

### Experimental causal-evaluation methodology — randomization and diverse sources

- URL: https://proceedings.mlr.press/v139/gentzel21a.html
- Gentzel, Pruthi, and Jensen (ICML 2021) discuss using experimental data to evaluate causal methods and highlight both the value of unbiased treatment-effect estimates from randomized trials and the importance of evaluating across diverse sources.
- Relevance: randomly assign the kernel treatment within paired task instances, predeclare the estimand, and report uncertainty. Use multiple task families and model families so a result cannot be attributed to one scenario template or one provider.

### Task Shield — security must be assessed jointly with task utility

- URL: https://aclanthology.org/2025.acl-long.1435/
- Task Shield frames defense around whether actions contribute to user goals and reports both attack-success and task-utility outcomes on AgentDojo.
- Relevance: the proposed validation must predeclare a two-dimensional primary outcome: invariant violation prevention and legitimate-task completion. False blocks, unnecessary approval requests, action overhead, and completion quality are not secondary niceties; they are necessary to establish effectiveness rather than mere refusal.
