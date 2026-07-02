# Order Entry and Editing

## Header vs. lines

An order is one **header** plus one or more **lines**. Getting the header right
first matters because line pricing and taxing key off it.

**Header carries:**
- Customer account and **ship-to** (job) — drives pricing level, tax jurisdiction,
  and delivery address.
- Order type (quote vs. order; delivered vs. pickup).
- Dates: order date, requested/promise date.
- Terms and salesperson.
- PO number / job reference from the customer.

**Lines carry:**
- Item, quantity, and unit of measure.
- Unit price and any line-level discount.
- Fulfillment source: on-hand inventory vs. direct shipment (tied to a PO).
- Line status (open / picked / shipped / cancelled quantities).

## Entering a clean order

1. Pick the **customer**, then the correct **ship-to/job** — before touching lines.
   Changing the ship-to after lines exist can change pricing and tax, so fix it
   early.
2. Set the **order type** and dates.
3. Add lines: item, quantity, UOM. Watch the UOM — lumber items commonly sell in
   multiple UOMs (each / MBF / lineal), and a wrong UOM is the classic source of a
   10x pricing surprise.
4. Review the price each line resolved to (see "Where prices come from" below)
   before committing.
5. Confirm totals, expected margin, and delivery info, then save/commit.

> **Verify:** the literal screen/menu path for order entry at Beisser and any
> required custom fields — replace this note with the confirmed procedure.

## Where prices come from

When a line is entered, Agility resolves a price from the pricing setup, in
priority order — customer-specific contract/job pricing beats price-level pricing,
which beats the item's default/list price. Manual overrides beat everything but are
visible to margin review.

Practical implications:

- If a price "looks wrong," check **which source it resolved from** before
  overriding it — the fix may belong in the customer's contract pricing, not on
  this one order.
- Overrides on a quote carry into the converted order.

**Beisser policy:** price overrides below cost/margin thresholds are expected to be
flagged for review rather than silently shipped.

> **Verify:** Beisser's active price levels, contract pricing usage, and the margin
> threshold that triggers review.

## Editing an existing order

What you can safely change depends on how far the order has progressed:

- **Quote / untouched open order** — everything is editable.
- **After picking has started** — quantity reductions below the picked quantity and
  item swaps on picked lines require un-picking first; add new lines instead where
  possible.
- **After a shipment exists** — shipped quantities and their pricing are locked
  into the shipment/invoice; only the open remainder is editable.
- **Ship-to changes late in the game** — re-check tax and pricing; they were
  resolved from the original ship-to.

## Common gotchas

- **Wrong UOM on a line** — the most common cause of absurd extended prices.
- **Duplicate orders** — a customer PO number already on another open order is a
  red flag; search by customer PO before entering.
- **Quote never converted** — the customer thinks they ordered; we have only a
  quote. Nothing ships from a quote.
- **Editing the wrong document** — confirm you're on the order, not an old quote or
  a copied order, before making changes.
