
def detect_quality(width):
    if width >= 3840:
        return "4K"
    elif width >= 1920:
        return "1080p"
    elif width >= 1280:
        return "720p"
    return "SD"
