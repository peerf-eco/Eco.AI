from setuptools import find_packages, setup


setup(
    name="eco-ai-data",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["datasets", "openai", "python-dotenv"],
    entry_points={
        "console_scripts": [
            "eco-ai-data=eco_ai_data.cli.main_cli:main",
            "eco-ai-data-doc=eco_ai_data.cli.doc_main_cli:main",
        ]
    },
)
