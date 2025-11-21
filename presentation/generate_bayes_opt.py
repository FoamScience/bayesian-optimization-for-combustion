#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "numpy",
#   "scikit-learn",
#   "scipy",
#   "bayesian-optimization",
#   "packaging",
# ]
# ///

"""
Bayesian Optimization Visualization Data Generator
Generates JSON data for animating Bayesian optimization steps
"""

import numpy as np
import json
from pathlib import Path
from bayes_opt import BayesianOptimization
from bayes_opt.acquisition import ExpectedImprovement

# Define the objective function
def F1(x, k=1, m=0, lb=0.01):
    """Objective function with multiple local minima"""
    def z(x, k, m, lb):
        cond = np.abs(x) / k - np.floor(np.abs(x) / k)
        return np.array([1 - m + (m / lb) * i if i < lb else 1 - m + (m / (1 - lb)) * (1 - i) for i in cond])

    c = z(x, k, m, lb)
    p = (x - 40) * (x - 185) * x * (x + 50) * (x + 180)
    return 3e-9 * np.abs(p) * c + 10 * np.abs(np.sin(0.1 * x))

# Objective function for minimization (bayes_opt maximizes, so we negate)
def obj_func(x):
    return -F1(np.array([x]), 1, 0, 0.01)[0]

# Helper to get posterior predictions
def posterior(optimizer, X):
    """Get GP posterior mean and std at points X"""
    # Fit the GP with current data
    X_train = np.array([[res["params"]["x"]] for res in optimizer.res])
    y_train = np.array([res["target"] for res in optimizer.res])
    optimizer._gp.fit(X_train, y_train)

    mu, sigma = optimizer._gp.predict(X, return_std=True)
    return mu, sigma

# Generate data
np.random.seed(100)  # Same seed as in presentation for consistency
x_range = np.linspace(-200, 200, 500)
y_true = F1(x_range, 1, 0, 0.01)

# Acquisition function (Expected Improvement)
# xi parameter controls exploration (higher = more exploration)
acq_function = ExpectedImprovement(xi=0.01)

# Initialize Bayesian Optimization
optimizer = BayesianOptimization(
    obj_func,
    {'x': (-200, 200)},
    acquisition_function=acq_function,
    random_state=100
)

# Get initial samples (3 random points)
n_init = 3
optimizer.maximize(init_points=n_init, n_iter=0)

# Prepare output
output_dir = Path("public/bayes-opt")
output_dir.mkdir(exist_ok=True)

# ==============================================================================
# NEW ARCHITECTURE: Component Registry + State Filtering
# ==============================================================================

# Global component registry - all components that will ever exist
all_components = []

# Helper function to add a component to the registry
def add_component(comp_dict):
    all_components.append(comp_dict)

# Helper function to filter components active at a specific state index
def get_active_components(state_idx):
    return [
        comp for comp in all_components
        if comp["lifetimeStart"] <= state_idx and
           (comp.get("lifetimeEnd") is None or comp["lifetimeEnd"] >= state_idx)
    ]

# ==============================================================================
# COMPONENT CREATION
# ==============================================================================

# Component 1: True Objective (visible in ALL states 0-14)
add_component({
    "id": "true_objective",
    "type": "line",
    "label": "True Objective",
    "data": y_true.tolist(),
    "color": "#1e66f5",  # Blue throughout
    "strokeWidth": 2,
    "showPoints": False,
    "pointSize": 0,
    "lifetimeStart": 0,
    "lifetimeEnd": None  # Visible forever
})

# Component 2: Initial samples (visible from state 1 onwards)
xx = np.array([[res["params"]["x"]] for res in optimizer.res])
yy = np.array([res["target"] for res in optimizer.res])
initial_samples = [{"x": float(xx[i][0]), "y": float(-yy[i])} for i in range(n_init)]

add_component({
    "id": "samples_initial",
    "type": "points",
    "label": f"Initial Samples ({n_init} points)",
    "data": initial_samples,
    "color": "#a6e3a1",  # Green
    "strokeWidth": 0,
    "showPoints": True,
    "pointSize": 8,
    "lifetimeStart": 1,
    "lifetimeEnd": None  # Visible forever
})

