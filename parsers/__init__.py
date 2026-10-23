from parsers.sibupk import SibupkParser

PARSERS = {p.name: p for p in (SibupkParser(),)}