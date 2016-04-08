def sum_layer(iface):
    from osgeo import gdal

    l = iface.activeLayer()
    p = l.dataProvider()
    u = p.dataSourceUri()

    ds = gdal.Open(u)
    arr = ds.ReadAsArray()
    print arr.sum().astype(int)
    return arr
