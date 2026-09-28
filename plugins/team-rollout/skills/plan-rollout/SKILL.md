---
name: plan-rollout
description: Sequences the decisions in rolling Claude out to a team or an organisation — identity, access, governance, spend, visibility — and flags the ones that are hard to undo. Use when planning a deployment, onboarding a group, deciding who gets which surface, or when the user asks how to set Claude up for their company.
allowed-tools: Read, Glob, Grep
---

# Rolling out to an organisation

Five decisions, and **the order is the content**. Each one narrows the next, so
taking them out of sequence means redoing the earlier ones.

```
Structure and Identity → Access → Governance → Spend → Visibility
```

## Before the first decision: what success is

Settle the objective before touching a setting, because it is what breaks
ties. It has two halves: one ambition for the whole organisation, concrete
enough to be measured and short enough to repeat, and the constraints that are
genuinely yours.

A useful shape: *every unit using it weekly by the end of the quarter, with no
security escalation from the regulated one.* When an option speeds up adoption
and risks that second clause, the objective has already chosen for you.

## Who decides each one

A decision with no owner is the fastest way to stall a rollout. Look for the
characteristic, not the job title:

| Decision | Decided with | What they need from you |
|---|---|---|
| Structure and Identity | Whoever runs the identity provider | How groups will be cut, and which directory group feeds each one |
| Access | The team leads, plus whoever answers for data risk | Which groups get what, in which phase, and the workflow behind every write permission |
| Governance | Whoever runs enablement, plus security | The possible postures, and the consequence of each |
| Spend | Whoever commits the budget | Proposed limits and the usage that justifies them |
| Visibility | Whoever answers for data risk | The options, a recommendation, and what changing it later costs |

Two of them routinely escalate past the person running the rollout: **spend**,
to whoever owns the budget, and **visibility**, to whoever owns the risk.

## Take these knowing they are costly to reverse

Four choices cost a second migration to undo. Decide them deliberately, with the
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

### Connectors

A connector is where access stops being abstract: it is the single biggest
driver of early adoption and the single biggest change in what a mistake can
reach. **Three gates, all of which must be open** for anyone to use one:

| Gate | Controls | Opened by |
|---|---|---|
| Organisation | Whether it exists here at all | Whoever administers the organisation |
| Role | Whether this group's role includes it | Whoever administers the organisation |
| Member | Whether the person has connected their own account | The person |

Claude acts with **that user's own permissions** in the connected system — it
does not widen access, it inherits it. Which is why the interesting decision
is depth, not existence:

- **Read is where the value starts.** Most groups whose work lives in a system
  need to read it and nothing more, and read-only is a different conversation
  with security than write.
- **Write means changing data as that person.** It gets phased, it gets
  announced, and it gets **signed off by whoever owns the risk** — not by the
  team who wants it. Each tool that writes or deletes has its own setting:
  allowed, needing approval, or blocked.
- Granting is cheap; **withdrawing breaks a workflow someone now depends on**,
  so announce a removal the way you announced the grant.

Where the identity provider supports it, provision connector access centrally
rather than per person, so scope follows the group someone is in.

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

Consumption moves the bill, not headcount, and the agentic surfaces consume
several times what chat does per task. Four levers move it without touching a
single limit:

- **The default model and the effort ceiling** for routine work. This moves
  more than most limit changes.
- **Instructions at the point of use** — short answers unless more is asked
  for, read only the files needed — as guidance rather than enforcement.
- **Reuse**: a skill costs context only once it fires; a shared project keeps the
  context once instead of per person.
- **Scheduled and background work**, which consumes while nobody is watching.
  Bound it and review what is still scheduled.

Repeated overrides are a signal, not an exception: if several people in a
group need one, the group is wrong. And decide the escalation path at the same
time as the limits — what gets approved in the day, and what escalates to
whoever holds the budget.

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

Worked through on a request to enable a scheduled-task surface: it runs
unattended, so it runs under a dedicated identity, never a borrowed person's, a
limit of its own with alerts before that limit rather than at it, no access to
any connector granted with write depth, and a two-week window in one
volunteer group before anyone else sees it. The group under external audit
gets it last, after that audit's own reviewer has read the same four
answers.
