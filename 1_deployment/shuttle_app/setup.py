from setuptools import setup, find_packages

setup(
    name="shuttle",
    version="0.1.0",
    packages=find_packages(),
    description="Shuttle file transfer and scanning utility with disk space throttling",
    author="Mat Davis",
    python_requires='>=3.6',
    # Add dependencies including the shared library
    install_requires=[
        "shuttle_common>=0.1.0",  # Dependency on the shared library
        "PyYAML>=6.0",            # For configuration handling
    ],
    # Entry points for command-line scripts
    entry_points={
        'console_scripts': [
            'run-shuttle=shuttle.shuttle:main',
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
