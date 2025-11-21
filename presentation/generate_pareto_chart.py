#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "plotly",
# ]
# ///

"""
Generate Pareto frontier visualization for multi-objective Bayesian optimization.
Exports to JSON format compatible with PlotlyChart component.
"""

import json
import plotly.graph_objects as go
from pathlib import Path

# Define the output path
output_dir = Path(__file__).parent / "public" / "pareto"
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "pareto-frontier-plotly.json"

# Catppuccin Mocha color palette
COLORS = {
    'blue': '#89b4fa',
    'green': '#a6e3a1',
    'red': '#f38ba8',
    'cyan': '#89dceb',
    'mauve': '#cba6f7',
}

# Define trial points
all_trials_x = [2.8, 3.2, 3.9, 4.6, 5.3, 6.1, 6.9, 7.6, 4.5, 5.7, 6.7, 7.4, 8.2, 6.0, 7.3, 8.7]
all_trials_y = [7.5, 6.2, 5.5, 4.0, 3.2, 2.6, 2.0, 1.6, 7.0, 5.8, 4.8, 4.2, 3.5, 7.5, 6.2, 5.0]

# Pareto optimal points (non-dominated)
pareto_x = [2.8, 3.2, 3.9, 4.6, 5.3, 6.1, 6.9, 7.6]
pareto_y = [7.5, 6.2, 5.5, 4.0, 3.2, 2.6, 2.0, 1.6]

# Dominated points
dominated_x = [4.5, 5.7, 6.7, 7.4, 8.2, 6.0, 7.3, 8.7]
dominated_y = [7.0, 5.8, 4.8, 4.2, 3.5, 7.5, 6.2, 5.0]

# Candidate trial locations
candidate_x = [3.0, 4.2, 6.0, 3.6]
candidate_y = [6.8, 4.6, 2.3, 5.0]

# Create figure
fig = go.Figure()

# Add high acquisition value region (below Pareto frontier)
promising_x = [1.5, 2.8] + pareto_x + [7.6, 1.5]
promising_y = [0, 7.5] + pareto_y + [0, 0]
fig.add_trace(go.Scatter(
    x=promising_x,
    y=promising_y,
    fill='toself',
    fillcolor=f'rgba(137, 220, 235, 0.35)',  # Cyan with transparency
    line=dict(width=0),
    mode='lines',
    name='High Acquisition Value',
    showlegend=True,
    hoverinfo='name'
))

# Add dominated region (above Pareto frontier)
dominated_region_x = [2.8, 2.8] + pareto_x + [10, 10, 2.8]
dominated_region_y = [9, 7.5] + pareto_y + [1.6, 9, 9]
fig.add_trace(go.Scatter(
    x=dominated_region_x,
    y=dominated_region_y,
    fill='toself',
    fillcolor=f'rgba(243, 139, 168, 0.2)',  # Red with transparency
    line=dict(width=0),
    mode='lines',
    name='Low Acquisition Value',
    showlegend=True,
    hoverinfo='name'
))

# Add dominated trial points
fig.add_trace(go.Scatter(
    x=dominated_x,
    y=dominated_y,
    mode='markers',
    name='Dominated Trials',
    marker=dict(
        size=10,
        color=COLORS['red'],
        line=dict(width=1, color='white')
    ),
    hovertemplate='<b>Dominated Trial</b><br>Obj 1: %{x:.2f}<br>Obj 2: %{y:.2f}<extra></extra>'
))

# Add Pareto frontier (line + markers)
fig.add_trace(go.Scatter(
    x=pareto_x,
    y=pareto_y,
    mode='markers+lines',
    name='Pareto Frontier',
    marker=dict(
        size=12,
        color=COLORS['green'],
        line=dict(width=2, color='white')
    ),
    line=dict(
        color=COLORS['green'],
        width=3
    ),
    hovertemplate='<b>Pareto Optimal</b><br>Obj 1: %{x:.2f}<br>Obj 2: %{y:.2f}<extra></extra>'
))

# Add candidate trial locations
fig.add_trace(go.Scatter(
    x=candidate_x,
    y=candidate_y,
    mode='markers',
    name='Candidate Trials',
    marker=dict(
        size=14,
        color=COLORS['cyan'],
        symbol='diamond',
        line=dict(width=2, color='white')
    ),
    hovertemplate='<b>Candidate Trial</b><br>Obj 1: %{x:.2f}<br>Obj 2: %{y:.2f}<extra></extra>'
))

# Update layout
fig.update_layout(
    xaxis=dict(
        title='Objective 1 (minimize)',
        range=[1.5, 10],
        showgrid=True,
        gridcolor='rgba(128, 128, 128, 0.2)',
        zeroline=False
    ),
    yaxis=dict(
        title='Objective 2 (minimize)',
        range=[0, 9],
        showgrid=True,
        gridcolor='rgba(128, 128, 128, 0.2)',
        zeroline=False
    ),
    showlegend=True,
    legend=dict(
        x=1.02,
        y=1,
        xanchor='left',
        yanchor='top',
        bgcolor='rgba(0,0,0,0)',
        bordercolor='rgba(128, 128, 128, 0.3)',
        borderwidth=1
    ),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    hovermode='closest',
    margin=dict(l=60, r=180, t=40, b=60)
)

# Export to JSON
# Plotly's to_json() returns a string, but we want a properly formatted dict
fig_dict = fig.to_dict()
fig.show()

# Write to file with pretty formatting
with open(output_file, 'w') as f:
    json.dump(fig_dict, f, indent=2)

print(f"✓ Pareto frontier chart exported to: {output_file}")
print(f"  - {len(fig.data)} data traces")
print(f"  - Output size: {output_file.stat().st_size / 1024:.1f} KB")
print("\nUsage in slides.md:")
print(f'<PlotlyChart data="/pareto/pareto-frontier-plotly.json" :height="400" />')
