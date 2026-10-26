from parsers.sibupk import SibupkParser
from parsers.nstu import NstuParser

PARSERS = {p.name: p for p in (SibupkParser(), NstuParser())}