import arcpy
import sys
import os

def main():
    """
    Main function to execute the Custom Hillshade tool logic.
    """
    # 1. Get Parameters from Tool Interface
    dem_path = arcpy.GetParameterAsText(0)  # Input DEM Raster
    aoi_polygon = arcpy.GetParameterAsText(1)  # Input Polygon (Feature Set)

    if not dem_path:
        arcpy.AddError("No DEM provided.")
        return

    # 2. Set Up Environment
    if aoi_polygon:
        arcpy.env.extent = aoi_polygon
        arcpy.AddMessage("Processing extent set to input polygon.")

    arcpy.env.overwriteOutput = True
    # Important: Prevent automatic adding of outputs to the active map,
    # as we want to control adding them to our specific new map.
    arcpy.env.addOutputsToMap = False

    # Check for required extensions
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    elif arcpy.CheckExtension("ImageAnalyst") == "Available":
        arcpy.CheckOutExtension("ImageAnalyst")
    else:
        arcpy.AddError("Spatial Analyst or Image Analyst extension is required.")
        return

    # 3. Create or Access Map
    try:
        p = arcpy.mp.ArcGISProject("CURRENT")
    except OSError:
        arcpy.AddError("This script must be run within an active ArcGIS Pro session.")
        return

    m = None
    # Attempt to create a new map (ArcGIS Pro 3.2+)
    try:
        if hasattr(p, "createMap"):
            m = p.createMap("Custom Hillshade", "Map")
            arcpy.AddMessage("Created new map: 'Custom Hillshade'")
        else:
            # Fallback for older Pro versions
            raise AttributeError("createMap not supported")
    except Exception:
        # Fallback: Use active map
        m = p.activeMap
        if not m:
            arcpy.AddWarning("Could not create new map and no active map found. Using the first map in project.")
            maps = p.listMaps()
            if maps:
                m = maps[0]
            else:
                arcpy.AddError("No maps found in project.")
                return
        else:
            arcpy.AddMessage(f"Using active map: '{m.name}'")

    # 4. Process Rasters (Using arcpy.sa/ia)
    # Import Spatial Analyst tools
    from arcpy.sa import NbrRectangle, Statistics, Hillshade, Slope, Raster

    # Load DEM
    arcpy.AddMessage("Loading DEM...")
    dem_raster = Raster(dem_path)

    # --- Processing Steps ---

    # Step 1: Create Blurred Elevations
    arcpy.AddMessage("Creating blurred elevation layers...")
    # Statistics: Mean, 10x10 and 20x20
    elev_blur_10 = Statistics(dem_raster, NbrRectangle(10, 10, "CELL"), "MEAN")
    elev_blur_20 = Statistics(dem_raster, NbrRectangle(20, 20, "CELL"), "MEAN")

    # Step 2: Create Hillshades
    # Hillshade: Azimuth 315, Altitude 45
    arcpy.AddMessage("Creating hillshade layers...")
    hs_original = Hillshade(dem_raster, 315, 45)
    hs_blur_10 = Hillshade(elev_blur_10, 315, 45)
    hs_blur_20 = Hillshade(elev_blur_20, 315, 45)

    # Step 3: Create Slopes
    # Slope: Degree
    arcpy.AddMessage("Creating slope layers...")
    slope_original = Slope(dem_raster, "DEGREE")
    slope_blur_10 = Slope(elev_blur_10, "DEGREE")
    slope_blur_20 = Slope(elev_blur_20, "DEGREE")

    # Step 4: Create Highlights
    # Uses original Hillshade but styled differently
    highlights_raster = hs_original

    # Step 5: Create Edges
    # Hillshade of the Slope of original elevation
    arcpy.AddMessage("Creating edges layer...")
    edges_raster = Hillshade(slope_original, 315, 45)

    # --- Adding Layers and Applying Symbology ---

    # Helper function to add layer and apply CIM
    def add_and_style_layer(raster, name, style_type):
        """
        Saves a raster to scratchGDB, adds it to the map, and applies the specific CIM symbology.
        style_type options: 'semitransparent_black', 'inverted_semitransparent_black', 'highlights', 'edges'
        """
        # Create a safe name for saving
        safe_name = name.replace(" ", "_")

        # Determine output path in scratchGDB
        # Use arcpy.env.scratchGDB which is always available in Pro
        out_path = os.path.join(arcpy.env.scratchGDB, safe_name)

        # Save the raster to persist it
        # Note: If it already exists, overwriteOutput=True handles it.
        try:
            raster.save(out_path)
        except Exception as e:
            arcpy.AddWarning(f"Failed to save raster {name}: {e}")
            # Try memory workspace as fallback if GDB fails
            out_path = os.path.join("memory", safe_name)
            raster.save(out_path)

        # Add the saved raster to the map
        # map.addDataFromPath returns the added Layer object
        try:
            lyr = m.addDataFromPath(out_path)
        except Exception as e:
            arcpy.AddError(f"Failed to add layer {name}: {e}")
            return None

        # Rename layer to the display name
        lyr.name = name

        # Apply Symbology via CIM
        cim = lyr.getDefinition("V2")

        # Ensure it's a stretch colorizer
        # Most single-band rasters default to Stretch.
        if 'RasterStretchColorizer' not in cim.colorizer.type:
             # If strictly needed, we could force change the colorizer type,
             # but usually for continuous data (Hillshade/Slope/Elev) it is Stretch.
             pass

        # Define Color Stops based on style_type
        # Helper for RGB Color
        def create_color(r, g, b, alpha=100):
            c = arcpy.cim.CreateCIMObjectFromClassName('CIMRGBColor', 'V2')
            c.values = [r, g, b]
            c.alpha = alpha
            return c

        def create_stop(color, position):
            s = arcpy.cim.CreateCIMObjectFromClassName('CIMColorRampColorStop', 'V2')
            s.color = color
            s.position = position
            return s

        stops = []

        if style_type == 'semitransparent_black':
            # Low (0%): Black, 60% Alpha (Transp 40%? No, Tutorial says Transp 60% -> Alpha 40)
            # High (100%): Black, 100% Alpha (Transp 0? No, Tutorial says Transp 100% -> Alpha 0)
            # Wait, let's re-verify Tutorial Text vs Logic.
            # Tutorial: "Low elevations are semitransparent black and high elevations are fully transparent black."
            # "Left (Black) ... Transparency to 60 percent." -> Low Val = Black, Alpha 40.
            # "Right (White -> Black) ... Transparency to 100 percent." -> High Val = Black, Alpha 0.

            stops.append(create_stop(create_color(0,0,0, 40), 0.0))
            stops.append(create_stop(create_color(0,0,0, 0), 1.0))

        elif style_type == 'inverted_semitransparent_black':
            # Inverted of above.
            # Low (Flat) -> Transparent (Alpha 0).
            # High (Steep) -> Semitransparent (Alpha 40).
            stops.append(create_stop(create_color(0,0,0, 0), 0.0))
            stops.append(create_stop(create_color(0,0,0, 40), 1.0))

        elif style_type == 'highlights':
            # "fully transparent white to fully opaque white"
            # Left (Low Val): White, Transp 100% (Alpha 0)
            # Middle (60% Pos): White, Transp 100% (Alpha 0)
            # Right (High Val): White, Opaque (Alpha 100)
            stops.append(create_stop(create_color(255,255,255, 0), 0.0))
            stops.append(create_stop(create_color(255,255,255, 0), 0.6))
            stops.append(create_stop(create_color(255,255,255, 100), 1.0))

        elif style_type == 'edges':
            # 0% (Low): Black, Opaque (Alpha 100)
            # 55%: Black, Opaque (Alpha 100)
            # 70%: Black, Transparent (Alpha 0)
            # 72%: White, Transparent (Alpha 0)
            # 100% (High): White, Opaque (Alpha 100)
            stops.append(create_stop(create_color(0,0,0, 100), 0.0))
            stops.append(create_stop(create_color(0,0,0, 100), 0.55))
            stops.append(create_stop(create_color(0,0,0, 0), 0.70))
            stops.append(create_stop(create_color(255,255,255, 0), 0.72))
            stops.append(create_stop(create_color(255,255,255, 100), 1.0))

        # Construct the Color Ramp
        ramp = arcpy.cim.CreateCIMObjectFromClassName('CIMLinearContinuousColorRamp', 'V2')
        ramp.colorSpace = {"type": "CIMICCColorSpace", "url": "Default RGB"}
        ramp.fromColor = stops[0].color
        ramp.toColor = stops[-1].color
        ramp.colorStops = stops

        # Apply to Colorizer
        cim.colorizer.colorRamp = ramp

        lyr.setDefinition(cim)
        return lyr

    # 5. Add Layers in Order
    # Reverse order logic: Last added is on TOP.

    # 6. Add Background (White Opaque)
    # Re-use DEM for background geometry
    # Save as "Background"
    safe_bg_name = "Background"
    out_bg = os.path.join(arcpy.env.scratchGDB, safe_bg_name)
    dem_raster.save(out_bg)
    lyr_bg = m.addDataFromPath(out_bg)
    lyr_bg.name = "Background"

    # Apply White Opaque CIM
    cim_bg = lyr_bg.getDefinition("V2")
    c_white = arcpy.cim.CreateCIMObjectFromClassName('CIMRGBColor', 'V2')
    c_white.values = [255, 255, 255]
    c_white.alpha = 100
    ramp_bg = arcpy.cim.CreateCIMObjectFromClassName('CIMLinearContinuousColorRamp', 'V2')
    ramp_bg.colorStops = [
        arcpy.cim.CreateCIMObjectFromClassName('CIMColorRampColorStop', 'V2', color=c_white, position=0),
        arcpy.cim.CreateCIMObjectFromClassName('CIMColorRampColorStop', 'V2', color=c_white, position=1)
    ]
    cim_bg.colorizer.colorRamp = ramp_bg
    lyr_bg.setDefinition(cim_bg)

    # 7. Add Edges
    add_and_style_layer(edges_raster, "Edges", "edges")

    # 8. Add Highlights
    add_and_style_layer(highlights_raster, "Highlights", "highlights")

    # 9. Add Slopes
    # Add detailed layers last so they are on top
    add_and_style_layer(slope_blur_20, "Slope Blur 20", "inverted_semitransparent_black")
    add_and_style_layer(slope_blur_10, "Slope Blur 10", "inverted_semitransparent_black")
    add_and_style_layer(slope_original, "Slope", "inverted_semitransparent_black")

    # 10. Add Hillshades
    # Add detailed layers last so they are on top
    add_and_style_layer(hs_blur_20, "Hillshade Blur 20", "semitransparent_black")
    add_and_style_layer(hs_blur_10, "Hillshade Blur 10", "semitransparent_black")
    add_and_style_layer(hs_original, "Hillshade", "semitransparent_black")

    # 11. Add Elevations
    # Add detailed layers last so they are on top
    add_and_style_layer(elev_blur_20, "Elevation Blur 20", "semitransparent_black")
    add_and_style_layer(elev_blur_10, "Elevation Blur 10", "semitransparent_black")
    lyr_elev = add_and_style_layer(dem_raster, "Elevation", "semitransparent_black")

    # 12. Add Basemap
    # Add basemap last - usually puts it at bottom
    m.addBasemap("Imagery")

    arcpy.AddMessage("Process Complete. Layers added to map.")

    # Save Project
    p.save()

if __name__ == "__main__":
    main()
