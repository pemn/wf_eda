#!python
# Parameterized form with yaml persistence

import os, os.path, param, yaml, logging, time
from functools import partial
import panel as pn
webview = None
pn.extension('vtk')

logging.basicConfig(format='%(message)s', level=99)
log = lambda *argv: logging.log(99, time.strftime('%H:%M:%S ') + ' '.join(map(str,argv)))

# shorten paths when they are subdirectories of the current working dir
def relative_paths(path):
  cwd_drive, cwd_tail = os.path.splitdrive(os.getcwd().lower())
  path_drive, path_tail = os.path.splitdrive(path.lower())
  if cwd_drive == path_drive and os.path.commonpath([path_tail, cwd_tail]) == cwd_tail:
    return os.path.relpath(path)
  return(path)

def winforms_file_dialog(dialog_type, allow_multiple = False):
  import clr
  clr.AddReference('System.Windows.Forms') 
  import System.Windows.Forms as WinForms
  file_path = None
  if dialog_type == webview.OPEN_DIALOG:
    dialog = WinForms.OpenFileDialog()
    dialog.Multiselect = allow_multiple
    dialog.RestoreDirectory = True
    if dialog.ShowDialog() == WinForms.DialogResult.OK:
      file_path = tuple(dialog.FileNames)
  if dialog_type == webview.FOLDER_DIALOG:
    dialog = WinForms.FolderBrowserDialog()
    dialog.RestoreDirectory = True
    if dialog.ShowDialog() == WinForms.DialogResult.OK:
      file_path = (dialog.SelectedPath,)
  if dialog_type == webview.SAVE_DIALOG:
    dialog = WinForms.SaveFileDialog()
    dialog.RestoreDirectory = True
    if dialog.ShowDialog() == WinForms.DialogResult.OK:
      file_path = dialog.FileName
  return file_path

def webview_create_file_dialog(dialog_type, allow_multiple = False):
  global webview
  if webview is not None:
    w = webview.active_window()
    if w is not None:
      return w.create_file_dialog(dialog_type, allow_multiple)
  # fall back to Winforms
  return winforms_file_dialog(dialog_type, allow_multipe)  

def pn_iframe_html(p):
  return pn.pane.HTML(f'<iframe src="~/{p}" style="height:100%; width:100%"></iframe>', sizing_mode='stretch_both')

class WorkFlowBase(list, param.Parameterized):
  def get(self, key, default = None):
    for k,t,w in self:
      if k == key:
        return w.value
    return default

  def set(self, key, v):
    for k,t,w in self:
      if k == key:
        if t == 'FileSelector' and isinstance(v, (list,tuple)):
          v = ','.join(v)
        w.value = v
  
  def has_key(self, key):
    for k,t,w in self:
      if k == key:
        return True
    return False

  def keys(self):
    return [k for k,t,w in self]

  def values(self):
    return [self.get(k) for k,t,w in self]

  def items(self, event = None):
    return [(k, self.get(k)) for k,t,w in self]
  
