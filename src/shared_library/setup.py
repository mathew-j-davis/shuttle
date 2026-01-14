from setuptools import setup, find_packages

setup(
    name="shuttle_common",
    version="0.2.0",
    packages=find_packages(),
    description="Common utilities for shuttle and defender_test applications",
    author="Mat Davis",
    python_requires='>=3.6',
    # Add any package dependencies here
    install_requires=[
        # e.g., "requests>=2.25.0",
    ],
    # Add classifiers for better package metadata
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
