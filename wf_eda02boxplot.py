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
  for v in self.get('grade_fields'):
    display(hv.BoxWhisker(df, kdims=self.get('lito_field'), vdims=v, label=v))
  return display()

if __name__=='__main__':
  from workflowform import run_step
  run_step('wf_eda02boxplot', 'wf_eda.yaml')
