---
theme: foamscience
hideInToc: true
title: Multi-objective Bayesian Optimization for Combustion CFD
info: |
  ## Multi-objective Bayesian Optimization for Combustion CFD
  using FoamBO package for no-code bayesian optimization analysis
  on multi-objective CFD problems
class: text-center
drawings:
  persist: false
transition: slide-left
mdc: true
duration: 35min
logoLight: https://foamscience.github.io/bayesian-optimization-for-combustion/images/nhr-tu-logo.png
logoDark: https://foamscience.github.io/bayesian-optimization-for-combustion/images/nhr-tu-logo-dark.png
layout: cover
background: https://foamscience.github.io/bayesian-optimization-for-combustion/images/cover.jpg
bachgroundOpacity: 0.50
footer:
  author: Mohammed Elwardi Fadeli
  affiliation: NHR4CES - Numerical Methods in Combustion - Nov. 2025
---

<script setup>
const baseUrl = import.meta.env.BASE_URL || '/'
</script>

# Multi-objective Bayesian Optimization for Combustion CFD

A practical approach to Bayesian Optimization on OpenFOAM cases

Mohammed Elwardi Fadeli <mdi-dot /> Numerical Methods in Combustion <mdi-dot /> Nov. 2025

---
hideInToc: true
---

# The story today

<br/>

**Core topics:**
<Toc :columns="2" :mode="onlyCurrentTree" />

