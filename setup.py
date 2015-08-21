from setuptools import setup

setup(
    name="sbedecoder",
    version="0.1",
    author="TradeForecaster Global Markets, LLC",
    author_email="github@tradeforecaster.com",
    description=("Simple Bianry Encoding (SBE) decoder (handles CME MDP3 messages)"),
    license="MIT",
    keywords="sbe mdp3",
    url="https://github.com/tfgm/sbedecoder",
    packages=['sbedecoder', ],
    scripts=['scripts/mdp_decoder.py'],
    long_description='see https://github.com/tfgm/sbedecoder/INSTALL.md',
    install_requires=['dpkt', 'lxml', 'nose'],
)
