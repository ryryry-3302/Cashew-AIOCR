# Bank Statement Transaction Extraction Prompt

Use this prompt with a VLM (like ChatGPT, Claude, etc.) to extract transactions from bank statement images or PDFs.

---

## Task

You are an information extraction system. Your task is to read the attached bank statement and extract **every** financial transaction into a structured JSON format.

---

## Requirements

1. **Extract every transaction** that appears on the statement
2. **Do NOT summarize** the statement
3. **Do NOT omit transactions** - extract all of them
4. **Do NOT combine transactions** - each transaction is separate
5. **Return ONLY valid JSON** - no markdown, no explanations

---

## Output Schema

Return exactly this structure:

```json
{
  "institution": "",
  "account_name": "",
  "statement_period": {
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD"
  },
  "currency": "",
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "",
      "amount": 0.00,
      "currency": "",
      "direction": "debit",
      "balance_after": null,
      "reference": "",
      "notes": ""
    }
  ]
}
```

---

## Field Definitions

### Top-level fields

| Field | Description |
|-------|-------------|
| `institution` | Name of the bank/financial institution |
| `account_name` | Name of the account (e.g., "Savings", "Checking") |
| `statement_period.start` | First date shown on the statement |
| `statement_period.end` | Last date shown on the statement |
| `currency` | Currency code (e.g., "SGD", "USD", "EUR") |
| `transactions` | Array of transaction objects |

### Transaction fields

| Field | Description |
|-------|-------------|
| `date` | Transaction date in ISO format (YYYY-MM-DD) |
| `description` | Full description of the transaction |
| `amount` | **Positive number only** - never negative |
| `currency` | Currency code (usually same as top-level) |
| `direction` | Either `"debit"` or `"credit"` |
| `balance_after` | Balance after transaction, or `null` if not shown |
| `reference` | Reference number or ID, or empty string |
| `notes` | Any additional notes, or empty string |

---

## Amount and Direction Rules

**CRITICAL: Amounts are ALWAYS positive numbers.**

The `direction` field determines whether the transaction is an expense or income:

### Debit (Expense)
```
Example: Grab*Food      -18.20
```
Becomes:
```json
{
  "amount": 18.20,
  "direction": "debit"
}
```

### Credit (Income)
```
Example: Salary 3500.00
```
Becomes:
```json
{
  "amount": 3500.00,
  "direction": "credit"
}
```

**Do NOT store negative numbers.** The Python script will determine the sign.

---

## OCR Rules

1. If OCR is uncertain, preserve the original spelling as closely as possible
2. Do not guess merchant names
3. Keep capitalization as seen
4. Preserve Chinese or other Unicode text
5. If you cannot read something clearly, leave it as an empty string rather than guessing

---

## What to Ignore

Do NOT output:
- Opening balance
- Closing balance
- Totals or summaries
- Interest summaries
- Page numbers
- Headers
- Footers
- Advertisements
- Any non-transaction text

**Only output actual financial transactions.**

---

## Validation Checklist

Before responding, verify:

1. JSON is valid and parseable
2. Every transaction has a `date`
3. Every transaction has an `amount`
4. Every transaction has a `direction`
5. Every transaction has a `description`
6. Dates are in ISO format (YYYY-MM-DD)
7. Amounts are positive numbers
8. Direction is either "debit" or "credit"
9. Output contains no Markdown formatting

---

## Example Output

```json
{
  "institution": "DBS Bank",
  "account_name": "Savings Account",
  "statement_period": {
    "start": "2024-06-01",
    "end": "2024-06-30"
  },
  "currency": "SGD",
  "transactions": [
    {
      "date": "2024-06-15",
      "description": "GRAB FOOD",
      "amount": 18.20,
      "currency": "SGD",
      "direction": "debit",
      "balance_after": 913.42,
      "reference": "",
      "notes": ""
    },
    {
      "date": "2024-06-14",
      "description": "SALARY PAYMENT",
      "amount": 3500.00,
      "currency": "SGD",
      "direction": "credit",
      "balance_after": 931.62,
      "reference": "",
      "notes": ""
    }
  ]
}
```

---

## Important Notes

- Be thorough - missing transactions cannot be recovered
- Be accurate - incorrect amounts or directions will cause issues downstream
- If the statement spans multiple pages, extract transactions from all pages
- If you're unsure about a field, use an empty string rather than making assumptions
- The extracted JSON will be automatically validated and processed
