# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SmoothLayer
                                 A QGIS plugin
 Smoothes a raster layer
                             -------------------
        begin                : 2016-03-09
        copyright            : (C) 2016 by GGR
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
    """Load SmoothLayer class from file SmoothLayer.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .smooth_layer import SmoothLayer
    return SmoothLayer(iface)
