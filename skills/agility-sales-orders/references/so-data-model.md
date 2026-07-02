# Sales Order Data Model (behind the screens)

For "where does this number come from?" questions. For actual SQL/report building,
send the user to **Reporting Expert** mode — this file is orientation, not a schema
reference.

## Core tables

| Table | Grain | Holds |
|-------|-------|-------|
| `so_header` | One row per order | Customer, ship-to, order type, status, dates, terms, customer PO |
| `so_detail` | One row per order line | Item, ordered/open quantities, UOM, unit price |
| `shipments_header` | One row per shipment | Ship date, order reference, delivery info |
| `shipments_detail` | One row per shipped line | Shipped quantity and pricing as of shipment |
| `cust` / `cust_shipto` | Customer / ship-to | Account terms, credit; job addresses and tax jurisdiction |
| `item` | One row per item | Item master: descriptions, UOMs, product group |

## How they relate

- An order's lines join to the header on the order's business key (`so_id`) —
  never on `prrowid` (an internal row id, not a stable business key).
- Shipments reference the order they fulfill; one `so_header` can have many
  `shipments_header` rows (partials/backorders).
- Shipped quantity lives in `shipments_detail`; **open** quantity on the order is
  ordered minus shipped/cancelled — which is why a "shipped" report and an "open
  orders" report read different tables.
- Customer and ship-to on the header explain pricing and tax: pricing follows the
  account/ship-to that was on the order when the line was priced.

## Practical mappings

| Question on the screen | Where the data lives |
|------------------------|----------------------|
| "What's still open on this order?" | `so_detail` open quantities |
| "What did we actually ship?" | `shipments_detail` for that order |
| "Why this price?" | `so_detail` unit price, resolved from pricing setup at entry time |
| "Which job was this for?" | `cust_shipto` referenced by the order header |
| "Order history for a customer" | `so_header` filtered by the customer key |

> **Verify:** column-level details belong in the Reporting skill's schema
> references — keep this file at the orientation level and let Reporting Expert
> own the SQL.
