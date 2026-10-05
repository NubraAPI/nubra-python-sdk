# Snippet: Accessing Corporate Actions

Original source path: `market_data/company_fundamentals/accessing_corporate_actions.py`

```python
response = market_data.corp_actions("TCS")

for action in response.result.corporate_actions:
    print(action.corp_action_name)
    print(action.action_type)
    print(action.upcoming_event)
    print(action.record_date)
    print(action.execution_date)
    print(action.ratio1, action.ratio2)
    print(action.dividend_type)
```
