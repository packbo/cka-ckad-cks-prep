# Timed exam + AI tutor

## Full exam (2h, scored)

```bash
./run.sh exam
```

Same rules as the real CKA: real cluster, real commands, no notes.

## AI examiner (opencode)

Install the `opencode` AI agent in this VM:

```bash
curl -fsSL https://opencode.ai/install | bash
opencode auth login   # pick a provider (free tiers: Google AI Studio, GitHub Copilot…)
```

Then, from the repo root (important: `AGENTS.md` there teaches the AI its examiner role):

```bash
cd /root/cka-ckad-cks-prep
opencode
```

Prompts that work well:

- *"Fais-moi passer le scénario X en mode examinateur, indices progressifs seulement"*
- *"Génère un nouveau scénario difficile sur les NetworkPolicies au format cka-sim"*
- *"Analyse mes réponses et liste mes points faibles par domaine"*

The AI follows the hint ladder defined in `AGENTS.md` (level 1 orientation → level 3
near-solution) and verifies your work in the cluster before grading.
