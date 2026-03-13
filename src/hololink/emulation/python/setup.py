import re

from setuptools import setup


def get_version():
    with open("../../../../VERSION", "r") as f:
        version = re.match(r"[0-9\.]+", f.read().strip()).group(0)
    return version


setup(
    name="hololink",
    version=get_version(),
    description="Holoscan Sensor Bridge Emulation",
    url="https://github.com/nvidia-holoscan/holoscan-sensor-bridge",
    packages=["hololink", "hololink.emulation", "hololink.emulation.sensors"],
    package_dir={"hololink": "hololink"},
    package_data={
        "hololink.emulation": ["*.so"],
        "hololink.emulation.sensors": ["*.so"],
    },
    include_package_data=True,
)
