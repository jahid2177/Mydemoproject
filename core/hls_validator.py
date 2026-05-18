import subprocess

def validate_hls(url):

    cmd = [
        "ffprobe",
        "-v",
        "error",
        url
    ]

    result = subprocess.run(cmd)

    return result.returncode == 0
