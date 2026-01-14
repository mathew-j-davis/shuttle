from setuptools import setup, find_packages

setup(
    name="mdatp-simulator",
    version="0.2.0",
    description="Simulator for Microsoft Defender for Endpoint (MDATP) for testing",
    author="Shuttle Team",
    packages=["mdatp_simulator"],
    entry_points={
        "console_scripts": [
            "mdatp-simulator=mdatp_simulator.simulator:main",
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