class WorkFlowForm(WorkFlowBase):
  _file = None
  _mode = None
  _qta = None

  def __init__(self, file = None, mode = None):
    super().__init__()
    if file is not None:
      self._file = file
    if self._mode is None:
      self._mode = mode
    self._mode = mode
    if len(self) == 0:
      self.load()

  def load(self, file = None):
    self.clear()
    if file is None:
      if self._file is None:
        return
      else:
        file = self._file
    data = None
    if isinstance(file, list):
      data = file
    else:
      if not os.path.exists(file):
        return
      self._name = os.path.splitext(os.path.basename(file))[0]
      with open(file, 'r') as f:
        data = yaml.safe_load(f)
    for k,t,v in data:
      self.append([k, t, self.widget(t, v)])

  def widget(self, t, v):
    w = None
    if t == 'MultiFileSelector':
      w = pn.widgets.LiteralInput(value=v)
    elif t == 'Filename':
      w = pn.widgets.Switch(value=v)
    elif t == 'List':
      w = pn.widgets.LiteralInput(value=v)
    elif t == 'Selector' and len(v):
      w = pn.widgets.Select(value=v[0], options=v[1:])
    elif t == 'Integer':
      w = pn.widgets.IntInput(value=v)
    else:
      c = getattr(param, t)
      p = c()
      widget_class = pn.param.Param.widget_type(p)
      w = widget_class(value=v)
    return w

  def dump(self, event = None):
    # MUST use list instead of tuple or YAML will be incorrect
    r = []
    for k,t,w in self:
      if t == 'Selector':
        r.append([k, t, [w.value] + w.options])
      else:
        r.append([k, t, w.value])
    return r

  def echo(self, event = None):
    for k,v in self.items():
      print(k, v)
    if event is not None:
      obj_icon = event.obj.icon
      event.obj.icon='hourglass'
      event.obj.disabled = True
      run_step(os.path.splitext(os.path.basename(self._file))[0], self)
      event.obj.disabled = False
      event.obj.icon=obj_icon

  def save(self, file = None):
    if not isinstance(file, str):
      file = None
    if file is None:
      if self._file is None:
        return
      else:
        file = self._file
    with open(file, 'w') as f:
      yaml.dump(self.dump(), f)

  def file_browse(self, k, t, e = None):
    fl = None
    global webview
    if webview is not None:
      fl = self.wv_file_dialog(k, t)
    else:
      fl = self.qt_file_dialog(k, t)
    if fl is not None:
      fl = list(map(relative_paths, fl))
    if fl is not None:
      self.set(k, fl)

  def random_seed(self, k, e = None):
    import random
    self.set(k, random.randrange(100))

  def wv_file_dialog(self, k = '', t = ''):
    # OPEN_DIALOG = 10
    # FOLDER_DIALOG = 20
    # SAVE_DIALOG = 30
    dialog_type = 10
    allow_multiple = False
    if t == 'MultiFileSelector':
      allow_multiple = True
    if k.lower().startswith('output'):
      dialog_type = 30
    return webview_create_file_dialog(dialog_type, allow_multiple)

  def qt_file_dialog(self, k = '', t = ''):
    from PyQt5.QtWidgets import QApplication, QFileDialog
    if self._qta is None:
      self._qta = QApplication([])
    fd = QFileDialog()
    if k.lower().startswith('output'):
      fd.setAcceptMode(QFileDialog.AcceptSave)
    if t == 'MultiFileSelector':
      fd.setFileMode(QFileDialog.ExistingFiles)
    if fd.exec():
      return tuple(fd.selectedFiles())
    return None

  def steps(self):
    return [k for k,t,w, in self if t == 'Filename']

  def __panel__(self):
    if self._mode is False:
      return
    p = pn.GridBox(ncols=3, sizing_mode='stretch_both')
    for k,t,w in self:
      p.append(k)
      p.append(w)
      b = None
      if t.endswith('FileSelector'):
        b = pn.widgets.Button(icon='folder-open')
        b.on_click(partial(self.file_browse, k, t))
      if t == 'Integer':
        b = pn.widgets.Button(icon='dice')
        b.on_click(partial(self.random_seed, k))
      p.append(b)
    p.append(self._file)
    b = pn.widgets.Button(name='save', icon='device-floppy', sizing_mode='stretch_width', min_width=120, icon_size='2em')
    b.on_click(self.save)
    p.append(b)
    if self._mode:
      b= pn.widgets.Button(name='run', icon='player-play', sizing_mode='stretch_width', min_width=120, icon_size='2em')
      b.on_click(self.echo)
    else:
      b = pn.layout.spacer.Spacer()
    p.append(b)
    return p
  panel = __panel__
  __call__ = __panel__

def s_step_panel(self):
  ''' render a step according to the custom payload '''
  r = None
  if self.step_name is None:
    ...
  elif not self.get(self.step_name):
    r = pn.pane.Markdown('# 💤 ' + self.step_name)
  elif os.path.exists(self.step_name + '.py'):
    step = __import__(self.step_name)
    # on the step script, call the user defined function with shortest name
    name = sorted(dir(step), key=len)[0]
    log(f'calling function {name}')
    fn = getattr(step, name)
    r = fn(self)
    if hasattr(r, 'save'):
      r.save(self.step_name + '.html')
      log('function results saved to file: ' + self.step_name + '.html')
  elif os.path.exists(self.step_name + '.ipynb'):
    log('running jupyter notebook ' + self.step_name)
    r = run_notebook(self.step_name + '.ipynb')
    if r:
      r = pn_iframe_html(r)
    else:
      r = None
  elif os.path.exists(self.step_name + '.html'):
    r = pn_iframe_html(self.step_name + '.html')
  return r

class WorkFlowStep(WorkFlowBase):
  step_name = None
  def __init__(self, form = None):
    super().__init__()
    if form is not None:
      self.extend(form)
  @classmethod
  def factory(cls, name, form = None, **kwargs):
    self = None
    if form is None:
      # clean object
      self = type(name, (cls,), kwargs)()
    else:
      # deep copy a existing instance of a sibling class
      self = WorkFlowStep(form)
    self.step_name = name
    return self

  panel = __panel__ = s_step_panel


def form_pipeline(form_yaml, step = None):
  form = WorkFlowForm(form_yaml)
  base_name = os.path.splitext(os.path.basename(form_yaml))[0]
  vt = pn.template.VanillaTemplate()
  p = None
  if step:
    p = WorkFlowStep.factory(base_name + step, form)
  else:
    p = pn.pipeline.Pipeline()
    p.add_stage('form', form)
    for step in form.steps():
      step_name = step.removeprefix(base_name)
      p.add_stage(step_name, WorkFlowStep.factory(step, form))
  vt.main.append(p)
  return vt

