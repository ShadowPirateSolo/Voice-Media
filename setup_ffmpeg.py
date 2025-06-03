import os
import platform
import urllib.request
import zipfile
import tarfile
import shutil
import stat


def setup_ffmpeg():
    system = platform.system()
    os.makedirs("bin", exist_ok=True)

    if system == "Windows":
        target_path = os.path.join("bin", "ffmpeg.exe")
        os.environ["FFMPEG_BINARY"] = target_path

        if os.path.isfile(target_path):
            return

        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        archive = "ffmpeg.zip"
        temp_dir = "bin_temp"

        try:
            urllib.request.urlretrieve(url, archive)
            with zipfile.ZipFile(archive, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            for root, _, files in os.walk(temp_dir):
                if "ffmpeg.exe" in files:
                    shutil.move(os.path.join(root, "ffmpeg.exe"), target_path)
                    break

        finally:
            if os.path.exists(archive):
                os.remove(archive)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    elif system == "Linux":
        target_path = os.path.join("bin", "ffmpeg")
        os.environ["FFMPEG_BINARY"] = target_path

        if os.path.isfile(target_path):
            return

        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        archive = "ffmpeg.tar.xz"
        temp_dir = "bin_temp"

        try:
            urllib.request.urlretrieve(url, archive)

            with tarfile.open(archive, "r:xz") as tar:
                tar.extractall(temp_dir)

            for root, _, files in os.walk(temp_dir):
                if "ffmpeg" in files:
                    shutil.move(os.path.join(root, "ffmpeg"), target_path)
                    break

            os.chmod(target_path, os.stat(target_path).st_mode | stat.S_IEXEC)

        finally:
            if os.path.exists(archive):
                os.remove(archive)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
