"""
Builds the two charts for the Phase 0 simulation summary analysis:
  1. Customer funnel (total -> trial started -> converted -> active today)
  2. Terminal-status breakdown (part-to-whole across all 1,100 customers)

Colors follow the dataviz skill's validated reference palette (references/palette.md):
sequential blue ordinal ramp for the funnel, the 5-slot categorical order for the
part-to-whole breakdown (validated via scripts/validate_palette.js).
"""
import json
import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- palette (from the dataviz skill's reference palette) ---
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

FUNNEL_RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#104281"]  # ordinal steps 250/350/450/650
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]  # slots 1-5, validated

plt.rcParams["font.family"] = "sans-serif"


def load_stats():
    data = json.load(open("../internal/_sim_customer_timeline.json"))
    total = len(data)
    ever_trial = [t for t in data if t["trial"] is not None]
    ever_paid = [t for t in ever_trial if t["trial"]["outcome"] == "converted"]
    active = [t for t in ever_paid if t["churn_date"] is None]
    lapsed = [t for t in ever_paid if t["churn_date"] is not None]

    still_buying, quiet = [], []
    for t in lapsed:
        churn_dt = datetime.date.fromisoformat(t["churn_date"])
        post = [o for o in t["order_events"] if datetime.date.fromisoformat(o["date"]) > churn_dt]
        (still_buying if post else quiet).append(t)

    course_merch_only = [t for t in data if t["account_type"] == "course_merch_only"]
    trial_not_converted = [t for t in ever_trial if t["trial"]["outcome"] != "converted"]

    return {
        "total": total,
        "ever_trial": len(ever_trial),
        "ever_paid": len(ever_paid),
        "active": len(active),
        "lapsed": len(lapsed),
        "still_buying": len(still_buying),
        "quiet": len(quiet),
        "course_merch_only": len(course_merch_only),
        "trial_not_converted": len(trial_not_converted),
    }


def build_funnel_chart(stats):
    stages = ["Total customers LTD", "Ever started trial", "Converted (ever-paid)", "Active subscribers today"]
    values = [stats["total"], stats["ever_trial"], stats["ever_paid"], stats["active"]]

    fig, ax = plt.subplots(figsize=(9, 4.2))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    y_pos = range(len(stages))[::-1]
    bars = ax.barh(list(y_pos), values, color=FUNNEL_RAMP, height=0.55, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.015, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", ha="left", fontsize=11, color=INK_PRIMARY, fontweight="bold")

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(stages, fontsize=10.5, color=INK_SECONDARY)
    ax.set_xlabel("Customers", fontsize=9.5, color=INK_MUTED)
    ax.set_title("Kinetic customer funnel — lifetime to date", fontsize=13, color=INK_PRIMARY,
                 loc="left", fontweight="bold", pad=14)
    ax.xaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRIDLINE)
    ax.tick_params(colors=INK_MUTED, length=0)
    ax.set_xlim(0, max(values) * 1.18)
    fig.tight_layout()
    fig.savefig("../internal/funnel_chart.png", dpi=140, facecolor=SURFACE)
    plt.close(fig)


def build_segment_breakdown_chart(stats):
    labels = ["Active subscriber", "Trial, never converted", "Course/merch-only\n(never subscribed)",
              "Lapsed, gone quiet", "Lapsed, still buying"]
    values = [stats["active"], stats["trial_not_converted"], stats["course_merch_only"],
              stats["quiet"], stats["still_buying"]]
    # sort descending for readability
    order = sorted(range(len(values)), key=lambda i: -values[i])
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    colors = [CATEGORICAL[i] for i in order]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    y_pos = range(len(labels))[::-1]
    bars = ax.barh(list(y_pos), values, color=colors, height=0.6, zorder=3)

    total = stats["total"]
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + total * 0.012, bar.get_y() + bar.get_height() / 2,
                f"{val:,}  ({val/total:.1%})", va="center", ha="left", fontsize=10.5,
                color=INK_PRIMARY, fontweight="bold")

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=10.5, color=INK_SECONDARY)
    ax.set_xlabel("Customers", fontsize=9.5, color=INK_MUTED)
    ax.set_title(f"Where all {total:,} customers stand today", fontsize=13, color=INK_PRIMARY,
                 loc="left", fontweight="bold", pad=14)
    ax.xaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRIDLINE)
    ax.tick_params(colors=INK_MUTED, length=0)
    ax.set_xlim(0, max(values) * 1.35)
    fig.tight_layout()
    fig.savefig("../internal/segment_breakdown_chart.png", dpi=140, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    stats = load_stats()
    build_funnel_chart(stats)
    build_segment_breakdown_chart(stats)
    print("Wrote funnel_chart.png and segment_breakdown_chart.png")
    print(stats)
