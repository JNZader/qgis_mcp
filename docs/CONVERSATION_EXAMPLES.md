# Conversation Examples with Claude Desktop

Real examples of using QGIS through Claude Desktop.

---

## 🎯 Basic Operations

### Example 1: First Time Use

**You:**
```
Hi! I just installed the QGIS MCP server. Can you help me test it?
```

**Claude:**
```
Hello! I'd be happy to help you test the QGIS MCP integration. Let me start by
checking what tools I have access to and seeing if there are any layers currently
loaded in QGIS.
```

[Claude uses `list_layers`]

```
Good news! The connection is working. Currently, you have a clean QGIS project
with no layers loaded.

To test the integration, we could:
1. Load a sample dataset (if you have one)
2. Create a simple geometric layer
3. Test the analysis tools

Do you have any GIS data files (shapefiles, GeoJSON, etc.) you'd like to load?
```

---

### Example 2: Loading Data

**You:**
```
Yes, I have a shapefile at C:\gis_data\countries\world_countries.shp
```

**Claude:** [Uses `add_vector_layer`]
```
Perfect! I've loaded the shapefile as "World Countries". Let me get some details
about it...
```

[Uses `get_layer_info`]

```
The layer contains:
- **Feature count:** 177 countries
- **Geometry type:** Polygon
- **CRS:** EPSG:4326 (WGS 84 - Geographic coordinates)
- **Extent:** Global coverage (-180° to 180° longitude, -90° to 90° latitude)
- **Fields:**
  - NAME (String) - Country name
  - ISO_A3 (String) - 3-letter country code
  - POP_EST (Integer) - Estimated population
  - GDP_MD_EST (Integer) - Estimated GDP
  - CONTINENT (String) - Continent name

This looks like a comprehensive world countries dataset! What would you like to
explore or analyze?
```

---

### Example 3: Data Exploration

**You:**
```
Show me the 10 most populous countries
```

**Claude:** [Uses `get_features` with sort/filter]
```
Here are the 10 most populous countries based on the estimated population:

1. **China** - 1,439,323,776 people
2. **India** - 1,380,004,385 people
3. **United States** - 331,002,651 people
4. **Indonesia** - 273,523,615 people
5. **Pakistan** - 220,892,340 people
6. **Brazil** - 212,559,417 people
7. **Nigeria** - 206,139,589 people
8. **Bangladesh** - 164,689,383 people
9. **Russia** - 145,934,462 people
10. **Mexico** - 128,932,753 people

Interesting observations:
- Asia dominates with 6 of the top 10
- Combined population of top 10: ~4.5 billion (57% of world population)
- Significant gap between China/India and the rest

Would you like me to:
- Calculate more detailed statistics?
- Create a map visualization?
- Analyze population by continent?
```

---

## 🗺️ Spatial Analysis

### Example 4: Buffer Analysis

**You:**
```
I want to find all areas within 50km of the coast. I have a coastline layer
loaded.
```

**Claude:**
```
Great! To find areas within 50km of the coast, I'll:
1. Create a 50km buffer around the coastline
2. Show you the results

Let me first check what layers you have...
```

[Uses `list_layers`]

```
I can see your "Coastline" layer. Let me create the buffer now...
```

[Uses `buffer_layer`]

```
Done! I've created a new layer called "Coastal_Zone_50km" with the buffered area.

This layer now shows all areas within 50 kilometers of the coastline.

Some statistics about the buffer:
- Buffer features: [number from tool result]
- Total coastline length: [if available]

Next steps you could consider:
1. Clip your countries layer by this buffer to find coastal countries
2. Calculate how much land area is within 50km of coast
3. Export a map showing the coastal zones

Would you like me to proceed with any of these?
```

---

### Example 5: Multi-Step Analysis

**You:**
```
Yes, show me which countries have coastline
```

**Claude:**
```
I'll find all countries that intersect with the coastal zone buffer. This will
give us countries with coastline...
```

[Uses `clip_layer` or similar intersection operation]

```
Analysis complete! Here are the countries with coastline:

**Total coastal countries:** 142 (out of 177 total countries)

**By continent:**
- Africa: 38 coastal countries
- Asia: 35 coastal countries
- Europe: 29 coastal countries
- North America: 23 coastal countries
- South America: 12 coastal countries
- Oceania: 5 coastal countries

**Landlocked countries:** 35 total
Notable landlocked countries: Switzerland, Austria, Mongolia, Bolivia,
Paraguay, Afghanistan, Nepal, etc.

**Interesting facts:**
- Island nations (100% coastal): Japan, Philippines, Indonesia, UK, etc.
- Countries with longest coastlines: Canada, Indonesia, Greenland, Russia
- Most connected continent: Europe (nearly all countries have coast access)

Would you like me to:
1. Export a map showing coastal vs landlocked countries?
2. Calculate percentage of each country within the coastal zone?
3. Analyze population living in coastal areas?
```

---

## 📊 Statistics and Analysis

### Example 6: Field Statistics

**You:**
```
Calculate statistics for the GDP field
```

