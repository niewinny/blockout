
def find_valid_3d_areas(self, context):
    """Find valid 3D view areas for dropping and identify asset shelf regions"""
    valid_areas = []
    self.asset_shelf_areas = []

    # First, identify all asset shelf regions
    for area in context.screen.areas:
        for region in area.regions:
            # Add any region related to asset shelves to invalid areas
            if region.type in ['ASSET_SHELF', 'ASSET_SHELF_HEADER', 'ASSET_SHELF_FOOTER']:
                shelf_info = {
                    'width': region.width,
                    'height': region.height,
                    'right': region.x + region.width,
                    'top': region.y + region.height,
                    'left': region.x,
                    'bot': region.y
                }
                self.asset_shelf_areas.append(shelf_info)

    # Identify valid 3D view window regions
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            window_region = None
            region_3d = None

            for r in area.regions:
                if r.type == 'WINDOW':
                    window_region = r
                    break

            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    region_3d = space.region_3d
                    break

            if window_region and region_3d:
                # Store valid 3D view data
                area_info = {
                    'area': area,
                    'region': window_region,
                    'region_3d': region_3d,
                    'width': window_region.width,
                    'height': window_region.height,
                    'right': window_region.x + window_region.width,
                    'top': window_region.y + window_region.height,
                    'left': window_region.x,
                    'bot': window_region.y
                }
                valid_areas.append(area_info)

    return valid_areas

def is_mouse_in_asset_shelf(cls, position):
    """Check if mouse is over any asset shelf region"""

    for area_info in cls.asset_shelf_areas:
        if (area_info['left'] <= position.x < area_info['right'] and
            area_info['bot'] <= position.y < area_info['top']):
            return True
    return False

def is_mouse_in_valid_area(cls, position):
    """Check if mouse is in a valid drop area (3D view and not asset shelf)"""
    # First check if it's over the asset shelf
    if is_mouse_in_asset_shelf(cls, position):
        return None

    # Then check if it's in a 3D view area
    for area_info in cls.valid_drop_areas:
        if (area_info['left'] <= position.x < area_info['right'] and
            area_info['bot'] <= position.y < area_info['top']):
            return area_info
    return None
