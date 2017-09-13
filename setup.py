from setuptools import setup

setup(
    name="sbedecoder",
    version="0.1.2",
    author="TradeForecaster Global Markets, LLC",
    author_email="github@tradeforecaster.com",
    description=("Simple Bianry Encoding (SBE) decoder (handles CME MDP3 messages)"),
    license="MIT",
    keywords="sbe mdp3 orderbook",
    url="https://github.com/tfgm/sbedecoder",
    packages=['sbedecoder', 'orderbook'],
    scripts=['scripts/mdp_decoder.py', 'scripts/mdp_book_builder.py'],
    long_description='see https://github.com/tfgm/sbedecoder/INSTALL.md',
    install_requires=['dpkt', 'lxml', 'nose', 'mako', 'autopep8'],
)
