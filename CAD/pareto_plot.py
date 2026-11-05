import sys
import pandas as pd
from utils.plotting import plot_pareto_front

run_id = sys.argv[1]
specs = pd.read_csv(f'solutions/{run_id}.csv')['Specs'].apply(eval).iloc[:5000]
feasible = [s for s in specs
            if s['gain'] > 200 and s['phm'] > 60 and s['ugbw'] > 100e6
            and s['slewRate'] > 30 and s['noise'] < 0.03]
plot_pareto_front(feasible, f'output_figs/{run_id}/pareto.png')
