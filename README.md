# nightime_walkability
This repository contains the code developed during my internship in AAU-CRENAU for the analysis of **night-time pedestrian mobility and walkability** from GPS trajectories.

The objective is to investigate how the **urban environment and pedestrian trajectories differ between daytime and nighttime**, with a particular focus on the characteristics of the built environment encountered along walking trajectories.

The overall processing pipeline is:

```text
Raw GPS trajectories
        │
        ▼
┌─────────────────────────┐
│ 1. Data acquisition     │
│    OSM / GNSS traces     │
└────────────┬────────────┘
             │
             ▼
┌──────────────────────────────┐
│ 2. GPX preprocessing         │
│    - parse GPX files          │
│    - recover timestamps       │
│    - remove points without    │
│      valid time information   │
│    - separate individual     │
│      trajectories             │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 3. Trajectory filtering      │
│    - walking detection       │
│    - speed filtering         │
│    - minimum points          │
│    - temporal consistency    │
└──────────────┬───────────────┘
               │
               ▼
┌─────────────────────────┐
│ 4. Map matching         │
│    GPS → pedestrian     │
│    network              │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ 4. Feature extraction   │
│    Urban morphology     │
│    Street environment
     Day/ night           │
└────────────┬────────────┘
             │
             ▼
       Analysis of
     night-time walking
```

---

## 1. Project objectives

The project aims to identify **urban and trajectory-level determinants associated with walking at night**.

The analysis combines:

* pedestrian GPS trajectories;
* OpenStreetMap pedestrian networks;
* building geometry and height information;
* public street-lighting data;
* astronomical information to define daytime/nighttime periods;
* urban morphology indicators;
* trajectory and map-matching information.

The main research questions include:

1. How do pedestrian trajectories differ between daytime and nighttime?
2. Which characteristics of the urban environment are associated with nighttime walking?
3. Does the built environment encountered along a trajectory differ depending on the time of day?
4. Which spatial and morphological features may help explain changes in pedestrian route choice?

---


# 2. Trajectory preprocessing

The trajectory preprocessing pipeline is designed to be **city-independent**.

The same sequence of processing steps is applied to the datasets from different study areas, including Paris and London, and can be extended to any city for which compatible GPX trajectory data are available.

For each city, the data are stored in separate directories corresponding to successive preprocessing stages.

For example, for paris:

```text
paris_gpx
    │
    │  Extract individual traces
    ▼
paris-traces
    │
    │  Split by GPX <trkseg>
    ▼
paris_segment_traces
    │
    │  Temporal cleaning
    │  Remove observations without timestamps
    ▼
paris_traces_clean
    │
    │  Walking trajectory filtering
    ▼
paris_traces_walking


The same structure is used for different cities:

```text
Paris:
    paris_gpx
    paris-traces
    paris_segment_traces
    paris_traces_clean
    paris_traces_walking

London:
    london_gpx
    london-traces
    london_segment_traces
    london_traces_clean
    london_traces_walking
```
## 2.1 Raw GPX data

`CITY_gpx` contains the original GPX trajectory data obtained for the study area.

These raw files are preserved before any preprocessing is applied.

The raw GPX data contain:

* several individual traces in the same file;
* multiple recording segments;
* observations without timestamps;
* recording interruptions;
* temporal inconsistencies.

Consequently, the raw files cannot be directly considered as clean individual trajectories.

---

## 2.2 Individual trace extraction

The first preprocessing step separates the individual traces contained in the raw GPX dataset.

The objective is to transform the raw collection into independently processable trajectories.

```text
Raw GPX data
      │
      ├── Trace 1
      ├── Trace 2
      ├── Trace 3
      └── ...
```

The resulting traces are stored in:

```text
CITY-traces/
```

This stage focuses on **identifying and separating individual traces**, without yet performing the final temporal or walking-quality filtering.

---

## 2.3 GPX segment separation

A single trace may contain several GPX `<trkseg>` elements.

These segments can correspond to interruptions or separate continuous portions of a recording.

The next stage therefore separates the trace according to its GPX track segments.

```text
CITY-traces/
      │
      ▼
Split by <trkseg>
      │
      ▼
