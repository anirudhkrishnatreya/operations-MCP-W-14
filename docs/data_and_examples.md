# Data & Examples

This document outlines the sample data provided in the repository and provides three example questions with their corresponding saved outputs from the Operations Assistant.

## Sample Data

The project comes with mock data to simulate an operations environment.

### 1. Inventory Data (`data/inventory.csv`)
A CSV file containing product inventory records.
- **Example Records:**
  - `1, Headphones X200, HX-200, 45, 89.99, in_stock, 2024-11-01`
  - `3, USB-C Hub, USB-4P, 0, 34.99, out_of_stock, 2024-10-28`

### 2. Document Data (`data/documents/`)
A folder containing standard operating procedures (SOPs), policies, and support tickets in text format.
- **return_policy.txt**: Outlines the 30-day return window and a 15% restocking fee for opened electronics.
- **ticket_001_damaged_item.txt**: A sample support ticket where a customer received a cracked "Headphones X200" casing and received a free return label.

---

## Example Questions & Saved Outputs

Here are three sample questions you can ask the Operations Assistant, along with example outputs it might generate and save.

### Example 1: Policy Query
**Question:** "What is the return policy for opened electronics?"

**Saved Output:**
> **Operations Report: Return Policy for Electronics**
>
> Based on the internal return policy documentation (`return_policy.txt`):
> - **General Window:** Returns are accepted within 30 days with a receipt.
> - **Condition:** Items must be in their original packaging.
> - **Electronics:** A restocking fee of 15% applies specifically to opened electronics.
> - **Defective Items:** If the electronics are damaged or defective upon delivery, the customer must contact support within 48 hours for a free return label.

### Example 2: Inventory & Ticket Correlation
**Question:** "Do we have Headphones X200 in stock, and have there been any recent tickets regarding them?"

**Saved Output:**
> **Operations Report: Headphones X200 Status**
>
> **Inventory Status:**
> - According to the inventory records (`data/inventory.csv`), the **Headphones X200** (SKU: HX-200) are currently **in stock**.
> - There are **45 units** available at a unit price of $89.99.
>
> **Support Tickets:**
> - There is one recent ticket (`ticket_001_damaged_item.txt`) involving this product.
> - Customer John Doe reported receiving the item with a cracked casing. The issue was resolved by issuing a free return label and shipping a replacement unit.

### Example 3: External Web Research
**Question:** "Check the current price of similar headphones on a competitor's site to see if our $89.99 price for the Headphones X200 is competitive."

**Saved Output:**
> **Operations Report: Competitor Pricing Analysis for Headphones X200**
>
> **Internal Data:**
> - Our current price for the **Headphones X200** is **$89.99** (from `inventory.csv`).
>
> **External Research:**
> - Based on data fetched from the external web URL provided:
> - Competitor A lists a similar model (Wireless Headphones Pro) at **$99.99**.
> - Competitor B lists their equivalent model at **$85.00** with free shipping.
>
> **Conclusion:**
> Our price of $89.99 sits comfortably in the middle of the market range. We are competitive, though slightly higher than Competitor B. We may want to highlight our 30-day return policy and quick replacement service (as seen in recent support tickets) to justify the slight premium.
