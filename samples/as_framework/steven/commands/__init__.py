# Copyright (c) 2017 Laszlo Attila Toth
# Distributed under the terms of the GNU General Public License v3

import collections

from dewi.core.context import Context
from dewi.loader.plugin import Plugin
from steven.commands.xssh import XSshCommand


class CommandsPlugin(Plugin):
    def get_description(self) -> str:
        return "Steve: A set of tools for Support"

    def get_dependencies(self) -> collections.Iterable:
        return {'dewi.core.CorePlugin'}

    def load(self, c: Context):
        self._r(c, XSshCommand)

    def _r(self, c: Context, t: type):
        c['commands'].register_class(t)