CITY_segment_traces/
```

This prevents disconnected recording portions from being automatically treated as one continuous trajectory.

Each resulting segment can then be processed independently.

---

## 2.4 Temporal cleaning

The segment-level trajectories are then cleaned using their temporal information.

This stage:

* extracts timestamps from GPX observations;
* identifies missing timestamps;
* removes observations for which temporal information is unavailable or invalid;
* orders observations chronologically;
* checks temporal consistency;
* preserves the spatial coordinates associated with valid observations.

The resulting dataset is stored in:

```text
CITY_traces_clean/
```


## 2.5 Walking trajectory filtering

The cleaned trajectories are then filtered to identify trajectories corresponding to pedestrian movement.

The filtering procedure include:

* minimum number of observations;
* plausible pedestrian speed;
* temporal consistency;
* removal of unrealistic movements;

The resulting dataset is stored in:

```text
CITY_traces_walking/
```

These trajectories constitute the **input dataset for map matching**.



This city-independent organization makes the pipeline suitable for **multi-city comparative studies** as well as for processing a new city from scratch.


# 3. Day / night classification

Each trajectory is associated with a temporal period based on its timestamp and the astronomical conditions at the corresponding location.

The project uses **astronomical twilight** rather than a simple fixed-hour definition of night.

The day/night classification can therefore account for seasonal changes in sunrise and sunset.

A trajectory may be classified as:

```text
DAY
NIGHT
MIXED
```

depending on the temporal distribution of its observations.

This classification is used later to compare the characteristics of trajectories and their surrounding urban environments.

---

# 4. Map matching

GPS observations do not necessarily lie directly on the pedestrian network.

The map-matching stage associates each GPS trajectory with the most plausible sequence of edges in the OSM pedestrian network.

The general workflow is:

```text
GPS trajectory
      │
      ▼
GPS observations
      │
      ▼
Candidate network locations
      │
      ▼
Map-matching algorithm
      │
      ▼
Matched pedestrian path
      │
      ▼
Network edges
```

The project uses a **Hidden Markov Model (HMM)-based map-matching approach**.

The pedestrian network is constructed from OpenStreetMap data and stored as a graph, typically in GraphML format.

For each trajectory, the matching procedure produces:

* matched network nodes/edges;
* the corresponding trajectory points;
* the matched path;
* matching diagnostics;
* information about unsuccessful or incomplete matches.

output:

```text
data/
└── map_matching/
    ├── matched_trajectories.gpkg
    ├── matching_summary.csv
    └── unique_edges.csv
