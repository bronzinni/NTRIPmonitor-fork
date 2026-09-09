#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass


@dataclass
class DbSettings:
    host: str = None
    port: int = None
    database: str = None
    user: str = None
    password: str = None
    storeObservations: bool = None

@dataclass
class MultiprocessingSettings:
    multiprocessingActive: bool = True
    maxReaders: int = None
    readersPerDecoder: int = None
    clearCheck: float = None
    appendCheck: float = None

