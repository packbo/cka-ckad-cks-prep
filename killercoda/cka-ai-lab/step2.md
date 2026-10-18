# Practice with scenarios

List the available scenarios:

```bash
./run.sh list
```

Start one (example):

```bash
./run.sh run create-deploy
```

Inside a scenario you type **real kubectl commands** (pipes with `jq`/`grep` work).
Meta-commands:

| Command | Effect | Penalty |
|---|---|---|
| `:hint 1` | Orientation (which command family) | -10% |
| `:hint 2` | Research method (`paths(scalars)`, `explain --recursive`) | -25% |
| `:hint 3` | Doc tip / anti-pitfall | -40% |
| `:check` | Validate cluster state | — |
| `:solution` | Show full solution | 0 points |
| `:skip` | Move on | — |

Run 2-3 scenarios from different domains (workloads, networking, storage…).
Scenario bank: `/root/cka-ckad-cks-prep/cka-sim/scenarios/`.
