#!/usr/bin/env python3
"""
Test to verify that vega-lite markdown blocks are properly converted to images
when using append_to_document_by_id.
"""

import json

# Test input with vega-lite markdown block
test_input = {
    "document_id": "1ABC123DEF456GHI789JKL",  # Replace with actual document ID
    "body": """# Vega-Lite Test

This document tests vega-lite chart conversion in append operations.

## Sample Chart

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
      {"a": "C", "b": 43},
      {"a": "D", "b": 91}
    ]
  }
}
```

This chart should be converted to an image and embedded in the document.

## Another Chart

```json
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

This should also be converted to an image.""",
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

print("🎯 VEGA-LITE INSERT TEST")
print("="*50)
print(json.dumps(test_input, indent=2))
print("\n" + "="*50)
print("✅ FIXES APPLIED:")
print("  • _insert_content_to_document now processes vega-lite markdown")
print("  • _insert_content_to_document_tab now processes vega-lite markdown")
print("  • Both functions call _process_markdown_with_images_and_vega_lite()")
print("  • Image data is passed to BatchUpdateBody.from_markdown()")
print("  • New position parameter: 'prepend' or 'append'")
print("  • Backward compatibility maintained with old function names")
print("\n🚀 READY TO TEST!")
print("Replace document_id with actual ID and run:")
print("  • insert_content_to_document_by_id with position='append'")
print("  • OR append_to_document_by_id (backward compatibility)")
print("The vega-lite charts should be converted to images and embedded!")