class FeedBackText(param.Parameterized):
  _w = None
  _p = None
  def __init__(self, step = None, **kwargs):
    super().__init__(**kwargs)
    self._p = step
    self._w = pn.widgets.TextAreaInput(sizing_mode='stretch_width')

  def load(self, event = None):
    if os.path.exists(self.name + '.txt'):
      with open(self.name + '.txt') as f:
        self._w.value = f.read()

  def save(self, event = None):
    with open(self.name + '.txt', 'w') as f:
      f.write(self._w.value)
    # fire the entire render of this step, so the html output file is updated
    s_step_panel(self._p)

  def __panel__(self):
    self.load()
    p = pn.Row()
    p.append(pn.pane.Markdown('# 📝'))
    p.append(self._w)
    b = pn.widgets.Button(name='save', icon='device-floppy', min_width=120, icon_size='2em')
    b.on_click(self.save)
    p.append(b)
    return p
  panel = __panel__
  __call__ = __panel__

def run_step(step_name, form):
  if isinstance(form, str):
    form = WorkFlowForm(form)
  step = WorkFlowStep.factory(step_name, form)
  if not step.has_key(step_name):
    step.append([step_name, 'Filename', pn.widgets.Switch(value=True)])
  return step.panel()

display_buffer = None
def display(data = None):
  ''' 
  drop in replacement for jupyter display but for workflow steps
  if called without arguments: returns a pn.Column with items
  that were queued for display, then clear the queue.
  '''
  global display_buffer
  if not isinstance(display_buffer, pn.Column):
    display_buffer = pn.Column()
  if data is None:
    # return stored data so far and clear the buffer
    data = display_buffer
    display_buffer = None
    return data
  else:
    display_buffer.append(data)

def run_notebook(notebook, output = None, **kwargs):
  import papermill as pm
  from nbconvert import HTMLExporter, MarkdownExporter
  # custom papermill flow to avoid saving a output file
  nb = pm.iorw.load_notebook_node(notebook)
  nb = pm.parameterize.parameterize_notebook(nb, kwargs)
  nb = pm.engines.papermill_engines.execute_notebook_with_engine(None, nb, pm.utils.nb_kernel_name(nb))
  nb = pm.execute.remove_error_markers(nb)
  exporter = HTMLExporter()
  exporter.exclude_input = True
  exporter.exclude_input_prompt = True
  exporter.exclude_output_prompt = True
  r = exporter.from_notebook_node(nb)
  if not output:
    output = os.path.splitext(notebook)[0] + '.html'
  with open(output, 'w', encoding = 'utf-8') as f:
    log('notebook results saved to file: ' + output)
    f.write(r[0])
  return output

def webview_panel_start(p, url = None, port = 5000, headless = None):
  # server
  if url is None:
    url = f'http://localhost:{port}'
  if isinstance(p, str) and os.path.exists(p):
    if p.lower().endswith('yaml'):
      p = WorkFlowForm(p, True)
    else:
      p = pn_iframe_html(p)
  kwargs = dict(port=port, verbose=True, static_dirs={'~': ''})
  if headless:
    pn.serve(p, **kwargs)
  else:
    from panel.io.server import get_server, StoppableThread
    kwargs['start'] = True
    t = StoppableThread(target=get_server, io_loop=None, daemon=True, args=(p,), kwargs=kwargs)
    t.start()
  # client
  if not headless:
    global webview
    import webview
    from win32api import GetSystemMetrics
    webview.create_window(None, url, None, None, GetSystemMetrics(16), GetSystemMetrics(17))
    webview.start()

def mesh_viewer(meshes):
  from pd_vtk import vtk_plot_meshes
  if not isinstance(meshes, list):
    meshes = [meshes]
  p = vtk_plot_meshes(meshes, scalars=False, show=False)
  return pn.pane.VTK(p.ren_win, orientation_widget=True, sizing_mode='stretch_both')

if __name__=='__main__':
  import argparse, sys
  parser = argparse.ArgumentParser()
  parser.add_argument('data')
  parser.add_argument('-n', help='run notebook mode')
  parser.add_argument('--headless', help='start a server and dont open webview window', action='store_true')
  parser.add_argument('-v', help='3d viewer mode', action='store_true')
  parser.add_argument('-p', help='pipeline mode', action='store_true')
  parser.add_argument('--step', help='show only this pipeline step')
  args = parser.parse_args()
  if args.n is not None:
    print("running notebook:", args.n, "form:", args.data)
    r = run_notebook(args.notebook, form_yaml = args.data)
    if r:
      print("results saved on file:", r)
  elif args.p:
    webview_panel_start(form_pipeline(args.data, args.step), headless = args.headless)
  elif args.v:
    from pd_vtk import pv_read
    meshes = [pv_read(_) for _ in args.data.split(',')]
    webview_panel_start(mesh_viewer(meshes), headless = args.headless)
  elif args.data:
    webview_panel_start(args.data, headless = args.headless)
