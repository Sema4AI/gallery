#!/usr/bin/env python3
"""
Test to demonstrate the new insert functionality with prepend and append options.
"""

import json

# Test input for prepend functionality
test_prepend_input = {
    "document_id": "1ABC123DEF456GHI789JKL",  # Replace with actual document ID
    "body": """# This content should appear at the BEGINNING

This content should be prepended to the existing document.

## Prepend Test Section
- This should be at the top
- Before any existing content
- With proper vega-lite support

```vega-lite
{
  "mark": "bar",
  "encoding": {
    "x": {"field": "a", "type": "ordinal"},
    "y": {"field": "b", "type": "quantitative"}
  },
  "data": {
    "values": [
      {"a": "Prepend", "b": 100},
      {"a": "Test", "b": 200},
      {"a": "Data", "b": 150}
    ]
  }
}
```

This chart should be converted to an image and appear at the beginning.""",
    "position": "prepend",
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

# Test input for append functionality
test_append_input = {
    "document_id": "1ABC123DEF456GHI789JKL",  # Replace with actual document ID
    "body": """# This content should appear at the END

This content should be appended to the existing document.

## Append Test Section
- This should be at the bottom
- After all existing content
- With proper vega-lite support

```vega-lite
{
  "mark": "line",
  "encoding": {
    "x": {"field": "year", "type": "temporal"},
    "y": {"field": "value", "type": "quantitative"}
  },
  "data": {
    "values": [
      {"year": "2020", "value": 100},
      {"year": "2021", "value": 120},
      {"year": "2022", "value": 110},
      {"year": "2023", "value": 140}
    ]
  }
}
```

This chart should be converted to an image and appear at the end.""",
    "position": "append",
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

print("🎯 NEW INSERT FUNCTIONALITY TEST")
print("="*60)
print("✅ NEW FEATURES:")
print("  • insert_content_to_document_by_id() - new primary function")
print("  • insert_content_to_document_by_name() - new primary function")
print("  • position parameter: 'prepend' or 'append'")
print("  • append_to_document_by_id() - backward compatibility alias")
print("  • append_to_document_by_name() - backward compatibility alias")
print("  • Vega-lite charts properly converted in all functions")
print("\n" + "="*60)
print("📝 PREPEND TEST:")
print(json.dumps(test_prepend_input, indent=2))
print("\n" + "="*60)
print("📝 APPEND TEST:")
print(json.dumps(test_append_input, indent=2))
print("\n" + "="*60)
print("🚀 READY TO TEST!")
print("1. Create a document with some existing content")
print("2. Test prepend: Run insert_content_to_document_by_id with position='prepend'")
print("3. Test append: Run insert_content_to_document_by_id with position='append'")
print("4. Verify content appears at the correct positions")
print("5. Verify vega-lite charts are converted to images")