# ==============================================================================
# BAYESIAN OPTIMIZATION ITERATIONS
# ==============================================================================

n_iterations = 3
state_idx = 2  # States 0 and 1 are initial states

for iteration in range(n_iterations):
    print(f"Processing iteration {iteration}...")

    # Get current GP predictions
    X_pred = x_range.reshape(-1, 1)
    mu, sigma = posterior(optimizer, X_pred)

    # Negate back to get minimization values
    mu = -mu
    ci_upper = mu + 1.96 * sigma
    ci_lower = mu - 1.96 * sigma

    # Calculate Expected Improvement
    # Set y_max for the acquisition function (current best target value)
    acq_function.y_max = optimizer.max['target']
    # For ExpectedImprovement, we need to pass the mean and std from GP predictions
    # Note: mu is already negated for minimization, but EI expects maximization values
    # So we need to pass -mu (which is the original maximization target)
    ei = acq_function.base_acq(-mu, sigma)

    # Normalize EI for better visualization (scale to [0, 50] range)
    ei_range = ei.max() - ei.min()
    if ei_range > 0:
        ei_normalized = (ei - ei.min()) / ei_range * 50
    else:
        ei_normalized = np.ones_like(ei) * 25  # Middle of [0, 50] range if no variation

    # State A: GP Mean only (1 state)
    add_component({
        "id": f"gp_mean_{iteration}",
        "type": "line",
        "label": "GP Mean",
        "data": mu.tolist(),
        "color": "#fab387",  # Peach
        "strokeWidth": 3,
        "showPoints": False,
        "pointSize": 0,
        "lifetimeStart": state_idx,
        "lifetimeEnd": state_idx + 3  # Visible for 4 states (A, B, C, D)
    })
    state_idx += 1

    # State B: GP Mean + Confidence Interval (1 state)
    add_component({
        "id": f"ci_{iteration}",
        "type": "area",
        "label": "95% Confidence",
        "data": {
            "upper": ci_upper.tolist(),
            "lower": ci_lower.tolist()
        },
        "color": "#cba6f7",  # Mauve
        "strokeWidth": 1,
        "lifetimeStart": state_idx,
        "lifetimeEnd": state_idx + 2  # Visible for 3 states (B, C, D)
    })
    state_idx += 1

    # State C: GP Mean + CI + Expected Improvement (1 state)
    add_component({
        "id": f"ei_{iteration}",
        "type": "line",
        "label": "Expected Improvement",
        "data": ei_normalized.tolist(),
        "color": "#f38ba8",  # Red
        "strokeWidth": 2,
        "showPoints": False,
        "pointSize": 0,
        "lifetimeStart": state_idx,
        "lifetimeEnd": state_idx + 1  # Visible for 2 states (C, D)
    })
    state_idx += 1

    # Perform one optimization iteration
    optimizer.maximize(init_points=0, n_iter=1)

    # Get the new sample point
    new_x = optimizer.res[-1]["params"]["x"]
    new_y = -optimizer.res[-1]["target"]

    # State D: New sample point (persists after being added)
    add_component({
        "id": f"new_sample_{iteration}",
        "type": "points",
        "label": "New Sample",
        "data": [{"x": float(new_x), "y": float(new_y)}],
        "color": "#f9e2af",  # Yellow
        "strokeWidth": 0,
        "showPoints": True,
        "pointSize": 8,  # Match initial sample size
        "lifetimeStart": state_idx,
        "lifetimeEnd": None  # Persist forever after being added
    })
    state_idx += 1

    # Update data arrays
    xx = np.array([[res["params"]["x"]] for res in optimizer.res])
    yy = np.array([res["target"] for res in optimizer.res])

# ==============================================================================
# FINAL CONVERGED STATE
# ==============================================================================

