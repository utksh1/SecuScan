# Plugin Schema Examples

This file contains schema examples for plugin inputs.
#TEXT
{
  "key": "username",
  "type": "text",
  "label": "Username",
  "required": true
}
#Select
{
"key":"theme",
"type":"select",
"label":"theme",
"options":["light","dark"]
"required":"false"
}
#Multiselect
{
"key":"tags",
"type":"multiselect",
"label":"tags",
"options":["bug","feature","docs"]
}
#Checkbox
{
"key":"subscribe",
"type":"checkbox",
"label":"subscribe",
"default":"false"
}
#Number
"key":"age",
"type":"number",
"label":"age",
"min":0,
"max"💯
}
#File path
{
  "key": "file_path",
  "type": "file",
  "label": "Upload File"
}
# Required vs Optional Fields

- **required: true** → Field must be provided
- **required: false** → Field is optional and can be skipped
#Present maps
{
  "preset": {
    "username": "guest",
    "theme": "dark",
    "subscribe": true
  }

}
---

## Notes

- All examples above are simplified for plugin contributors.
- Schema fields must follow valid JSON format.
- Ensure keys in presets match schema keys exactly.