**Claude:** [Uses `calculate_statistics`]

```
Here are the GDP statistics for all countries:

**Summary Statistics:**
- **Count:** 177 countries
- **Total GDP:** $142.4 trillion
- **Mean GDP:** $804.5 billion per country
- **Median GDP:** $45.2 billion
- **Minimum:** $0.6 billion (Tuvalu)
- **Maximum:** $21.4 trillion (United States)

**Distribution:**
- Top 10% of countries: $98.7 trillion (69% of world GDP)
- Bottom 50% of countries: $8.9 trillion (6% of world GDP)

**By Continent:**
- Asia: $39.8 trillion (28%)
- North America: $25.1 trillion (18%)
- Europe: $23.4 trillion (16%)
- South America: $5.9 trillion (4%)
- Africa: $2.8 trillion (2%)
- Oceania: $1.9 trillion (1%)

**Economic Inequality:**
The wealth concentration is significant - the top 10 economies account for nearly
70% of global GDP, while half of all countries share only 6%.

Would you like me to:
1. Create a choropleth map showing GDP distribution?
2. Analyze GDP per capita instead?
3. Compare GDP with population to find economic outliers?
```

---

## 🎨 Map Creation

### Example 7: Export Map

**You:**
```
Create a map showing the countries colored by population
```

**Claude:**
```
I'll export a map showing population distribution across countries. Let me set up
the visualization...
```

[Uses `export_map`]

```
Map created successfully!

**Map Details:**
- File: world_population_map.png
- Resolution: 1920 x 1080 pixels
- Format: PNG
- Extent: Global (all countries visible)

**Legend:**
- Darker colors = Higher population
- Lighter colors = Lower population

The map clearly shows:
- High population density in Asia (China, India, Indonesia)
- Moderate population in Europe and North America
- Lower population density in Africa (despite large countries)
- Very low density in Oceania and Arctic regions

Would you like me to:
1. Export at higher resolution for printing (300 DPI)?
2. Change to PDF format?
3. Create a focused map of a specific region?
```

---

### Example 8: High-Resolution Export

**You:**
```
Yes, export a PDF at print quality focused on Europe
```

**Claude:** [Uses `export_map` with parameters]

```
High-resolution map created!

**Map Details:**
- File: europe_map.pdf
- Resolution: 3300 x 2550 pixels (A4 at 300 DPI)
- Format: PDF (vector graphics where possible)
- Region: Europe
- DPI: 300 (print quality)

This PDF is suitable for:
- Professional printing
- Reports and presentations
- Publication in documents

The file is ready at: europe_map.pdf

Would you like me to create maps for other regions or adjust the styling?
```

---

## 🔬 Advanced Workflows

### Example 9: Complete Analysis Project

**You:**
```
I'm studying urban heat islands. I need to:
1. Find all cities over 1 million population
2. Create 10km zones around them
3. Extract elevation data for these zones
4. Calculate average elevation

Can you help?
```

**Claude:**
```
Absolutely! This is a great urban heat island analysis. Let me break this down
into steps and execute them:

**Step 1: Identify major cities**
Let me filter your cities layer for population > 1 million...
```

[Uses `get_features` with filter]

```
Found 512 cities with population over 1 million. Top 10:
1. Tokyo (38.5M)
2. Delhi (30.3M)
3. Shanghai (27.1M)
...

**Step 2: Create 10km urban zones**
Creating buffer zones around each city...
```

[Uses `buffer_layer`]

```
Created "Urban_Zones_10km" layer with 512 buffered areas.

**Step 3: Extract elevation for urban zones**
Now I'll clip your elevation data to the urban zones...
```

[Uses `clip_layer`]

```
Elevation data extracted for all urban zones.

**Step 4: Calculate statistics**
Computing average elevation for each zone...
```

[Uses `calculate_statistics`]

```
**Analysis Results:**

**Global Urban Zone Statistics:**
- Average elevation: 245 meters above sea level
- Median elevation: 156 meters
- Lowest city zones:
  - Amsterdam: -2m (below sea level)
  - New Orleans: 1m
  - Bangkok: 2m
- Highest city zones:
  - La Paz, Bolivia: 3,640m
  - Quito, Ecuador: 2,850m
  - Mexico City: 2,240m

**Urban Heat Island Implications:**
- 68% of major cities are in low-elevation coastal areas (<100m)
- These cities are more vulnerable to urban heat islands
- Coastal proximity may provide some cooling but increases flood risk
- High-altitude cities may have different heat island dynamics

**Regional Patterns:**
- Asian cities: Average 165m (mostly coastal plains)
- European cities: Average 287m (more inland/elevated)
- American cities: Average 312m (varied terrain)
- African cities: Average 456m (highland plateaus)

I can now:
1. Export maps showing this analysis
2. Create detailed reports for each region
3. Correlate elevation with temperature data (if available)
4. Identify most vulnerable cities

What would you like to explore next?
```

---

### Example 10: Problem Solving

**You:**
```
The buffer operation failed with "Invalid geometry" error
```

