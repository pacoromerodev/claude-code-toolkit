---
name: plan-rollout
description: Sequences the decisions in rolling Claude out to a team or an organisation — identity, access, governance, spend, visibility — and flags the ones that are hard to undo. Use when planning a deployment, onboarding a group, deciding who gets which surface, or when the user asks how to set Claude up for their company.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Rolling out to an organisation

Five decisions, and **the order is the content**. Each one narrows the next, so
taking them out of sequence means redoing the earlier ones.

```
Structure and Identity → Access → Governance → Spend → Visibility
```

## Take these knowing they are hard to undo

Four choices are expensive to reverse. Decide them deliberately, with the
person who owns the consequence in the room:

| Decision | Why it is hard to undo |
|---|---|
| **Claiming the domain** | Irreversible. Existing accounts get a migration window, and not everything transfers with them |
| **One organisation or several** | Splitting later means moving people, content and billing |
| **Mapping identity groups to roles** | Everything downstream hangs off it; changing it re-permissions everyone at once |
| **Retention** | Sets what can be produced later. It cannot be applied retroactively |

Everything else can be adjusted once people are using it.

## 1. Structure and identity

**One organisation unless** there are genuinely separate contracts, separate
identity providers, or data that must not mix. Two organisations means two of
everything, forever.

Before anything else: at least two owners who are actual people, single sign-on
enforced, user provisioning decided, domain claimed. A naming convention and a
billing owner can be settled in parallel.

**Just-in-time provisioning** creates the account at first login — less to
maintain, and no way to pre-assign groups. **Directory-driven provisioning**
puts joiners and leavers where they belong automatically, and is what an
organisation of any size ends up needing.

## 2. Access

Group membership is **additive**. Someone in two groups gets the union of what
both grant — a narrow group never takes away what a broad one gave.

The consequence is the rule most rollouts learn late: **anything regulated
needs its own group, not a narrower version of a general one.** If a general
group grants a connector, no narrow group can un-grant it.

Three ways to shape groups:

- **By reporting line** — easy to explain, rarely matches how risk is
  distributed
- **By risk profile** — matches the controls, confuses people who cannot see
  why they are in it
- **Hybrid** — reporting line for the default, risk groups layered on top.
  Usually right.

Surfaces have two gates: the organisation switch, and the per-role grant.
Turning something on for the organisation does not give it to anyone until a
role grants it.

## 3. Governance

Anything people create — skills, plugins, projects, organisation instructions —
spreads. Four controls decide how far, and their defaults are deliberate:

| Control | Default | What it means |
|---|---|---|
| Who can create and provision | Owners | Keep it there until the review path exists |
| Sharing a skill | On | People can hand work to each other |
| Sharing with groups | Off | A wider blast radius, opened on purpose |
| Sharing with the whole organisation | Off | **No in-product review step** — whatever is shared is simply shared |

That last row is the one to plan around. If organisation-wide sharing is
opened, the review happens in your process or it does not happen.

Three postures, all defensible:

- **Open building, reviewed distribution** — anyone builds, a named group
  approves anything that spreads. The usual answer.
- **Centralised** — a platform team builds, everyone consumes. Slower,
  predictable.
- **Fully open** — fastest, and only honest where nothing sensitive is in play.

For Claude Code specifically, the platform owner ships managed settings. Start
from `settings/managed-settings.json` in this plugin.

## 4. Spend

Owned by whoever owns the budget, not by the platform team.

- An organisation ceiling, plus per-group limits expressed per member
- Decide the **multi-group rule** before anyone is in two groups: when limits
  differ, does the higher or the lower apply? Both are defensible; discovering
  it at the limit is not
- At the limit, usage **pauses**. Nothing queues, nothing degrades. People
  stop, and they will ask why
- Tier by usage — light, standard, heavy — rather than by seniority

**Before raising a limit, check the default model and the effort setting for
that group.** A group running an expensive model on routine work will look like
a capacity problem and is a configuration one. That is the most common false
alarm in the whole rollout.

## 5. Visibility

Decide what you need to be able to answer later, then pick the mechanism:

| Need | Mechanism |
|---|---|
| What was said and produced | The compliance interface — conversation content, integrable with data-loss and discovery tooling |
| Who did what, and when | Audit logs — **metadata only**, never content |
| How much is being used, by whom | Analytics |
| Operational telemetry | OpenTelemetry — note that some surfaces include prompt text by default |
| Allow or deny before a response | Inference-time hooks |

Two things that surprise people: audit logs have no content in them, and
retention has a **minimum**. There is no zero-retention option, and some
categories are held considerably longer.

Enable the compliance interface before you need it. It is not retroactive.

## Judging whether it is working

Adoption is two numbers per group, not one: **breadth** — how many people use
it at all — and **depth** — how much those people use it. Low breadth with high
depth is an enablement problem. High breadth with low depth means it has not
reached real work yet.

## When a new capability appears

Three questions, in order:

1. **Who receives it by default?** Everyone, or nobody until granted?
2. **What does it bring with it?** New data paths, new surfaces, new spend?
3. **Does it move the risk position?** If yes, it goes to a pilot group first,
   with the identity, alerting and limits worked out there.

A worked example: a new chat-surface integration gets its own identity per
channel, alerts at 75% and 95% of its limit, is blocked in channels containing
external guests, and stays off for the group handling payment data until that
group's own review is done.
