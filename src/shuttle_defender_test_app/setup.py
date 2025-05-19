from setuptools import setup, find_packages

setup(
    name="shuttle_defender_test",
    version="0.1.0",
    packages=find_packages(),
    description="Shuttle Defender Test application for validating Windows Defender",
    author="Mat Davis",
    python_requires='>=3.6',
    # Add dependencies including the shared library
    install_requires=[
        "shuttle_common>=0.1.0",  # Dependency on the shared library
    ],
    # Entry points for command-line scripts
    entry_points={
        'console_scripts': [
            'run-defender-test=shuttle_defender_test.shuttle_defender_test:main',
        ],
    },
    # Add classifiers for better package metadata
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
