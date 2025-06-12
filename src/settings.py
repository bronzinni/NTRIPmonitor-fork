#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field


# This module is misnamed.
# The actual settings are not dealt with here.
# This module will be renamed later - dataclasses.py would not be silly

@dataclass
class DbSettings:
    host: str = None
    port: int = None
    database: str = None
    user: str = None
    password: str = None
    storeObservations: bool = None

# pre-declare CasterSettings for use in Mountpoint
class CasterSettings:
    pass

@dataclass
class Mountpoint:
    sitename: str
    city: str = None
    countrycode: str = None
    latitude: float = None
    longitude: float = None
    receiver: str = None
    rtcm_version: str = None

    mountpointId: int = None
    caster: CasterSettings = None

@dataclass
class CasterSettings:
    name: str = None
    casterId: int = None
    casterUrl: str = None
    user: str = None
    password: str = None
    # requested_mountpoints: list[str] = field(default_factory=list)
    active: bool = False
    mountpoints: list[Mountpoint] = field(default_factory=list)


    @property
    def sitenames(self) -> list:
        return [site.sitename for site in self.mountpoints]


@dataclass
class MultiprocessingSettings:
    multiprocessingActive: bool = True
    maxReaders: int = None
    readersPerDecoder: int = None
    clearCheck: float = None
    appendCheck: float = None
