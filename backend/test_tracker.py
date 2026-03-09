import sys
from app.context.tracker import variable_tracker

source = """
# Enterprise Runtime Demo example
x = 10
y = input_data + x
z = df['column_name']
print(z)
"""

res = variable_tracker.analyze_cell("test_cell", "python", source)
print(f"Defined: {res.defined}")
print(f"Referenced: {res.referenced}")
