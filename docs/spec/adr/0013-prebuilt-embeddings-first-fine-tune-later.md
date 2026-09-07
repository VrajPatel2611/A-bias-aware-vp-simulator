# ADR-0013 · Prebuilt embeddings first; fine-tune later

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-22 |
| **Deciders** | Vraj Patel, Yogesh Bagotia |
| **Supersedes** | — |

## Context

Keyword matching caused every detector error observed in validation. Semantic matching would fix it. Training an embedding model from scratch is not viable; fine-tuning requires labelled pairs we do not yet have.

## Decision

Ship with a prebuilt sentence-transformer in a hybrid keyword-plus-embedding matcher. Collect labelled pairs through an admin review queue. Fine-tune once ~2 000 pairs exist, and only ship the fine-tuned model if it beats the baseline on a held-out set.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Train from scratch | Millions of pairs, multi-GPU weeks — not viable for this team, and unnecessary. |
| Fine-tune immediately | Would overfit on a few hundred hand-made pairs and perform worse than the baseline. |
| API embeddings | Adds latency, cost, and an external dependency to every question. |

## Consequences

+ Ships now at zero cost, on CPU, with data never leaving the server
+ Creates the labelled corpus as a by-product of normal operation
+ Fine-tuning later is a contained, measurable change
− Encoder version becomes part of `engine_version`; changing it requires replay
