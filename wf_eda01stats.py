#!python

def main(self = None):
  def q1(_):
    return np.nanquantile(_, 0.25)
  def q2(_):
    return np.nanquantile(_, 0.5)
  def q3(_):
    return np.nanquantile(_, 0.75)
  if self is None:
    return
  from workflowform import display, FeedBackText
  from IPython.display import Markdown
  import numpy as np
  import pandas as pd
  import holoviews as hv
  hv.extension('matplotlib')
  display(FeedBackText(self, name = self.step_name))
  df = pd.read_excel(self.get('sample_db'))
  df.mask(df == -99, inplace=True)
  display(hv.Bars(df, [self.get('lito_field')],[self.get('length_field')], label='%s ✕ %s' % (self.get('lito_field'), self.get('length_field'))).aggregate(function=np.nansum))
  for v in self.get('grade_fields'):
    display(Markdown('### ' + v))
    pt = pd.DataFrame.pivot_table(df, v, self.get('lito_field'), [], [pd.Series.count, pd.Series.mean, pd.Series.min, pd.Series.max, pd.Series.var, pd.Series.std, q1, q2, q3])
    display(pt.set_axis(pt.columns.levels[0], axis=1))
  return display()

if __name__=='__main__':
  from workflowform import run_step
  run_step('wf_eda01stats', 'wf_eda.yaml')
