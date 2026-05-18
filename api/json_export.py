
import json

def export_json(data, output='data/output/streams.json'):
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
