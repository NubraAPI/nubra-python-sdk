# Snippet: Accessing Shareholding Pattern

Original source path: `market_data/company_fundamentals/accessing_shareholding_pattern.py`

```python
pattern = market_data.shareholding_pattern(fincode, limit=4).result.shareholding_pattern

print(pattern.dates)

# Values are percentages, not absolute share counts.
for row in pattern.data:
    print(row.label)
    for entry in row.values:
        print(entry.date, entry.value)
        for child in entry.shareholding_children or []:
            print("  ", child.label, child.value)
```