```

The pedestrian graph should be generated once and reused for all trajectories in order to avoid rebuilding or reloading the network unnecessarily.

---

# 6. Spatial feature extraction

After map matching, environmental features are computed along the pedestrian trajectories.

The objective is to characterize the **urban environment experienced by pedestrians**.

The feature extraction combines several datasets:

```text
                  ┌───────────────┐
                  │ GPS trajectory│
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ Map matching  │
                  └───────┬───────┘
                          │
                          ▼
             Matched trajectory points
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
      Buildings      Streetlights      OSM network
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                  Urban features
```

## 6.1 Street morphology

The surrounding street geometry is characterized using ray-based measurements.

For each trajectory location, rays are cast around the pedestrian position to describe the geometry of the surrounding street.

The resulting measurements include indicators such as:

* minimum ray length;
* mean ray length;
* median ray length;
* ray-length dispersion;
* harmonic-type indicators;
* 2D and 2.5D ray measurements.

These measurements provide information about the openness or enclosure of the pedestrian's visual environment.

---

## 6.2 Sky View Factor

The **Sky View Factor (SVF)** is used to characterize how much of the sky is visible from a pedestrian position.

The computation is based on the surrounding building geometry and ray casting.

The current analysis includes, among others:

```text
svf_geom
```

as well as ray-length-derived indicators such as:

```text
min_raylen2D
avg_raylen2D
med_raylen2D
drift_raylen2D
H_raylen2D
avg_raylen25D
```

The building heights are incorporated when available in order to obtain three-dimensional morphological information.

---

## 6.3 Building environment

Building footprints and heights are used to characterize the built environment around each pedestrian position.

Potential indicators include:

* building height;
* building density;
* distance to surrounding buildings;
* street enclosure;
* visibility-related indicators;
* 2D and 3D morphological measures.

Building height information can be derived from available geographic datasets and associated with building geometries. For paris we used BD TOPO from IGN, while for London we used data from GlobalBuildingAtlas.

The prepare_GBA.py and Beijing_GBA.py files are examples to download and preprocess building data needed from GlobalBuildingAtlas in gpkg format.
for example: For London, building data are obtained from the GlobalBuildingAtlas (GBA).

Because the complete global dataset is not required, a dedicated script automatically identifies and downloads the GBA tile(s) covering the study area.

The processing workflow is:

GlobalBuildingAtlas
        │
        ▼
Required tile(s)
        │
        ▼
GBA processing / enrichment
        │
        ▼
3D / LoD1 building geometries
        │
        ▼
Reprojection to study CRS
        │
        ▼
Study-area clipping
        │
        ▼
London building dataset

The script allows to automate the acquisition and preparation of the required GBA data, including the generation of the LoD1 building representation used by the subsequent analysis.

---

## 6.4 Street lighting

Street-lighting data are incorporated(when available) to characterize the artificial lighting environment.

For each trajectory location, nearby streetlights can be identified and summarized.

One of the current features is:

```text
streetlight_count
```

representing the number of streetlights within the selected spatial context.

This feature is particularly relevant for the analysis of night-time pedestrian environments.

---

# 7. Feature dataset

The different processing stages are eventually combined into a single analytical dataset.

A typical feature table contains information such as:

```text
trace_id
period
edge_id
sample_idx
fraction

min_raylen2D
avg_raylen2D
med_raylen2D
drift_raylen2D
H_raylen2D

avg_raylen25D
svf_geom

isovist_area
isovist_perimeter

streetlight_count

hauteur
...
```

Each observation corresponds to a spatial sample along a pedestrian trajectory.

The resulting dataset can then be aggregated at different levels:

* GPS point;
* trajectory;
* network edge;
* day/night period;
* individual participant, when available.

---

# 8. Repository structure

The repository is organized to reflect the processing pipeline:

```text
night-time-walkability/
│
├── README.md
│
├── src/
│   │
│   ├── 01_data_acquisition/
│   │   ├── osm_network.py
│   │   ├── buildings.py
│   │   └── streetlights.py
│   │
│   ├── 02_preprocessing/
│   │   ├── filter_trajectories.py
│   │   ├── walking_detection.py
│   │   └── day_night.py
│   │
│   ├── 03_map_matching/
│   │   ├── map_matching.py
│   │   └── network.py
│   │
│   └── 04_features/
│       ├── morphological_features.py
│       ├── svf.py
│       ├── isovist.py
│       └── streetlights.py
│
├── data/
│   ├── raw/
│   ├── osm/
│   ├── buildings/
│   ├── streetlights/
│   └── processed/
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_trajectory_analysis.ipynb
│   └── 03_feature_analysis.ipynb
│
├── results/
│   ├── maps/
│   ├── tables/
│   └── figures/
│
└── requirements.txt
```

Large datasets and raw trajectories should **not be committed directly to GitHub**. Their paths and acquisition instructions should instead be documented.

---

# 9. Reproducibility

The pipeline is designed to be reusable for different cities.

The main city-specific parameters should be defined in a configuration file rather than hard-coded in the processing scripts.

For example:

```yaml
city: Paris

crs: EPSG:2154

osm_graph: data/osm/paris_walk.graphml

trajectory_folder: data/traces/paris/

building_file: data/buildings/paris_buildings.gpkg

streetlight_file: data/streetlights/paris_streetlights.gpkg
```

A similar configuration can be created for another study area:

```yaml
city: London

crs: EPSG:27700

osm_graph: data/osm/london_walk.graphml

trajectory_folder: data/traces/london/

building_file: data/buildings/london_buildings.gpkg

streetlight_file: data/streetlights/london_streetlights.gpkg
```

This allows the same processing pipeline to be applied to multiple cities.

---

