import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


# CONFIGURATION

# CITY

CITY_NAME = "london"

# INPUT FILE
INPUT_FILE = "C:/Users/oussama.nair/Downloads/outputs/london_morphological_features.csv"
# LIGHTING

# True  -> include streetlight features if available
# False -> completely ignore lighting
USE_LIGHTING = False

# LIGHTING FEATURES

lighting_features = [
    "streetlight_count",
]

# OUTPUT DIRECTORY
OUTPUT_DIR = Path(
    f"analysis_{CITY_NAME}"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def output_file(filename):
    """
    Return a path inside the city-specific output directory.
    """

    return OUTPUT_DIR / filename


def print_section(title):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# LOAD DATA
# ============================================================

print_section(
    f"LOADING DATA — {CITY_NAME.upper()}"
)

input_path = Path(INPUT_FILE)

if not input_path.exists():

    raise FileNotFoundError(
        f"Input file not found:\n"
        f"{input_path.resolve()}"
    )


df = pd.read_csv(
    input_path
)


print(
    f"Input file: "
    f"{input_path.resolve()}"
)

print(
    f"Shape: {df.shape}"
)


# ============================================================
# CHECK PERIOD COLUMN
# ============================================================

if "period" not in df.columns:

    raise ValueError(
        "The input CSV must contain a "
        "'period' column."
    )


print(
    "\nPeriod distribution:"
)

print(
    df["period"].value_counts(
        dropna=False
    )
)


# ============================================================
# DEFINE MORPHOLOGICAL FEATURES
# ============================================================

svf_features = [

    "min_raylen2D",

    "avg_raylen2D",

    "med_raylen2D",

    "drift_raylen2D",

    "H_raylen2D",

    "avg_raylen25D",

    "h_over_w",

    "svf_geom",
]


isovist_features = [

    "isovist_area",

    "isovist_perimeter",
]


# ============================================================
# AVAILABLE FEATURES
# ============================================================

print_section(
    "CHECKING AVAILABLE FEATURES"
)


all_requested_features = (
    svf_features
    + isovist_features
)


if USE_LIGHTING:

    all_requested_features += (
        lighting_features
    )


available_features = []

missing_features = []


for feature in all_requested_features:

    if feature in df.columns:

        available_features.append(
            feature
        )

    else:

        missing_features.append(
            feature
        )


# ------------------------------------------------------------
# Report missing features
# ------------------------------------------------------------

if missing_features:

    print(
        "\nFeatures requested but not found:"
    )

    for feature in missing_features:

        print(
            f"  - {feature}"
        )


# ------------------------------------------------------------
# Report available features
# ------------------------------------------------------------

print(
    "\nAvailable features:"
)

for feature in available_features:

    print(
        f"  - {feature}"
    )


# ============================================================
# LIGHTING STATUS
# ============================================================

print_section(
    "LIGHTING"
)


if USE_LIGHTING:

    available_lighting = [

        f

        for f in lighting_features

        if f in df.columns
    ]


    if available_lighting:

        print(
            "Lighting analysis: ENABLED"
        )

        print(
            "Lighting features:"
        )

        for feature in available_lighting:

            print(
                f"  - {feature}"
            )

    else:

        print(
            "Lighting analysis requested "
            "but no lighting features were found."
        )

        print(
            "Continuing without lighting."
        )

        USE_LIGHTING = False


else:

    print(
        "Lighting analysis: DISABLED"
    )


# ============================================================
# FINAL FEATURE LIST
# ============================================================

features = []


for feature in svf_features:

    if feature in df.columns:

        features.append(
            feature
        )


for feature in isovist_features:

    if feature in df.columns:

        features.append(
            feature
        )


if USE_LIGHTING:

    for feature in lighting_features:

        if feature in df.columns:

            features.append(
                feature
            )


print_section(
    "FINAL FEATURE SET"
)


for feature in features:

    print(
        f"  - {feature}"
    )


if not features:

    raise ValueError(
        "No analysis features were found "
        "in the input CSV."
    )


# ============================================================
# NUMERIC CONVERSION
# ============================================================

print_section(
    "CONVERTING FEATURES TO NUMERIC"
)


for feature in features:

    df[feature] = pd.to_numeric(
        df[feature],
        errors="coerce"
    )


# ============================================================
# MISSING VALUES
# ============================================================

print_section(
    "MISSING VALUES"
)


missing = (
    df[features]
    .isna()
    .sum()
)


missing_percent = (
    100
    *
    missing
    /
    len(df)
)


missing_table = pd.DataFrame({

    "missing_count":
        missing,

    "missing_percent":
        missing_percent,

})


print(
    missing_table
)


print(
    "\nTotal missing values:",
    missing.sum()
)


missing_table.to_csv(
    output_file(
        "selected_feature_missing_values.csv"
    )
)


# ============================================================
# DESCRIPTIVE STATISTICS
# ============================================================

print_section(
    "DESCRIPTIVE STATISTICS"
)


stats = (
    df[features]
    .describe()
    .T
)


print(
    stats
)


stats.to_csv(
    output_file(
        "selected_feature_statistics.csv"
    )
)


# ============================================================
# PERIOD COUNTS
# ============================================================

print_section(
    "PERIOD COUNTS"
)


period_counts = (
    df["period"]
    .value_counts(
        dropna=False
    )
)


print(
    period_counts
)


period_counts.to_csv(
    output_file(
        "period_counts.csv"
    )
)


# ============================================================
# PERIOD MEANS
# ============================================================

print_section(
    "PERIOD MEANS"
)


period_mean = (

    df
    .groupby(
        "period"
    )[features]
    .mean()
    .T
)


print(
    period_mean
)


period_mean.to_csv(
    output_file(
        "selected_features_period_mean.csv"
    )
)


# ============================================================
# PERIOD MEDIANS
# ============================================================

print_section(
    "PERIOD MEDIANS"
)


period_median = (

    df
    .groupby(
        "period"
    )[features]
    .median()
    .T
)


print(
    period_median
)


period_median.to_csv(
    output_file(
        "selected_features_period_median.csv"
    )
)


# ============================================================
# DAY / NIGHT COMPARISON
# ============================================================

print_section(
    "DAY / NIGHT COMPARISON"
)


periods = set(
    df["period"]
    .dropna()
    .astype(str)
    .str.lower()
    .unique()
)


if {
    "day",
    "night"
}.issubset(periods):


    day_mask = (
        df["period"]
        .astype(str)
        .str.lower()
        == "day"
    )


    night_mask = (
        df["period"]
        .astype(str)
        .str.lower()
        == "night"
    )


    day_mean = (
        df.loc[
            day_mask,
            features
        ]
        .mean()
    )


    night_mean = (
        df.loc[
            night_mask,
            features
        ]
        .mean()
    )


    comparison = pd.DataFrame({

        "day_mean":
            day_mean,

        "night_mean":
            night_mean,

        "absolute_difference":
            (
                night_mean
                -
                day_mean
            ),

        "relative_difference_percent":
            (
                100
                *
                (
                    night_mean
                    -
                    day_mean
                )
                /
                day_mean.replace(
                    0,
                    np.nan
                )
            ),
    })


    print(
        comparison
    )


    comparison.to_csv(
        output_file(
            "selected_features_day_night_comparison.csv"
        )
    )


else:

    print(
        "Day/night comparison skipped."
    )

    print(
        "Both 'day' and 'night' "
        "periods are required."
    )


# ============================================================
# CORRELATION
# ============================================================

print_section(
    "CORRELATION MATRIX"
)


corr = (
    df[features]
    .corr(
        method="pearson"
    )
)


print(
    corr.round(3)
)


corr.to_csv(
    output_file(
        "selected_features_correlation.csv"
    )
)


# ============================================================
# HIGH CORRELATIONS
# ============================================================

print_section(
    "HIGH CORRELATIONS |r| >= 0.80"
)


pairs = []


for i in range(
    len(features)
):

    for j in range(
        i + 1,
        len(features)
    ):

        value = (
            corr.iloc[i, j]
        )


        if pd.notna(value):

            if abs(value) >= 0.80:

                pairs.append({

                    "feature_1":
                        features[i],

                    "feature_2":
                        features[j],

                    "correlation":
                        value,

                })


high_corr = pd.DataFrame(
    pairs
)


if len(high_corr) > 0:

    high_corr[
        "abs_correlation"
    ] = (
        high_corr[
            "correlation"
        ]
        .abs()
    )


    high_corr = (
        high_corr
        .sort_values(
            "abs_correlation",
            ascending=False
        )
    )


    print(
        high_corr
    )


else:

    print(
        "No feature pairs above "
        "|r| >= 0.80"
    )


high_corr.to_csv(
    output_file(
        "selected_features_high_correlations.csv"
    ),
    index=False
)


# ============================================================
# CORRELATION HEATMAP
# ============================================================

print_section(
    "CORRELATION HEATMAP"
)


fig, ax = plt.subplots(
    figsize=(12, 10)
)


im = ax.imshow(
    corr.values,
    aspect="auto"
)


ax.set_xticks(
    range(len(features))
)


ax.set_yticks(
    range(len(features))
)


ax.set_xticklabels(
    features,
    rotation=70,
    ha="right"
)


ax.set_yticklabels(
    features
)


plt.colorbar(
    im,
    ax=ax,
    label="Pearson correlation"
)


ax.set_title(
    f"Correlation matrix — "
    f"{CITY_NAME.capitalize()}"
)


fig.tight_layout()


fig.savefig(
    output_file(
        "selected_features_correlation_heatmap.png"
    ),
    dpi=200
)


plt.close(fig)


# ============================================================
# DISTRIBUTIONS
# ============================================================

print_section(
    "DISTRIBUTIONS"
)


print(
    "Generating distributions..."
)


for feature in features:

    values = (
        df[feature]
        .dropna()
    )


    if len(values) == 0:

        print(
            f"Skipping {feature}: "
            "no valid values."
        )

        continue


    fig, ax = plt.subplots(
        figsize=(7, 5)
    )


    ax.hist(
        values,
        bins=50
    )


    ax.set_xlabel(
        feature
    )


    ax.set_ylabel(
        "Number of observations"
    )


    ax.set_title(
        f"Distribution of {feature} "
        f"— {CITY_NAME.capitalize()}"
    )


    fig.tight_layout()


    filename = (
        f"distribution_{feature}.png"
    )


    fig.savefig(
        output_file(filename),
        dpi=200
    )


    plt.close(fig)


# ============================================================
# DAY / NIGHT BOXPLOTS
# ============================================================

print_section(
    "DAY / NIGHT BOXPLOTS"
)


print(
    "Generating day/night comparisons..."
)


if {
    "day",
    "night"
}.issubset(periods):


    for feature in features:

        groups = []

        labels = []


        for period in [
            "day",
            "night"
        ]:


            values = (

                df.loc[
                    df["period"]
                    .astype(str)
                    .str.lower()
                    == period,
                    feature
                ]

                .dropna()
            )


            if len(values) > 0:

                groups.append(
                    values
                )

                labels.append(
                    period.capitalize()
                )


        if not groups:

            continue


        fig, ax = plt.subplots(
            figsize=(7, 5)
        )


        ax.boxplot(
            groups,
            tick_labels=labels,
            showfliers=False
        )


        ax.set_ylabel(
            feature
        )


        ax.set_title(
            f"{feature}: "
            f"Day vs Night — "
            f"{CITY_NAME.capitalize()}"
        )


        fig.tight_layout()


        filename = (
            f"day_night_{feature}.png"
        )


        fig.savefig(
            output_file(filename),
            dpi=200
        )


        plt.close(fig)


else:

    print(
        "Day/night boxplots skipped."
    )


# ============================================================
# STANDARDIZED PERIOD PROFILE
# ============================================================

print_section(
    "STANDARDIZED PERIOD PROFILES"
)


# ------------------------------------------------------------
# Mean of each feature for each period
# ------------------------------------------------------------

means = (

    df
    .groupby(
        "period"
    )[features]
    .mean()
)


# ------------------------------------------------------------
# Global mean/std
# ------------------------------------------------------------

global_mean = (
    df[features]
    .mean()
)


global_std = (
    df[features]
    .std()
)


# ------------------------------------------------------------
# Avoid division by zero
# ------------------------------------------------------------

global_std = (
    global_std
    .replace(
        0,
        np.nan
    )
)


# ------------------------------------------------------------
# Standardized means
# ------------------------------------------------------------

standardized_means = (

    means
    -
    global_mean
) / global_std


print(
    standardized_means.round(2)
)


standardized_means.to_csv(
    output_file(
        "standardized_period_profiles.csv"
    )
)


# ============================================================
# OPTIONAL STANDARDIZED DAY/NIGHT PROFILE
# ============================================================

if {
    "day",
    "night"
}.issubset(periods):


    day_night_standardized = (
        standardized_means
        .loc[
            [
                p
                for p in [
                    "day",
                    "night"
                ]
                if p in standardized_means.index
            ]
        ]
    )


    day_night_standardized.to_csv(
        output_file(
            "standardized_day_night_profiles.csv"
        )
    )


# ============================================================
# SUMMARY OF ANALYSIS
# ============================================================

print_section(
    "ANALYSIS SUMMARY"
)


print(
    f"City: {CITY_NAME}"
)


print(
    f"Input: "
    f"{input_path.resolve()}"
)


print(
    f"Observations: "
    f"{len(df):,}"
)


print(
    f"Features analysed: "
    f"{len(features)}"
)


print(
    f"Lighting enabled: "
    f"{USE_LIGHTING}"
)


print(
    "\nFeatures:"
)


for feature in features:

    print(
        f"  - {feature}"
    )


# ============================================================
# FINAL
# ============================================================

print_section(
    "ANALYSIS COMPLETE"
)


print(
    f"All results saved in:"
)


print(
    OUTPUT_DIR.resolve()
)


print()
print(
    "Generated files:"
)


for path in sorted(
    OUTPUT_DIR.iterdir()
):

    print(
        f"  {path.name}"
    )


print()
print(
    "Also generated distribution_*.png "
    "and day_night_*.png files when applicable."
)