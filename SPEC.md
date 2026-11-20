# SPEC — Contract Field Extractor

## What it does

Takes a plain-text contract and extracts key billing fields into structured JSON:
- SKU / product name
- Payment schedule (monthly, quarterly, annual)
- Pricing model (flat, usage-based, tiered)
- Billing metrics (seats, API calls, storage)
- Contract term (start date, end date, renewal)

Outputs a JSON object ready for a billing system.

## What it does NOT do

- Does not parse PDFs (input is plain text only)
- Does not validate legal terms
- Does not store contract data
- Does not use an LLM

## Input

```json
{
  "text": "This Agreement is between Acme Corp and Beta Inc. Product: Pro Plan. Payment: Monthly. Price: $29/month. Term: 12 months starting 2026-01-01. Renewal: automatic."
}
```

## Output

```json
{
  "product": "Pro Plan",
  "payment_schedule": "monthly",
  "price": 29,
  "currency": "usd",
  "term_months": 12,
  "start_date": "2026-01-01",
  "renewal": "automatic"
}
```

## Exit codes

- `0` — success, fields extracted
- `1` — invalid input (missing `text` field, non-string)
- `2` — no fields found (unrecognized contract format)

## Rules (deterministic, no ML)

### Product extraction
- Look for `Product: <name>` or `Plan: <name>` or `Service: <name>`
- Capture the text after the colon until end of line
- If not found, `product: null`

### Payment schedule
- `Monthly` or `monthly` → `monthly`
- `Quarterly` or `quarterly` → `quarterly`
- `Annual` or `annually` or `yearly` → `annual`
- If not found, `payment_schedule: null`

### Price extraction
- Look for `$<number>` or `<number> USD` or `<number> EUR`
- Capture the number as a float
- If not found, `price: null`

### Currency
- `$` or `USD` → `usd`
- `€` or `EUR` → `eur`
- If not found, `currency: null`

### Term extraction
- Look for `<number> months` or `<number> year`
- Convert years to months (×12)
- If not found, `term_months: null`

### Start date
- Look for `starting <date>` or `effective <date>` or `beginning <date>`
- Date format: YYYY-MM-DD
- If not found, `start_date: null`

### Renewal
- `automatic` or `auto-renew` → `automatic`
- `manual` or `non-renewing` → `manual`
- If not found, `renewal: null`

## Constraints

- No external API calls
- No file I/O beyond reading stdin and writing stdout
- No secrets in output
- Deterministic: same input → same output
