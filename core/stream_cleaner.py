def clean_dead(streams):

    working = []

    for stream in streams:

        if stream.get("alive"):

            working.append(stream)

    return working
