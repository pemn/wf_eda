#!python

def main(self = None):
  if self is None:
    return
  from workflowform import display, FeedBackText
  from IPython.display import Markdown
  import numpy as np
  import pandas as pd
  from _gui import pd_detect_xyz
  import holoviews as hv
  hv.extension('matplotlib')
  df = pd.read_excel(self.get('sample_db'))
  df.mask(df == -99, inplace=True)
  xyz = pd_detect_xyz(df)
  display(FeedBackText(name = self.step_name))
  display(hv.Overlay([hv.Scatter(rd, xyz[0], xyz[1], label=ri) for ri,rd in df.groupby(self.get('lito_field'))]).opts(fig_size=150))
  return display()

if __name__=='__main__':
  from workflowform import run_step
  run_step('wf_eda04scatter', 'wf_eda.yaml')
