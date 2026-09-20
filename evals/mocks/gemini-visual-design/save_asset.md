---
expect:
  temp_path: string
  destination_dir: string
  filename: string
---
{
  "saved_path": "{{input.destination_dir}}/{{input.filename}}",
  "success": true
}
