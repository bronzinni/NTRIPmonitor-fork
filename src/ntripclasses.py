#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field, asdict

# pre-declare Caster for use in Mountpoint
class Caster:
    pass

@dataclass
class Mountpoint:
    mountpoint: str
    identifier: str = None
    format: str = None
    format_details: str = None
    carrier: int = None
    nav_system: str = None
    network: str = None
    country: str = None
    latitude: float = None
    longitude: float = None
    nmea: int = None
    solution: int = None
    generator: str = None
    compr_encryp: str = None
    authentication: str = None
    fee: str = None
    bitrate: int = None
    misc: str = None

    mountpoint_id: int = None
    caster_id: int = None
    caster: str = None

    def as_dict(self):
        return asdict(self)

@dataclass
class Caster:
    name: str = None
    casterId: int = None
    casterUrl: str = None
    user: str = None
    password: str = field(default=None, repr = False)
    active: bool = False
    mountpoints: list[Mountpoint] = field(default_factory=list)


    @property
    def sitenames(self) -> list:
        return [site.mountpoint for site in self.mountpoints]

