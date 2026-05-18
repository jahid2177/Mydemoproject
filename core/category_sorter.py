def sort_category(streams):

    categories = {}

    for stream in streams:

        group = stream.get("group", "Other")

        if group not in categories:
            categories[group] = []

        categories[group].append(stream)

    return categories