**Claude:**
```
I see the issue. "Invalid geometry" errors in QGIS often occur when:

1. **Self-intersecting polygons** - The geometry crosses itself
2. **Null geometries** - Some features have no geometry
3. **CRS mismatch** - Layers in different coordinate systems

Let me diagnose your data:
```

[Uses `get_layer_info`]

```
I found the issue: Your layer is in geographic coordinates (EPSG:4326), which
uses degrees. When you buffer in "meters", QGIS gets confused.

**Solution:** We need to either:
1. Reproject to a projected CRS (like UTM or Web Mercator)
2. Use degree units for buffering

Let me help you fix this. What region are you working in? I can suggest the
best projection for your area.

Alternatively, if you want quick results, I can:
- Use a degree-based buffer (0.09° ≈ 10km at equator)
- Reproject on-the-fly during buffering

Which approach would you prefer?
```

---

## 💡 Learning & Exploration

### Example 11: Teaching Moment

**You:**
```
I'm new to GIS. What's a buffer and when would I use it?
```

**Claude:**
```
Great question! Let me explain buffers with a practical example.

**What is a Buffer?**
A buffer is a zone of a specified distance around a geographic feature.

**Real-World Example:**
Imagine you have a dataset of schools and want to know "which areas are within
walking distance (500m) of a school?"

The buffer creates a circle (or polygon) around each school with a 500m radius.
Areas inside any buffer are "within walking distance."

**Common Uses:**

1. **Proximity Analysis**
   - "Find all houses within 1km of a highway" (noise/pollution study)
   - "Identify areas 5km from fire stations" (emergency response coverage)

2. **Environmental Protection**
   - "Create 100m buffer around rivers" (riparian protection zones)
   - "Define 500m buffer around wetlands" (no-development zones)

3. **Urban Planning**
   - "Find properties within 400m of public transit" (transit-oriented development)
   - "Identify 10km zones around airports" (noise impact areas)

4. **Business Analysis**
   - "Map 5km delivery zones around restaurants"
   - "Find customer density within 10km of stores"

**Let's try it with your data!**

Do you have any layers loaded? I can demonstrate a buffer analysis with your
actual data to make it more concrete.
```

---

### Example 12: Workflow Design

**You:**
```
I want to find the best location for a new hospital. How would I approach this
with GIS?
```

**Claude:**
```
Excellent question! This is a classic site suitability analysis. Let me design
a GIS workflow for you.

**Hospital Site Selection - GIS Workflow:**

**Phase 1: Define Criteria**
First, let's identify what makes a good hospital location:

1. **Accessibility**
   - Near major roads (ambulance access)
   - Not too close to existing hospitals (avoid redundancy)
   - Central to underserved populations

2. **Infrastructure**
   - Adequate land area (minimum 2-5 hectares)
   - Utilities available (water, power, sewage)
   - Flat or gently sloping terrain

3. **Regulatory**
   - Zoned for healthcare use
   - Not in floodplains or hazard zones
   - Minimum distance from incompatible uses

**Phase 2: Data Requirements**
You'll need these layers:

- Existing hospitals (point layer)
- Roads network (line layer)
- Population distribution (polygon or raster)
- Land parcels (polygon layer)
- Elevation (raster)
- Flood zones (polygon)
- Zoning (polygon)

**Phase 3: GIS Analysis Steps**

```
# Step 1: Find underserved areas
1. Buffer existing hospitals (5km radius = "served" area)
2. Identify areas NOT in these buffers = underserved

# Step 2: Accessibility
3. Buffer major roads (500m = good access)
4. Intersect with underserved areas

# Step 3: Suitable land
5. Select flat areas (slope < 5%)
6. Select parcels > 20,000 m²
7. Exclude flood zones
8. Filter by proper zoning

# Step 4: Population proximity
9. Calculate population within 5km of each candidate site
10. Rank by population served

# Step 5: Combine results
11. Overlay all criteria
12. Score each site
13. Rank candidates
```

**Let's Start!**

Do you have these data layers? If so, I can help you execute this analysis
step-by-step. If not, I can suggest where to find this data or how to adapt
the analysis to what you have.

What data do you currently have available?
```

---

## 🎯 Quick Tasks

### Example 13: One-Off Analysis

**You:**
```
Quick question: how many features are in my Roads layer?
```

**Claude:** [Uses `get_layer_info`]

```
Your "Roads" layer contains **8,453 features** (road segments).

Additional info:
- Total road length: 12,847 km
- CRS: EPSG:32633 (WGS 84 / UTM zone 33N)
- Fields: road_type, name, surface, width

Is there anything specific about the roads you'd like to analyze?
```

---

### Example 14: Simple Export

**You:**
```
Export this as a PDF
```

**Claude:** [Uses `export_map`]

```
Done! Map exported to "qgis_map.pdf" at 1920x1080, suitable for presentations.

The PDF includes all visible layers in your current map view.
```

---

These examples show how natural the conversation can be while Claude performs
complex GIS operations in the background!

**Try your own workflows!** Claude can adapt to any GIS task you describe.