**Focus areas:**
- Practical usage of Bayesian Algorithms for CFD-related optimization tasks
- Some shameless self-promotion of [FoamBO](https://github.com/FoamScience/OpenFOAM-Multi-Objective-Optimization)

---

# Why BO for Combustion CFD?

How hard combustion simulations are to optimize?

- **Multi-physics coupling** - Chemistry + turbulence + heat transfer interactions
- **Stiff chemistry** - 10s-100s of species, vastly different timescales
- **High-dimensional** - Shape design parameters, turbulence models, boundary conditions
- **Multi-objective** - Emissions vs. efficiency, accuracy vs. cost, species vs. temperature
- **Noisy & non-convex** - Combustion instabilities, numerical errors, multiple local optima

<script setup>
import { ref } from 'vue'

const products = ref([
  { id: 1, name: 'Genetic Algorithms', price: '50-100 per generation × 20-50 gens = 1000-5000', comment: 'Too slow to be useful' },
  { id: 2, name: 'Swarm intelegence', price: 'Similar to GAs', comment: 'Too many particles' }
])
</script>

<br/>

<PDataTable :value="products" stripedRows tableStyle="min-width: 50rem">
  <PColumn field="name" header="Algorithm family"></PColumn>
  <PColumn field="price" header="Price"></PColumn>
  <PColumn field="comment" header="Comment"></PColumn>
</PDataTable>

---
hideInToc: true
---

# Why BO for Combustion CFD?

Bayesian Optimization advantages

<CustomList>
  <template #marker>
    <material-symbols-check-circle-unread class="text-green text-2xl"/>
  </template>

- **10-100x fewer evaluations** - Learns from every simulation
- **Intelligent sampling** - Focus on promising regions
- **Handles noise** - Robust to instabilities
- **Multi-objective native** - Pareto frontiers, not scalarization
- **Surrogate = free analysis** - Parameter importance, sensitivity
- **Probabilistic stopping/convergence** - instead of tolerance-based tradition

</CustomList>

- [Sandia Flame D](https://github.com/FoamScience/SandiaD-LTS-Bayesian-Optimization): 180 search space size, 6 objectives → 30 evaluations
- [Thermal Mixer](https://github.com/FoamScience/mixer-bayesian-optimization): 14k search space size, 3 objectives → 70 evaluations

---
transition: fade
---

# Bayesian Optimization Workflow

```yaml [Bayesian optimization algorithm]
Input: [Search domain D, Initial sample size n₀, Stopping criteria C]
Output: [Approximate optimum x*]                      # <--"Pareto front" instead if multi-objective

1:  Initialize:
        Sample X ← {x₁, …, xₙ₀} from D
        Evaluate y ← {f(x₁), …, f(xₙ₀)}
2:  Repeat:
3:      Build Surrogate:
            Fit probabilistic model f̂ using (X, y)
4:      Optimize Acquisition:                         # <-- use a multi-objective one if needed
            x* ← argmaxₓ α(x | f̂)
5:      Evaluate:
            y* ← f(x*)
6:      Update Data:
            X ← X ∪ {x*}
            y ← y ∪ {y*}
7:  Until: stopping criteria C are satisfied

8:  Return: x_best ← argmin/argmax(y)
```

---
hideInToc: true
transition: fade
---

# Bayesian Optimization Workflow

<script setup>
import { ref, onMounted } from 'vue'

const bayesStates = ref([])

onMounted(async () => {
  const baseUrl = import.meta.env.BASE_URL || '/'
  const labelsUrl = `${baseUrl}bayes-opt/labels.json`.replace(/\/+/g, '/')
  const labelsResponse = await fetch(labelsUrl)
  const labels = await labelsResponse.json()
  bayesStates.value = labels.map(item => ({
    label: item.label,
    data: `${baseUrl}bayes-opt/state-${String(item.index).padStart(2, '0')}.json`.replace(/\/+/g, '/')
  }))
})
</script>

<div v-if="bayesStates.length === 0" style="text-align: center; padding: 2rem; color: var(--c-subtext0);">
  Loading Bayesian optimization data...
</div>
<AnimatedChart
  v-else
  :states="bayesStates"
  :height="350"
  :transitionDuration="1200"
  legendPosition="top-center"
/>

---
transition: fade
---

## Surrogate models

<br>

Why GPs work well for CFD:

- **Smooth interpolation** - CFD objective functions are typically* continuous  
- **Uncertainty quantification** - predictive variance $\sigma^2(x)$ guides exploration  
- **Kernel flexibility** - encode domain knowledge (for smoothness assumption)
- **Small data regime** - work with 10–100 samples

> The previous example used a function from <Citation id="Kdela2022NewBF" citationStyle="author-year" />

---
hideInToc: true
---

## Surrogate models

<br>

More surrogate models:

- Random Forests:
  - Categorical variables, large dimensions, non-smooth objectives
  - But loses on uncertainty quantification

- Neural Networks:
  - Large datasets (>1000 samples), complex patterns
  - The large amount of trials needed

Often, GP with some kind of extension (eg. Dimensionality reduction) ends up being the best option

---
transition: fade
---

## Acquisition Functions

Tell where the next CFD evaluation is most valuable

<br/>

The most common one is **Expected Improvement**:

$$ EI(x) = (f_{\mathrm{best\_so\_far}}-\mu(x)) \Phi(Z) + \sigma(x) \phi(Z)$$

where $\mu, \sigma$ are the posterior mean and standard deviation of the surrogate
and $\Phi, \phi$ are standard normal Cumulative Distribution Function and Probability Density Function respectively

and $Z = \frac{f_{\mathrm{best\_so\_far}}-\mu(x)}{\sigma(x)}$

- **General Behavior:** High where $\mu(x)$ is low (exploitation) AND $\sigma(x)$ is high (exploration)

---
transition: fade
hideInToc: true
---

## Acquisition Functions

More acquisition functions to balance exploration/exploitation


- **Probability of Improvement:**
  - More exploitative than EI, used when confident in surrogate
  - Focuses on areas likely to beat current best
  - That's why it's also used in the **stopping stratey**

- **Upper Confidence Bound:**
  - Explicit exploration control via a hyperparameter

- **Knowledge Gradient:**
  - More conservative exploration, for very expensive cases (budget < 50 evaluations)

---
transition: fade
hideInToc: true
---

## Acquisition Functions

How about multi-objective setups?

**Key concept: Parameter domination**
- $x$ dominates $y$ if: $f_i(x) ≤ f_i(y)$ for all $i$, and $f_j(x) < f_j(y)$ for some $j$
- **Pareto optimal:** Not dominated by any other point

A few functions are common, which are basically extensions of single-objective ones:

- **Expected Hypervolume Improvement (EHVI):**
  - Measures volume improvement in objective space

- **q-Expected Hypervolume Improvement (qEHVI)**
    - Batch version: select q points simultaneously (parallel trials)
    - Enables efficient cluster utilization

---
transition: fade
hideInToc: true
---

## Acquisition Functions

How about multi-objective setups?

<script setup>
const baseUrl = import.meta.env.BASE_URL || '/'
const paretoData = `${baseUrl}pareto/pareto-frontier-plotly.json`.replace(/\/+/g, '/')
</script>

<PlotlyChart
  :data="paretoData"
  :height="360"
/>

---
transition: fade
---
 
# A shape-design example: TVC

An Axial Trapped-Vortex combustor case inspired by <Citation id="Manganaro2021" citationStyle="author-year" />

The goal is to optimize the combustor geometry to <span v-mark.underline.green> minimize methane emissions </span> and <br><span v-mark.underline.green> temperature non-uniformity </span> while maintaining <span v-mark.underline.orange> sufficient temperature rise</span> for efficient combustion.

<div class="absolute bottom-12 left-1/2 -translate-x-1/2 w-180">

![](/images/configuration.png)

</div>

---
hideInToc: true
---
 
# A shape-design example: TVC

<br>


- **Main channel**: A convergent/divergent flow channel with adjustable bevel geometry
- **Blunt bodies**: Front (fixed) and rear (variable) bluff bodies to generate recirculation zones
- **Swirl vanes**: Two parametric vanes (vane1 and vane2) to induce swirl and create vortex trapping

<div class="absolute bottom-12 left-1/2 -translate-x-1/2 w-180">

![](/images/configuration.png)

</div>

---

## AVC baseline configuration

<br>

First 6ms the solver runs with no chemistry for flow field development; then chemistry gets turned on until 50ms

- **Chemistry**: GRI-Mech 3.0 mechanism (53 species, 325 reactions) for methane-air combustion
- **Combustion model**: Eddy Dissipation Concept (EDC) for turbulence-chemistry interaction
- **Turbulence**: k-epsilon RANS model
- **Radiation**: P1 model with absorption-emission
- **Hot start initialization**: Domain initialized at 300K with air, then ignited with chemistry enabled
- Fuel: Pre-mixed methane-air at bottom inlet (15.61% CH4, 19.66% O2, 64.73% N2)

Ending up with 19 (geometrical) parameters to optimize (2 of which are categorical). That's a $7\cdot 10^{22}$ sized search space

---
transition: fade
---

## Optimization settings

<br>

Multi-objective optimization with **3 competing objectives**:

```
minimize:   CH4DomainAvg        (Average CH4 mass fraction in domain)
minimize:   PatternFactor       (Temperature non-uniformity at outlet)
maximize:   TemperatureRise     (T_outlet - T_inlet)
```

**Trade-offs**:
- Lower CH4 = better combustion efficiency (less unburned fuel)
- Lower pattern factor = more uniform temperature distribution (better for durability)
- Higher temperature rise = more energy extraction (conflicting with uniformity)

**Progress side-metric**:
- ContinuityErrors: Cumulative mass conservation error for aggressive early-stopping

---
hideInToc: true
---

## Optimization settings

<br>

Outcome constraints promote exploring designs that only "improve on" baseline performance:

```
CH4DomainAvg <= 1.1 × baseline
PatternFactor <= 1.1 × baseline
TemperatureRise >= 0.9 × baseline
```

The experiment runs 100 trials (3 concurrent simulations, each trial takes ~10-15mins)

The Early-stopping strategy stop trials in bottom 25th percentile of ContinuityErrors values at any given step. Which ends
up stopping more that 60% of the 100 trials

> DISCLAIMER! This case is a WIP - the optimization has discovered some bugs in case geometry parametrization
> and solver configuration. So insights hold little physical meaning, but it's a good learning case

> Also, for physical results, the case will have to pass mesh-independence tests, which is not yet implemented (very coarse mesh)

---
transition: fade
---

## Optimization insights

Convergence plots - the HyperVolume trace

<script setup>
const baseUrl = import.meta.env.BASE_URL || '/'
const hyperVolumeData = `${baseUrl}images/AVCs_hypervolume_trace.json`.replace(/\/+/g, '/')
</script>

<PlotlyChart :data="hyperVolumeData" :height="340"
    :layout="{xaxis: { showgrid: false, zeroline: false }, yaxis: { showgrid: false, zeroline: false }}" />

---
hideInToc: true
---

## Optimization insights

Current Pareto frontier points

For best `TemperatureRise` and `PatternFactor`, the algorithm suggests the following configuration.

Note the rear bluff body position and rotation, as well as the bevel position

<div class="absolute bottom-12 left-1/2 -translate-x-1/2 w-180">

![](/images/pareto_44.png)

</div>

---
hideInToc: true
---

## Optimization insights

Current Pareto frontier points

For best `CH4DomainAvg`, the algorithm suggests the following configuration:

More flow seperation = better burning efficiency <mdi-check class="text-green" />

<div class="absolute bottom-12 left-1/2 -translate-x-1/2 w-180">

![](/images/pareto_98.png)

</div>

---
hideInToc: true
---

## Optimization insights

Parallel coordinates for CH4DomainAvg

<script setup>
const baseUrl = import.meta.env.BASE_URL || '/'
const parallelCoordsData = `${baseUrl}images/AVCs_parallel_coordinates_for_ch4domainavg.json`.replace(/\/+/g, '/')
</script>

<PlotlyChart :data="parallelCoordsData" :height="380"
  :layout="{ font: { size: 8 }, margin: { t: 80 } }" />

---
hideInToc: true
---

## Optimization insights

Parallel coordinates for CH4DomainAvg

<script setup>
const baseUrl = import.meta.env.BASE_URL || '/'
const paretoFrontierData = `${baseUrl}images/AVCs_pareto_frontier_CH4DomainAvg_vs_PatternFactor.json`.replace(/\/+/g, '/')
</script>

<PlotlyChart :data="paretoFrontierData" :height="380"
    :layout="{xaxis: { showgrid: false, zeroline: false }, yaxis: { showgrid: false, zeroline: false }}" />

---
hideInToc: true
---

## Optimization insights

Convergence, Robustness and Sensitivity analysis

Here are a few curiousities to satisfy:

<CustomList>
  <template #marker>
    <material-symbols-question-mark class="text-green text-2xl"/>
  </template>

- In which metric analysis should we most confident in?
- What are the most important parameters? to which objectives?
- Would positionning the bevel before the read bluff body help with anything?
- Why did some trials fail?
- `bevelPosition` was focused in a sub-region out of its range. Why? countour plots might help here.

</CustomList>

```bash [Answer these questions with:]
uvx foamBO --visualize --config MOO.yaml ++store.read_from=json
```

---
layout: two-cols-header
---

# FoamBO

::left::

<CustomList>
  <template #marker>
    <material-symbols-check-circle-unread class="text-green text-2xl"/>
  </template>

- **Zero mathematical knowledge** required from users
- **Declarative configuration** - YAML-based parameter and objective definition
- **OpenFOAM integration** - automatic case parameterization
- **Multi-objective first** - Pareto optimization by default
- **Analysis built-in** - Parameter importance, convergence plots

</CustomList>

::right::

<br>

<script setup>
import { ref } from 'vue'
const treeTableData = ref([
  {
    key: '1',
    data: {
      name: 'Moo.yaml',
      notes: 'Configuration for FoamBO',
    },
    children: []
  },
  {
    key: '2',
    data: {
      name: 'FOAMCase',
      notes: 'A working OpenFOAM case, no template files',
    },
    children: []
  },
  {
    key: '3',
    data: {
      name: 'trials',
      notes: 'Arbitrary path, where trials live',
    },
    children: []
  },
  {
    key: '4',
    data: {
      name: 'artifacts',
      notes: 'Arbitrary path, where reports/checkpoints live',
    },
    children: []
  }
])
</script>

<PTreeTable :value="treeTableData" tableStyle="min-width: 20rem">
  <PColumn field="name" header="Name" expander></PColumn>
  <PColumn field="notes" header="Notes"></PColumn>
</PTreeTable>

---
hideInToc: true
---

## Typical FoamBO workflow

<br/>

<script setup>
import { ref } from 'vue'
const workflowStep = ref('0')
</script>

<PStepper v-model:value="workflowStep">
<PStepList>
  <PStep value="0">Problem Setup</PStep>
  <PStep value="1">Pilot Run</PStep>
  <PStep value="2">Full Optimization</PStep>
  <PStep value="3">Analysis</PStep>
</PStepList>

<PStepPanels>
<PStepPanel value="0">

<CustomList>
  <template #marker>
    <material-symbols-check-circle-unread class="text-green text-2xl"/>
  </template>

- Have a baseline OpenFOAM simulation
- Define objectives clearly;
- Fit the baseline case with scripts for computing metrics; these are just shell scripts returning either a `scalar` or `mean,sem`
- Identify 5-15 most important parameters
- Set realistic bounds

</CustomList>
</PStepPanel>

<PStepPanel value="1">

```bash [Generate a sample configuration]
uvx foamBO --generate-config --config MOO.yaml
```

<CustomList>
  <template #marker>
    <material-symbols-check-circle-unread class="text-green text-2xl"/>
  </template>


- YAML configuration has
  - Parameter definitions and the way they get substituted into the case
  - Metrics definitions
  - Trial Orchestration, global/early stopping strategies, runner settings (local, SLURM)
- Run a 20-30 trials optimization (coarse case) to verify the setup

</CustomList>

</PStepPanel>

<PStepPanel value="2">

```bash [Run an optimization experiment]
uvx foamBO --config MOO.yaml
```

<CustomList>
  <template #marker>
    <material-symbols-check-circle-unread class="text-green text-2xl"/>
  </template>

- Lower improvement bars, relax early-stopping
- Regularly perform the Analysis step to check on the optimization direction

</CustomList>

</PStepPanel>

<PStepPanel value="3">

```bash [Run an optimization experiment]
# This is more extensive; generates reports in artifacts folder
uvx foamBO --analysis --config MOO.yaml ++store.read_from=json
# This is more of a sky-high coolness-meter thing that you can show people
uvx foamBO --visualize --config MOO.yaml ++store.read_from=json
```

<CustomList>
  <template #marker>
    <material-symbols-check-circle-unread class="text-green text-2xl"/>
  </template>

- Check convergence plots, HyperVolume trace and the pareto-frontier charts
- Play with parameter sensitivity, and check search-space coverage
- Extract best pareto-point for each metric, and study objectve trade-offs using the surrogate model

</CustomList>
</PStepPanel>


</PStepPanels>
</PStepper>

---
transition: fade
---

## FoamBO configuration

Highlights of capabilities

```yaml [Multi-Objective setup - Parameters]
experiment:
  parameters:
  - name: rearBodyPosition
    bounds: [0.12, 0.3]
    parameter_type: float
  - name: vane1FilletCoeff
    values: [0.0, 0.5, 0.8]
    parameter_type: float
    is_ordered: true
  parameter_constraints: [ "rearBodyPosition >= vane1Position + 0.2" ]

optimization:
  case_runner:
    variable_substitution:
    - file: /system/geometryDict
      parameter_scopes:
        rearBodyPosition: rearBluntBody.positionX
        vane1FilletCoeff: vane1.filetCoeff
```

---
transition: fade
hideInToc: true
---

## FoamBO configuration

Highlights of capabilities

```yaml [Multi-Objective setup - Objectives]
optimization:
  metrics:
  - name: CH4DomainAvg
    progress: []
    command: ["pvpython", "/tmp/data/scripts/compute_metrics.py", "ch4_domain_average"]
  - name: PatternFactor
    progress: []
    command: ["pvpython", "/tmp/data/scripts/compute_metrics.py", "pattern_factor"]
  - name: ContinuityErrors
    progress: ["/tmp/data/scripts/get_metric.sh", ".", "continuity_error_cumulative"]
    command: ["/tmp/data/scripts/get_metric.sh", ".", "continuity_error_cumulative"]
    lower_is_better: True # <- guide the early-stopping if not an objective

  objective: "-CH4DomainAvg, -PatternFactor"

  outcome_constraints:
  - CH4DomainAvg <= 1.1*baseline
  - PatternFactor <= 1.1*baseline
```

---
transition: fade
hideInToc: true
---

## FoamBO configuration

Highlights of capabilities

```yaml [Multi-Objective setup - Trial orchestration]
orchestration_settings:
  max_trials: 100
  parallelism: 3
  global_stopping_strategy:
    min_trials: 10
    window_size: 5
    improvement_bar: 0.1
  early_stopping_strategy:
    type: percentile
    metric_names: ["ContinuityErrors"]
    percentile_threshold: 25
    min_progression: 5
    trial_indices_to_ignore: !range [0, 20]
```

```bash [More on this with]
uvx foamBO --docs
```

---

## Advanced Topics & Best Practices

<br/>

<mdi-report-problem class="mx-2 text-xl text-peach" /> High-fidelity CFD is too expensive, low-fidelity (coarse mesh) cheap but inaccurate<br>

<mdi-head-reload class="mx-2 text-xl text-green" /> Multi-fidelity BO surrogates<br/><br/>

- Build the surrogate on correlation between fidelities (eg. low-to-high resolution mesh)
- Optimize acquisition to choose both regular parameters and fidelity level
- Fidelity levels often translate to categorical parameters though
- **Example outcome:** 80% evaluations on coarse mesh, 20% on fine mesh
- **Speedup:** 5-10x while maintaining accuracy

---
hideInToc: true
---

## Advanced Topics & Best Practices

<br/>

Handling CFD constraints <mdi-format-horizontal-align-right /> **Early-stopping enforcement through side-metrics**:

- Convergence requirements: residuals < threshold
- Physical constraints: Re > 2000, pressure > 0
- Resource limits: walltime < 2 hours

**Other ways:**
1. **Penalize affected trials** - add constraint violation to objective
3. **Constrained EI** - only explore feasible regions (eg. dependent parameters)

---
hideInToc: true
layout: two-cols-header
---

## Advanced Topics & Best Practices

<br/><br/>

::left::

### When BO Works Well

<CustomList>
  <template #marker>
    <material-symbols-check-circle-unread class="text-green text-2xl align-middle"/>
  </template>

- 10-100 evaluations budget
- Continuous parameters dominate
- Smooth objective functions
- Expensive evaluations
- Need surrogate for analysis

</CustomList>

::right::

### When BO Struggles a little

<CustomList>
  <template #marker>
    <material-symbols-x-circle-rounded class="text-red text-2xl"/>
  </template>

- Very high dimensions (d > 50)
- Mostly categorical
- Discontinuous objectives<br> (eg. topology optimization)
- Very cheap evaluations
- Need guaranteed global optimum

</CustomList>

---

<span class="text-3xl">References and more links</span>

<script setup>
const baseUrl = import.meta.env.BASE_URL || '/'
const referencesFile = `${baseUrl}references.json`.replace(/\/+/g, '/')
</script>

<References :bibFile="referencesFile" />

<PDivider :type="solid" />

- [FoamBO](https://github.com/FoamScience/OpenFOAM-Multi-Objective-Optimization) repository has the demo-example and a few other cases
- The AVC optimization setup is available at [this repo](https://github.com/FoamScience/bayesian-optimization-for-combustion)
- A nice intro into [Bayesian Optimization](https://ax.dev/docs/intro-to-bo)
- More talks on this topic:
  - [MMA Seminar, Oct. 2024](https://foamscience.github.io/mma-seminar-byes-opt-presentation/)
  - [Last year's event](https://foamscience.github.io/nhr-training-sandia-d-flame-presentation/#/) though a little outdated

---
layout: end
---

### Questions?

<span class="text-6xl">Thank You!</span>

[This presentation source](https://github.com/FoamScience/bayesian-optimization-for-combustion) · [More NHR4CES Events](https://www.nhr4ces.de/events/)
