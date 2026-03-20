# Snippet: Accessing Response Fields

Original source path: `market_data/market_quotes/accessing_response_fields.py`

```python
order_book = quote.orderBook

print(f"Reference ID: {order_book.ref_id}")
print(f"Timestamp: {order_book.timestamp}")
print(f"Last Traded Price: {order_book.last_traded_price}")
print(f"Last Traded Quantity: {order_book.last_traded_quantity}")
print(f"Volume: {order_book.volume}")
print(f"Bid Levels: {len(order_book.bid)}")
print(f"Ask Levels: {len(order_book.ask)}")

for bid in order_book.bid:
    print(f"Bid price={bid.price} quantity={bid.quantity} orders={bid.num_orders}")

for ask in order_book.ask:
    print(f"Ask price={ask.price} quantity={ask.quantity} orders={ask.num_orders}")
```
