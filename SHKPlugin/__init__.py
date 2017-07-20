# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SHKPlugin
                                 A QGIS plugin
 Plugin zur Berechnung von Erreichbarkeiten im Saale-Holzland-Kreis

                             -------------------
        begin                : 2017-07-20
        copyright            : (C) 2017 by GGR
        email                : franke@ggr-planung.de
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SHKPlugin class from file SHKPlugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .shk_plugin import SHKPlugin
    return SHKPlugin(iface)
