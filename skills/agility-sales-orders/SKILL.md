# Agility Sales Orders — Skill Overview

This skill powers the **Sales Order Expert** mode in Beisser AI. It covers working
with sales orders in DMSI Agility at Beisser Lumber: entering and editing orders,
understanding order statuses and holds, and how orders flow into shipments and
invoices.

> **Status: draft knowledge pack.** The structure and lifecycle content below is a
> verified starting point at the concept level. Exact screen names, menu paths, and
> keystrokes vary by Agility version and configuration — sections that need
> confirmation against Beisser's live system are marked with `> **Verify:**` notes.
> Expand this pack by replacing those notes with confirmed procedures.

## Scope

Use this skill for questions like:

- "How does a quote become an order?"
- "What do the order statuses mean?"
- "Why can't this order ship?" (holds, credit, inventory)
- "How do orders relate to shipments and invoices?"
- "What's on the order header vs. the order lines?"

Out of scope (route the user elsewhere):

- **SQL and report building** → Reporting Expert mode (AgilitySQL schema specialist).
- **Purchasing, receiving, GL/AR/AP setup** → General Chat (main Agility docs corpus).

## Core terminology

| Term | Meaning |
|------|---------|
| **Sales order (SO)** | The customer's order: one header (customer, ship-to, terms, dates) plus one or more lines (item, quantity, price). |
| **Quote** | A priced, non-committing version of an order. Converts to a live order without re-keying. |
| **Ship-to** | The delivery address/site for the order. A customer account can have many ship-tos; jobs are typically represented as ship-tos. |
| **Hold** | A flag that blocks an order from progressing (commonly credit hold or a review/margin hold) until released by someone with permission. |
| **Direct shipment** | Material shipped from the vendor straight to the customer; the SO line is tied to a purchase order rather than on-hand inventory. |
| **Open quantity** | Ordered quantity not yet shipped. An order with open quantity after a shipment is a backorder/partial. |

## Answering guidance

- Ground every answer in this pack's reference files; if a detail isn't covered,
  say so and suggest where to look (Agility docs corpus, DMSI support, or a
  Beisser admin).
- Distinguish three kinds of statements clearly:
  1. **Agility behavior** — how the software works.
  2. **Beisser policy** — how we've decided to use it (marked as policy in the sources).
  3. **Unverified detail** — anything carrying a `> **Verify:**` note.
- For "why is this order stuck?" questions, walk the checklist in
  `references/order-lifecycle.md` (status → holds → inventory → shipping) in order.

## Reference files

| File | Contents |
|------|----------|
| `references/order-lifecycle.md` | Quote → order → pick → ship → invoice flow, statuses, holds, troubleshooting checklist |
| `references/order-entry.md` | Header vs. lines, pricing inputs, editing rules, common gotchas |
| `references/so-data-model.md` | The SO tables behind the screens (`so_header`, `so_detail`, shipments) — for "where does this number come from?" questions |
