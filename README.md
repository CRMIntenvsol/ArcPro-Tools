# Custom Hillshade Tool for ArcGIS Pro

This Python script implements the workflow described in the tutorial **[Illuminate terrain with a custom hillshade](https://learn.arcgis.com/en/projects/illuminate-terrain-with-a-custom-hillshade/)**. It automates the creation of a composite hillshade map using multiple blurred elevation layers, hillshades, slopes, and custom CIM-based symbology to achieve a realistic, artistic terrain visualization.

## Requirements

*   **ArcGIS Pro** (Tested on 3.0+)
*   **Spatial Analyst** OR **Image Analyst** Extension

## Setup Instructions

1.  **Download the Script:**
    Save the `arcgis_hillshade_tool.py` file to your computer.

2.  **Add to ArcGIS Pro:**
    *   Open your ArcGIS Pro project.
    *   In the **Catalog** pane, right-click your project toolbox (`.atbx`) -> **New** -> **Script**.
    *   **Name:** `CreateCustomHillshade`
    *   **Label:** `Create Custom Hillshade`
    *   **Script File:** Browse to and select `arcgis_hillshade_tool.py`.

3.  **Configure Parameters:**
    In the Script Tool properties, go to the **Parameters** tab and add the following:

    | Label | Name | Data Type | Type | Direction |
    | :--- | :--- | :--- | :--- | :--- |
    | **Input DEM** | `input_dem` | **Raster Layer** | Required | Input |
    | **Processing Extent (AOI)** | `aoi_polygon` | **Feature Set** | Optional | Input |

    *   *Tip:* For **Processing Extent**, you can set the Data Type to **Feature Set**. This allows you to interactively draw a polygon on the map when the tool runs.

4.  **Finish:** Click **OK** to save the tool.

## Usage

1.  Add your Digital Elevation Model (DEM) to your current map (or have it ready on disk).
2.  Open the **Create Custom Hillshade** tool from your toolbox.
3.  **Input DEM:** Select your elevation raster.
4.  **Processing Extent (AOI):** (Optional) Use the interactive draw button to sketch a polygon around your area of interest. If left blank, the entire DEM extent will be processed.
5.  **Run** the tool.

## Output

The tool will:
1.  Create a **new map** named "Custom Hillshade" (or add to the active map if creation is not supported).
2.  Generate the following layers (from top to bottom):
    *   **Elevation** (Original)
    *   **Elevation Blur 10** & **20**
    *   **Hillshade** (Original, Blur 10, Blur 20)
    *   **Slope** (Original, Blur 10, Blur 20)
    *   **Highlights**
    *   **Edges**
    *   **Background** (White)
    *   **Imagery Basemap**
3.  Apply complex **CIM Symbology** (custom color ramps with transparency) to each layer automatically.

## Notes

*   **Layer Grouping:** Due to limitations in scripting group layers without templates, the layers are added as a flat list. You can manually group them into **Elevation**, **Hillshade**, and **Slope** groups to match the tutorial organization exactly.
*   **Blend Modes:** The script sets up the "Construction" phase with transparency. To achieve the final blended effect with the basemap, you can select the top-most layers (Elevation/Hillshade groups) and set their **Blend Mode** to **Overlay** or **Luminosity** in the Appearance tab, as described in the final steps of the tutorial.
