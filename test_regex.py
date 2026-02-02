import re

# Test case from user's example
text = '''Claro, crearé el evento. El evento se llamará "prueba ia 3" y tendrá lugar el 2 de febrero del 2026 a las 16 hrs.

{
  "action": "create_event",
  "params": {
    "summary": "prueba ia 3",
    "start_time": "2026-02-02T16:00:00",
    "end_time": "2026-02-02T17:00:00",
    "description": ""
  }
}'''

print("Original text:")
print(text)
print("\n" + "="*50 + "\n")

# Test regex patterns
regex_strategies = [
    r'```json\s*([\[\{].*?[\]\}])\s*```',  # Code block
    r'([\[\{][\s\n]*"action".*?[\]\}])\s*$'  # Raw JSON at end
]

display_text = text
for reg in regex_strategies:
    display_text = re.sub(reg, '', display_text, flags=re.DOTALL)

# Clean up extra whitespace
display_text = re.sub(r'\n{3,}', '\n\n', display_text.strip())

print("Cleaned text:")
print(display_text)
print("\n" + "="*50 + "\n")

# Check if JSON was removed
if "{" not in display_text:
    print("✅ SUCCESS: JSON was removed")
else:
    print("❌ FAILED: JSON is still present")
