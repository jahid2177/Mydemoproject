def sort_category(streams):
    categories = {}
    for stream in streams:
        group = (stream.get('group') or 'Other').strip() or 'Other'
        categories.setdefault(group, []).append(stream)
    return {group: sorted(items, key=lambda x: x.get('name', '').lower()) for group, items in sorted(categories.items())}
