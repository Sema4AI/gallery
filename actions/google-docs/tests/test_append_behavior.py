#!/usr/bin/env python3
"""
Test to understand the current append behavior and determine if it's truly appending or prepending.
"""

import json

# Test input to check append behavior
test_input = {
    "document_id": "1ABC123DEF456GHI789JKL",  # Replace with actual document ID
    "body": """# This is appended content

This content should appear at the END of the existing document.

## Test Section
- Item 1
- Item 2
- Item 3

**Bold text** and *italic text* should work.

```vega-lite
{
  "mark": "bar",
  "encoding": {
    "x": {"field": "a", "type": "ordinal"},
    "y": {"field": "b", "type": "quantitative"}
  },
  "data": {
    "values": [
      {"a": "A", "b": 28},
      {"a": "B", "b": 55},
      {"a": "C", "b": 43}
    ]
  }
}
```

This chart should be converted to an image.""",
    "vscode:request:oauth2": {
        "oauth_access_token": {
            "type": "OAuth2Secret",
            "provider": "google",
            "scopes": [
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/documents"
            ],
            "access_token": "<access-token-will-be-requested-by-vscode>"
        }
    }
}

print("🔍 APPEND BEHAVIOR TEST")
print("="*50)
print("Current implementation analysis:")
print("• Uses start_index = raw_document.end_index - 1")
print("• Uses is_append = True")
print("• This should insert at the END of the document")
print("\nIf content appears at the BEGINNING, then it's prepending.")
print("If content appears at the END, then it's truly appending.")
print("\n" + "="*50)
print(json.dumps(test_input, indent=2))
print("\n🚀 READY TO TEST!")
print("1. Create a document with some existing content")
print("2. Run append_to_document_by_id with this test input")
print("3. Check if the new content appears at the beginning or end")
