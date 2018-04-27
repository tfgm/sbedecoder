from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md')) as f:
    long_description = f.read()

setup(
    name="sbedecoder",
    version="0.1.5",
    author="TradeForecaster Global Markets, LLC",
    author_email="github@tradeforecaster.com",
    description="Simple Binary Encoding (SBE) decoder (handles CME MDP3 messages)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="sbe mdp3 orderbook message decoder",
    url="https://github.com/tfgm/sbedecoder",
    packages=['sbedecoder', 'mdp', 'mdp.orderbook'],
    scripts=['scripts/mdp_decoder.py', 'scripts/mdp_book_builder.py'],
    install_requires=['dpkt', 'lxml'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ]
)
