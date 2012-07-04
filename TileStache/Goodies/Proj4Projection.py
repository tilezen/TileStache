import TileStache
from pyproj import Proj
from ModestMaps.Core import Point, Coordinate
from ModestMaps.Geo import Location, LinearProjection, Transformation

_grid_threshold = 1e-3

class Proj4Projection(LinearProjection):
    """ Projection that supports any projection that can be expressed in Proj.4 format.
    
        Required attributes:
          
          srs:
            The Proj.4 definition of the projection to use, as a string
          
          resolutions:
            An array of the zoom levels' resolutions, expressed as the number
            of projected units per pixel on each zoom level. The array is ordered
            with outermost zoom level first (0 is most zoomed out).
            
        Optional attributes:
          
          tile_size:
            The size of a tile in pixels, default is 256.
            
          transformation:
            Transformation to apply to the projected coordinates to convert them
            to tile coordinates. Defaults to Transformation(1, 0, 0, 1, 0), which
            gives row = projected_y * scale, column = projected_x * scale
    """
    def __init__(self, srs, resolutions, tile_size=256, transformation=Transformation(1, 0, 0, 0, 1, 0)):
        """
        Creates a new instance with the projection specified in srs, which is in Proj4
        format.
        """
        
        self.resolutions = resolutions
        self.tile_size = tile_size
        self.proj = Proj(srs)
        self.srs = srs
        self.tile_dimensions = \
            [self.tile_size * r for r in self.resolutions]

        try:
             self.base_zoom = self.resolutions.index(1.0)
        except ValueError:
            raise TileStache.Core.KnownUnknown('No zoom level with resolution 1.0')

        LinearProjection.__init__(self, self.base_zoom, transformation)
        
    def project(self, point, scale):
        p = LinearProjection.project(self, point)
        p.x = p.x * scale
        p.y = p.y * scale
        return p

    def unproject(self, point, scale):
        p = LinearProjection.unproject(self, point)
        p.x = p.x / scale
        p.y = p.y / scale
        return p
        
    def coordinateProj(self, coord):
        """Convert from Coordinate object to a Point object in the defined projection"""
        if coord.zoom >= len(self.tile_dimensions):
            raise TileStache.Core.KnownUnknown('Requested zoom level %d outside defined resolutions.' % coord.zoom)
        p = self.unproject(Point(coord.column, coord.row), 1.0 / self.tile_dimensions[coord.zoom])
        return p

    def locationProj(self, location):
        """Convert from Location object to a Point object in the defined projection"""
        x,y = self.proj(location.lon, location.lat)
        return Point(x, y)

    def projCoordinate(self, point, zoom=None):
        """Convert from Point object in the defined projection to a Coordinate object"""
        if zoom == None:
            zoom = self.base_zoom
        if zoom >= len(self.tile_dimensions):
            raise TileStache.Core.KnownUnknown('Requested zoom level %d outside defined resolutions.' % zoom)

        td = self.tile_dimensions[zoom]
        p = self.project(point, 1.0 / td)
        
        row = round(p.y)
        col = round(p.x)

        if abs(p.y - row) > _grid_threshold \
                or abs(p.x - col) > _grid_threshold:
            raise TileStache.Core.KnownUnknown(('Point(%f, %f) does not align with grid '
                                               + 'for zoom level %d '
                                               + '(resolution=%f, difference: %f, %f).') %
                                               (point.x, point.y, zoom, self.resolutions[zoom],
                                                p.y - row, p.x - col))

        c = Coordinate(int(row), int(col), zoom)
        return c

    def projLocation(self, point):
        """Convert from Point object in the defined projection to a Location object"""
        x,y = self.proj(point.x, point.y, inverse=True)
        return Location(y, x)

    def findZoom(self, resolution):
        try:
            return self.resolutions.index(resolution)
        except ValueError:
            raise TileStache.Core.KnownUnknown("No zoom level with resolution %f defined." % resolution)