# Run additional iterations silently
additional_iterations = 15
for i in range(additional_iterations):
    optimizer.maximize(init_points=0, n_iter=1)
    # Add each additional sample point to be visible in final state
    new_x = optimizer.res[-1]["params"]["x"]
    new_y = -optimizer.res[-1]["target"]
    add_component({
        "id": f"additional_sample_{i}",
        "type": "points",
        "label": "Additional Sample",
        "data": [{"x": float(new_x), "y": float(new_y)}],
        "color": "#f9e2af",  # Yellow, same as other new samples
        "strokeWidth": 0,
        "showPoints": True,
        "pointSize": 8,
        "lifetimeStart": state_idx,  # Only visible in final state (14)
        "lifetimeEnd": None
    })

# Final predictions
xx_final = np.array([[res["params"]["x"]] for res in optimizer.res])
yy_final = np.array([res["target"] for res in optimizer.res])

X_pred = x_range.reshape(-1, 1)
mu_final, sigma_final = posterior(optimizer, X_pred)
mu_final = -mu_final  # Negate back
ci_upper_final = mu_final + 1.96 * sigma_final
ci_lower_final = mu_final - 1.96 * sigma_final

# Final GP Mean (state 14)
add_component({
    "id": f"gp_mean_final",
    "type": "line",
    "label": "GP Mean (Converged)",
    "data": mu_final.tolist(),
    "color": "#fab387",  # Peach
    "strokeWidth": 3,
    "showPoints": False,
    "pointSize": 0,
    "lifetimeStart": state_idx,
    "lifetimeEnd": None  # Visible forever
})

# Final Confidence Interval (state 14)
add_component({
    "id": f"ci_final",
    "type": "area",
    "label": "95% Confidence",
    "data": {
        "upper": ci_upper_final.tolist(),
        "lower": ci_lower_final.tolist()
    },
    "color": "#cba6f7",  # Mauve
    "strokeWidth": 1,
    "lifetimeStart": state_idx,
    "lifetimeEnd": None  # Visible forever
})

# ==============================================================================
# STATE GENERATION
# ==============================================================================

total_samples = len(optimizer.res)
states = []
state_labels = [
    "The Objective Function",
    "Step 1: Initial Random Samples",
    "Iteration 1: Gaussian Process (Surrogate model)",
    "Iteration 1: With Confidence Interval",
    "Iteration 1: Acquisition Function (EI)",
    "Iteration 1: New Sample Added",
    "Iteration 2: Gaussian Process",
    "Iteration 2: With Confidence Interval",
    "Iteration 2: Acquisition Function (EI)",
    "Iteration 2: New Sample Added",
    "Iteration 3: Gaussian Process",
    "Iteration 3: With Confidence Interval",
    "Iteration 3: Acquisition Function (EI)",
    "Iteration 3: New Sample Added",
    f"Final: Converged after {total_samples} samples"
]

for idx in range(15):  # States 0-14
    active_components = get_active_components(idx)

    state_data = {
        "currentState": idx,
        "labels": x_range.tolist(),
        "components": active_components,
        "xRange": [-200, 200],
        "yRange": [0, 180],
        "xAxisLabel": "Parameter x",
        "yAxisLabel": "Objective f(x)"
    }

    states.append({
        "label": state_labels[idx],
        "data": state_data
    })

# ==============================================================================
# SAVE FILES
# ==============================================================================

# Save states to individual JSON files
for i, state in enumerate(states):
    filename = output_dir / f"state-{i:02d}.json"
    with open(filename, 'w') as f:
        json.dump(state["data"], f, indent=2)
    print(f"Generated: {filename}")

# Save state labels for reference
labels_file = output_dir / "labels.json"
with open(labels_file, 'w') as f:
    json.dump([{"index": i, "label": state["label"]} for i, state in enumerate(states)], f, indent=2)

total_samples = len(optimizer.res)

print(f"\nGenerated {len(states)} states for Bayesian optimization visualization")
print(f"Files saved to: {output_dir}")
print(f"Total components created: {len(all_components)}")
print(f"Total samples in optimization: {total_samples}")
print(f"\nBest result found:")
print(f"  x = {optimizer.max['params']['x']:.2f}")
print(f"  f(x) = {-optimizer.max['target']:.2f}")
