# Sales Order Lifecycle

## The flow at a glance

```
Quote  →  Open order  →  Picked/Staged  →  Shipped  →  Invoiced  →  Closed
             │
             └─ (blocked by holds: credit / review)
```

1. **Quote** — priced but not committed. No inventory demand, no credit exposure.
   Converts to a live order when the customer commits; the conversion carries the
   lines and pricing forward so nothing is re-keyed.
2. **Open order** — the order is live. Lines create demand against inventory and
   the order counts toward the customer's credit exposure.
3. **Picked / staged** — warehouse pulls material for the order. Partial picks are
   normal; the unpicked remainder stays open.
4. **Shipped** — a shipment is recorded against the order. One order can produce
   multiple shipments (partials/backorders), and delivered orders get proof of
   delivery via the Agility mobile POD app.
5. **Invoiced** — shipped quantities are billed. Invoicing follows shipment, so a
   partially shipped order can be partially invoiced.
6. **Closed** — all lines fully shipped and invoiced (or cancelled).

> **Verify:** the exact status labels shown in Beisser's order screens (and any
> custom statuses configured by DMSI) — replace this note with the literal status
> list from the live system.

## Holds

Holds stop an order from progressing until someone with permission releases them.

- **Credit hold** — the customer is over their limit or past due. The order can
  usually still be entered and edited, but it cannot ship until credit releases it.
- **Review / margin hold** — the order needs a second look before it ships (for
  example, pricing below margin thresholds).

**Beisser policy:** releasing a credit hold is a credit/office decision, not a
sales-counter decision. If an order is credit-held, contact the office rather than
working around it.

> **Verify:** which hold types are active at Beisser, who has release permission,
> and where the release is performed in the UI.

## "Why is this order stuck?" checklist

Walk these in order:

1. **Is it still a quote?** Quotes don't ship — convert it first.
2. **Any holds on the order?** Check for credit or review holds; a held order will
   not release to shipping regardless of inventory.
3. **Is there inventory to fulfill it?** Lines without available quantity wait for
   receipts or a purchase order. Direct-ship lines wait on the tied PO, not on-hand
   stock.
4. **Has it released to shipping/dispatch?** An order can be clean but simply not
   yet picked, staged, or scheduled on a delivery.
5. **Already shipped but not invoiced?** Then it's a billing question, not an order
   question — check the invoicing run.

## Partial shipments and backorders

- Shipping less than the ordered quantity leaves the remainder **open** on the
  order; the order stays open until every line is fully shipped or cancelled.
- Each shipment gets its own shipment record (and invoice, once billed), so a
  single order number can legitimately appear on several invoices.
- When cancelling a remainder instead of backordering it, cancel at the line level
  so the rest of the order is unaffected.

## Cancelling orders

- Quotes can be deleted/expired freely — nothing downstream depends on them.
- Open orders should be **cancelled**, not deleted, once anything has happened
  against them (picks, shipments, invoices), so the audit trail stays intact.
- Fully or partially shipped lines cannot simply be cancelled — the shipped portion
  is history; only the open remainder can be cancelled.

> **Verify:** Beisser's rules for who may cancel orders and whether restock fees
> apply to returns of already-shipped material.
